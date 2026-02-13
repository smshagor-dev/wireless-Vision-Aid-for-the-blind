/*
 * ESP32-CAM Wireless Camera for WVAB Project
 * 
 * This code sets up ESP32-CAM as a Wi-Fi camera that streams video
 * to the vision processing server.
 * 
 * Hardware Required:
 * - ESP32-CAM module
 * - FTDI programmer (for uploading code)
 * - 5V power supply
 * 
 * Installation:
 * 1. Install ESP32 board in Arduino IDE
 * 2. Select "AI Thinker ESP32-CAM" from Tools > Board
 * 3. Upload this code
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include "fb_gfx.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h"

// ===== Wi-Fi Configuration =====
// Option 1: Access Point Mode (ESP32 creates its own network)
const char* AP_SSID = "WVAB_Camera";
const char* AP_PASSWORD = "wvab12345";

// Option 2: Station Mode (ESP32 connects to existing Wi-Fi)
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Set to true for AP mode, false for Station mode
#define USE_AP_MODE true

// ===== Camera Pin Configuration (AI-Thinker ESP32-CAM) =====
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

#define LED_GPIO_NUM       4  // Flash LED

httpd_handle_t stream_httpd = NULL;

// ===== MJPEG Streaming Handler =====
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[64];

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frame");
  if (res != ESP_OK) {
    return res;
  }

  // Streaming loop
  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
    } else {
      if (fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!jpeg_converted) {
          Serial.println("JPEG compression failed");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      size_t hlen = snprintf((char *)part_buf, 64, 
                            "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", 
                            _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }

    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }

    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, "\r\n--frame\r\n", 13);
    }

    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }

    if (res != ESP_OK) {
      break;
    }
  }

  return res;
}

// ===== Start Camera Server =====
void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    Serial.println("Camera server started successfully");
  } else {
    Serial.println("Error starting camera server");
  }
}

// ===== Setup Function =====
void setup() {
  // Disable brownout detector
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(115200);
  Serial.println("\n\n=================================");
  Serial.println("WVAB ESP32-CAM Starting...");
  Serial.println("=================================");

  // Configure LED
  pinMode(LED_GPIO_NUM, OUTPUT);
  digitalWrite(LED_GPIO_NUM, LOW);

  // ===== Camera Configuration =====
  camera_config_t config;
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
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Frame size and quality settings
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;    // 640x480 - Good balance
    config.jpeg_quality = 10;              // Lower = better quality (0-63)
    config.fb_count = 2;
    Serial.println("PSRAM found - High quality mode");
  } else {
    config.frame_size = FRAMESIZE_QVGA;   // 320x240 - Lower resolution
    config.jpeg_quality = 12;
    config.fb_count = 1;
    Serial.println("No PSRAM - Low quality mode");
  }

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }

  // Camera sensor settings for better detection
  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);     // -2 to 2
  s->set_contrast(s, 0);       // -2 to 2
  s->set_saturation(s, 0);     // -2 to 2
  s->set_special_effect(s, 0); // 0 = No effect
  s->set_whitebal(s, 1);       // 0 = disable, 1 = enable
  s->set_awb_gain(s, 1);       // 0 = disable, 1 = enable
  s->set_wb_mode(s, 0);        // 0 to 4
  s->set_exposure_ctrl(s, 1);  // 0 = disable, 1 = enable
  s->set_aec2(s, 0);           // 0 = disable, 1 = enable
  s->set_ae_level(s, 0);       // -2 to 2
  s->set_aec_value(s, 300);    // 0 to 1200
  s->set_gain_ctrl(s, 1);      // 0 = disable, 1 = enable
  s->set_agc_gain(s, 0);       // 0 to 30
  s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
  s->set_bpc(s, 0);            // 0 = disable, 1 = enable
  s->set_wpc(s, 1);            // 0 = disable, 1 = enable
  s->set_raw_gma(s, 1);        // 0 = disable, 1 = enable
  s->set_lenc(s, 1);           // 0 = disable, 1 = enable
  s->set_hmirror(s, 0);        // 0 = disable, 1 = enable
  s->set_vflip(s, 0);          // 0 = disable, 1 = enable
  s->set_dcw(s, 1);            // 0 = disable, 1 = enable

  Serial.println("Camera initialized successfully");

  // ===== Wi-Fi Setup =====
  WiFi.mode(WIFI_STA);
  
  if (USE_AP_MODE) {
    // Create Access Point
    Serial.println("\nCreating Access Point...");
    WiFi.softAP(AP_SSID, AP_PASSWORD);
    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP IP address: ");
    Serial.println(IP);
    Serial.printf("Connect to Wi-Fi: %s\n", AP_SSID);
    Serial.printf("Password: %s\n", AP_PASSWORD);
    Serial.printf("Stream URL: http://%s:81/stream\n", IP.toString().c_str());
  } else {
    // Connect to existing Wi-Fi
    Serial.println("\nConnecting to Wi-Fi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWi-Fi Connected!");
      Serial.print("IP Address: ");
      Serial.println(WiFi.localIP());
      Serial.printf("Stream URL: http://%s:81/stream\n", WiFi.localIP().toString().c_str());
    } else {
      Serial.println("\nWi-Fi Connection Failed!");
      return;
    }
  }

  // Start camera streaming server
  startCameraServer();

  // LED blink to indicate ready
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_GPIO_NUM, HIGH);
    delay(200);
    digitalWrite(LED_GPIO_NUM, LOW);
    delay(200);
  }

  Serial.println("=================================");
  Serial.println("WVAB Camera Ready!");
  Serial.println("=================================");
}

// ===== Loop Function =====
void loop() {
  // Keep the server running
  delay(10);
}
