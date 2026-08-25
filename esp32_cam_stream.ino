#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_system.h"
#include "esp_wifi.h"
#include "mbedtls/gcm.h"

#if __has_include("esp32_secrets.h")
#include "esp32_secrets.h"
#else
#include "esp32_secrets.example.h"
#endif

// WVAB ESP32-CAM secure transport.
// Packet header (network byte order):
//   session_id:uint32 | frame_id:uint32 | total_chunks:uint16 |
//   chunk_index:uint16 | payload_size:uint16
// Every encrypted packet carries: base_nonce[12] | GCM tag[16] | ciphertext.
// The complete 14-byte header is authenticated as AES-GCM AAD.

#define TARGET_FPS 12
#define MIN_FRAME_INTERVAL_MS (1000 / TARGET_FPS)
#define WIFI_POWER_SAVE true
#define WIFI_RECONNECT_INTERVAL_MS 5000
#define AUTH_REFRESH_INTERVAL_MS 10000

const uint16_t MAX_UDP_PAYLOAD = 1450;
const uint16_t HEADER_SIZE = 14;
const uint16_t NONCE_SIZE = 12;
const uint16_t TAG_SIZE = 16;
const uint16_t MAX_FRAME_CHUNKS = 1024;
const uint32_t AUTH_FRAME_ID = 0xFFFFFFFFu;
const uint32_t MAX_DATA_FRAME_ID = 0xFFFFFFFEu;

WiFiUDP udp;
uint32_t session_id = 0;
uint32_t frame_id = 0;

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define LED_GPIO_NUM       4

static void halt_with_error(const char* message) {
  Serial.printf("FATAL: %s\n", message);
  while (true) {
    digitalWrite(LED_GPIO_NUM, HIGH);
    delay(150);
    digitalWrite(LED_GPIO_NUM, LOW);
    delay(850);
  }
}

static bool key_is_all_zero() {
  for (size_t i = 0; i < sizeof(WVAB_AES_KEY); ++i) {
    if (WVAB_AES_KEY[i] != 0) return false;
  }
  return true;
}

static void validate_secrets() {
  if (!WVAB_SECRETS_CONFIGURED) {
    halt_with_error("device secrets are not configured; run tools/generate_device_secrets.py");
  }
  if (sizeof(WVAB_AES_KEY) != 16 && sizeof(WVAB_AES_KEY) != 24 && sizeof(WVAB_AES_KEY) != 32) {
    halt_with_error("AES key must be 16, 24, or 32 bytes");
  }
  if (key_is_all_zero()) halt_with_error("refusing all-zero AES key");
  if (strlen(WVAB_UDP_TOKEN) < 16) halt_with_error("UDP token must be at least 16 characters");
  if (strlen(WVAB_UDP_HOST) == 0) halt_with_error("UDP host is empty");
  if (WVAB_UDP_PORT <= 0 || WVAB_UDP_PORT > 65535) halt_with_error("UDP port is invalid");

  if (WVAB_USE_AP_MODE) {
    if (strlen(WVAB_AP_SSID) == 0 || strlen(WVAB_AP_PASSWORD) < 8) {
      halt_with_error("AP SSID/password is invalid");
    }
  } else if (strlen(WVAB_WIFI_SSID) == 0 || strlen(WVAB_WIFI_PASSWORD) < 8) {
    halt_with_error("station Wi-Fi credentials are invalid");
  }
}

static void write_u32(uint8_t* buf, uint32_t value) {
  buf[0] = (value >> 24) & 0xFF;
  buf[1] = (value >> 16) & 0xFF;
  buf[2] = (value >> 8) & 0xFF;
  buf[3] = value & 0xFF;
}

static void write_u16(uint8_t* buf, uint16_t value) {
  buf[0] = (value >> 8) & 0xFF;
  buf[1] = value & 0xFF;
}

static void build_header(
    uint8_t header[HEADER_SIZE],
    uint32_t current_session_id,
    uint32_t current_frame_id,
    uint16_t total_chunks,
    uint16_t chunk_index,
    uint16_t payload_size) {
  write_u32(header, current_session_id);
  write_u32(header + 4, current_frame_id);
  write_u16(header + 8, total_chunks);
  write_u16(header + 10, chunk_index);
  write_u16(header + 12, payload_size);
}

static void derive_nonce(
    const uint8_t base_nonce[NONCE_SIZE],
    uint16_t chunk_index,
    uint8_t nonce[NONCE_SIZE]) {
  memcpy(nonce, base_nonce, NONCE_SIZE);
  uint32_t counter = (uint32_t(nonce[8]) << 24) |
                     (uint32_t(nonce[9]) << 16) |
                     (uint32_t(nonce[10]) << 8) |
                     uint32_t(nonce[11]);
  counter += chunk_index;
  nonce[8] = (counter >> 24) & 0xFF;
  nonce[9] = (counter >> 16) & 0xFF;
  nonce[10] = (counter >> 8) & 0xFF;
  nonce[11] = counter & 0xFF;
}

static bool init_gcm(mbedtls_gcm_context* ctx) {
  mbedtls_gcm_init(ctx);
  const int rc = mbedtls_gcm_setkey(
      ctx,
      MBEDTLS_CIPHER_ID_AES,
      WVAB_AES_KEY,
      static_cast<unsigned int>(sizeof(WVAB_AES_KEY) * 8));
  if (rc != 0) {
    Serial.printf("GCM key setup failed: %d\n", rc);
    mbedtls_gcm_free(ctx);
    return false;
  }
  return true;
}

static bool send_packet(
    const uint8_t header[HEADER_SIZE],
    const uint8_t base_nonce[NONCE_SIZE],
    const uint8_t tag[TAG_SIZE],
    const uint8_t* ciphertext,
    size_t ciphertext_len) {
  if (!udp.beginPacket(WVAB_UDP_HOST, WVAB_UDP_PORT)) return false;
  udp.write(header, HEADER_SIZE);
  udp.write(base_nonce, NONCE_SIZE);
  udp.write(tag, TAG_SIZE);
  if (ciphertext_len > 0) udp.write(ciphertext, ciphertext_len);
  return udp.endPacket() == 1;
}

static bool send_auth_packet() {
  const size_t token_len = strlen(WVAB_UDP_TOKEN);
  if (token_len < 16 || token_len > 256 || session_id == 0) return false;

  const uint16_t payload_len = static_cast<uint16_t>(NONCE_SIZE + TAG_SIZE + token_len);
  uint8_t header[HEADER_SIZE];
  build_header(header, session_id, AUTH_FRAME_ID, 0, 0, payload_len);

  uint8_t base_nonce[NONCE_SIZE];
  esp_fill_random(base_nonce, sizeof(base_nonce));
  uint8_t nonce[NONCE_SIZE];
  derive_nonce(base_nonce, 0, nonce);
  uint8_t ciphertext[256];
  uint8_t tag[TAG_SIZE];

  mbedtls_gcm_context ctx;
  if (!init_gcm(&ctx)) return false;
  const int rc = mbedtls_gcm_crypt_and_tag(
      &ctx,
      MBEDTLS_GCM_ENCRYPT,
      token_len,
      nonce,
      NONCE_SIZE,
      header,
      HEADER_SIZE,
      reinterpret_cast<const uint8_t*>(WVAB_UDP_TOKEN),
      ciphertext,
      TAG_SIZE,
      tag);
  mbedtls_gcm_free(&ctx);
  if (rc != 0) {
    Serial.printf("Auth encryption failed: %d\n", rc);
    return false;
  }
  return send_packet(header, base_nonce, tag, ciphertext, token_len);
}

static bool send_udp_frame(camera_fb_t* fb) {
  if (!fb || !fb->buf || fb->len == 0 || session_id == 0) return false;

  const uint16_t max_plain = MAX_UDP_PAYLOAD - HEADER_SIZE - NONCE_SIZE - TAG_SIZE;
  const size_t chunk_count = (fb->len + max_plain - 1) / max_plain;
  if (chunk_count == 0 || chunk_count > MAX_FRAME_CHUNKS) {
    Serial.printf("Dropping oversized frame: %u bytes, %u chunks\n",
                  static_cast<unsigned int>(fb->len),
                  static_cast<unsigned int>(chunk_count));
    return false;
  }
  const uint16_t total_chunks = static_cast<uint16_t>(chunk_count);

  uint8_t base_nonce[NONCE_SIZE];
  esp_fill_random(base_nonce, sizeof(base_nonce));
  uint8_t ciphertext[MAX_UDP_PAYLOAD];

  mbedtls_gcm_context ctx;
  if (!init_gcm(&ctx)) return false;
  bool success = true;

  for (uint16_t chunk_index = 0; chunk_index < total_chunks; ++chunk_index) {
    const size_t start = static_cast<size_t>(chunk_index) * max_plain;
    size_t end = start + max_plain;
    if (end > fb->len) end = fb->len;
    const uint16_t plain_len = static_cast<uint16_t>(end - start);
    const uint16_t payload_len = static_cast<uint16_t>(NONCE_SIZE + TAG_SIZE + plain_len);

    uint8_t header[HEADER_SIZE];
    build_header(header, session_id, frame_id, total_chunks, chunk_index, payload_len);

    uint8_t nonce[NONCE_SIZE];
    derive_nonce(base_nonce, chunk_index, nonce);
    uint8_t tag[TAG_SIZE];
    const int rc = mbedtls_gcm_crypt_and_tag(
        &ctx,
        MBEDTLS_GCM_ENCRYPT,
        plain_len,
        nonce,
        NONCE_SIZE,
        header,
        HEADER_SIZE,
        fb->buf + start,
        ciphertext,
        TAG_SIZE,
        tag);
    if (rc != 0) {
      Serial.printf("Frame encryption failed: %d\n", rc);
      success = false;
      break;
    }

    if (!send_packet(header, base_nonce, tag, ciphertext, plain_len)) {
      success = false;
      break;
    }
  }

  mbedtls_gcm_free(&ctx);
  if (frame_id >= MAX_DATA_FRAME_ID) {
    frame_id = 0;
  } else {
    ++frame_id;
  }
  return success;
}

static void connect_wifi() {
  if (WVAB_USE_AP_MODE) {
    WiFi.mode(WIFI_AP);
    if (!WiFi.softAP(WVAB_AP_SSID, WVAB_AP_PASSWORD)) {
      halt_with_error("could not start ESP32 access point");
    }
    Serial.print("AP IP: ");
    Serial.println(WiFi.softAPIP());
    Serial.printf("AP SSID: %s\n", WVAB_AP_SSID);
    return;
  }

  WiFi.mode(WIFI_STA);
  if (WIFI_POWER_SAVE) {
    WiFi.setSleep(true);
    esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
  }
  WiFi.begin(WVAB_WIFI_SSID, WVAB_WIFI_PASSWORD);
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(250);
  }
  if (WiFi.status() != WL_CONNECTED) halt_with_error("station Wi-Fi connection failed");
  Serial.print("Station IP: ");
  Serial.println(WiFi.localIP());
}

static void configure_camera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  const esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    halt_with_error("camera initialization failed");
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor) {
    sensor->set_brightness(sensor, 0);
    sensor->set_contrast(sensor, 0);
    sensor->set_saturation(sensor, 0);
    sensor->set_whitebal(sensor, 1);
    sensor->set_awb_gain(sensor, 1);
    sensor->set_exposure_ctrl(sensor, 1);
    sensor->set_gain_ctrl(sensor, 1);
    sensor->set_lenc(sensor, 1);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_GPIO_NUM, OUTPUT);
  digitalWrite(LED_GPIO_NUM, LOW);

  validate_secrets();
  do {
    session_id = esp_random();
  } while (session_id == 0);
  frame_id = 0;

  configure_camera();
  connect_wifi();

  if (!udp.begin(WVAB_UDP_PORT)) halt_with_error("could not initialize UDP socket");
  if (!send_auth_packet()) halt_with_error("initial UDP authentication packet failed");
  Serial.println("WVAB authenticated AES-GCM UDP streaming enabled");

  for (int i = 0; i < 3; ++i) {
    digitalWrite(LED_GPIO_NUM, HIGH);
    delay(120);
    digitalWrite(LED_GPIO_NUM, LOW);
    delay(120);
  }
}

void loop() {
  static uint32_t last_wifi_check = 0;
  static uint32_t last_frame_ms = 0;
  static uint32_t last_auth_ms = 0;
  const uint32_t now = millis();

  if (!WVAB_USE_AP_MODE && now - last_wifi_check >= WIFI_RECONNECT_INTERVAL_MS) {
    last_wifi_check = now;
    if (WiFi.status() != WL_CONNECTED) {
      WiFi.disconnect();
      WiFi.begin(WVAB_WIFI_SSID, WVAB_WIFI_PASSWORD);
      return;
    }
  }

  if (now - last_auth_ms >= AUTH_REFRESH_INTERVAL_MS) {
    if (send_auth_packet()) last_auth_ms = now;
  }
  if (now - last_frame_ms < MIN_FRAME_INTERVAL_MS) {
    delay(1);
    return;
  }
  last_frame_ms = now;

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    delay(50);
    return;
  }

  if (!send_udp_frame(fb)) Serial.println("UDP frame send failed");
  esp_camera_fb_return(fb);
}
