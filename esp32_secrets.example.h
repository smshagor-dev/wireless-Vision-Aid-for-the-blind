#pragma once
#include <stdint.h>

// This file is safe to commit because WVAB_SECRETS_CONFIGURED is false and
// the firmware refuses to stream with these placeholder values. Generate the
// real, git-ignored esp32_secrets.h with tools/generate_device_secrets.py.
#define WVAB_SECRETS_CONFIGURED 0
#define WVAB_USE_AP_MODE true
#define WVAB_AP_SSID "WVAB_CAM"
#define WVAB_AP_PASSWORD "CHANGE_ME"
#define WVAB_WIFI_SSID "CHANGE_ME"
#define WVAB_WIFI_PASSWORD "CHANGE_ME"
#define WVAB_UDP_HOST "192.168.4.2"
#define WVAB_UDP_PORT 9999
#define WVAB_UDP_TOKEN "CHANGE_ME"

static const uint8_t WVAB_AES_KEY[32] = {0};
