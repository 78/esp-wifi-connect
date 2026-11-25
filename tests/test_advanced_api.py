"""Run the settings HTTP handler with real cJSON and host substitutes for ESP-IDF."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AdvancedApiTests(unittest.TestCase):
    def test_settings_api(self):
        cjson = Path(os.environ.get("CJSON_DIR", "/nonexistent"))
        if not shutil.which("c++") or not (cjson / "cJSON.c").exists():
            self.skipTest("requires a host compiler and CJSON_DIR pointing to the cJSON source")
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            for name, text in FIXTURES.items():
                (build / name).write_text(text, encoding="utf-8")
            subprocess.run(["cc", "-c", str(cjson / "cJSON.c"), "-o", str(build / "cjson.o")], check=True)
            binary = build / "check"
            subprocess.run([
                "c++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-Wno-missing-field-initializers",
                "-I", str(build), "-I", str(ROOT / "include"), "-I", str(ROOT), "-I", str(cjson),
                str(build / "main.cc"), str(ROOT / "wifi_config_group.cc"), str(build / "cjson.o"),
                "-o", str(binary),
            ], check=True)
            subprocess.run([str(binary)], check=True)

    def test_station_static_ip_switching(self):
        if not shutil.which("c++"):
            self.skipTest("requires a host compiler")
        with tempfile.TemporaryDirectory() as temp:
            build = Path(temp)
            for name, text in STATION_FIXTURES.items():
                target = build / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            binary = build / "check_station"
            subprocess.run([
                "c++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter", "-Wno-missing-field-initializers",
                "-I", str(build), "-I", str(ROOT / "include"),
                str(build / "main.cc"), str(ROOT / "wifi_station.cc"),
                "-o", str(binary),
            ], check=True)
            subprocess.run([str(binary)], check=True)


FIXTURES = {
    "wifi_configuration_ap.h": r'''
#pragma once
#include "wifi_config_group.h"
#include <algorithm>
#include <cstring>
#include <string>
using esp_err_t = int;
constexpr int ESP_OK = 0;
constexpr int HTTPD_500_INTERNAL_SERVER_ERROR = 500;
constexpr int HTTPD_400_BAD_REQUEST = 400;
constexpr int HTTPD_404_NOT_FOUND = 404;
constexpr int HTTPD_SOCK_ERR_TIMEOUT = -5;
struct httpd_req_t {
    std::string body;
    const char* type = "application/json";
    size_t content_len = 0;
    size_t read = 0;
    int status = 200;
    std::string response;
};
inline int httpd_resp_send_err(httpd_req_t* r, int status, const char* msg) {
    r->status = status;
    r->response = msg;
    return ESP_OK;
}
inline int httpd_resp_set_type(httpd_req_t*, const char*) { return ESP_OK; }
inline int httpd_resp_set_hdr(httpd_req_t*, const char*, const char*) { return ESP_OK; }
inline int httpd_resp_sendstr(httpd_req_t* r, const char* s) { r->response = s; return ESP_OK; }
inline int httpd_resp_set_status(httpd_req_t* r, const char* s) { r->status = atoi(s); return ESP_OK; }
inline int httpd_resp_send_408(httpd_req_t* r) { return httpd_resp_send_err(r, 408, "timeout"); }
inline int httpd_req_get_hdr_value_str(httpd_req_t* r, const char*, char* out, size_t len) {
    if (std::strlen(r->type) >= len) return -1;
    std::strcpy(out, r->type);
    return ESP_OK;
}
inline int httpd_req_recv(httpd_req_t* r, char* data, size_t len) {
    const auto n = std::min({len, r->body.size() - r->read, size_t{4}});
    std::memcpy(data, r->body.data() + r->read, n);
    r->read += n;
    return static_cast<int>(n);
}
inline int httpd_req_get_url_query_str(httpd_req_t*, char* buf, size_t) {
    std::strcpy(buf, "lang=zh-CN");
    return ESP_OK;
}
inline int httpd_query_key_value(const char*, const char*, char* buf, size_t) {
    std::strcpy(buf, "zh-CN");
    return ESP_OK;
}
class WifiConfigurationAp {
public:
    void SetAdvancedGroups(const std::vector<wifi_config::Group>& groups);
    void RefreshWifiStaticIpOptions();
    void BuildAdvancedGroups();
    esp_err_t GetAdvancedConfig(httpd_req_t* req);
    esp_err_t SaveAdvancedConfig(httpd_req_t* req);
    std::vector<std::string> GetSavedSsids() const { return saved_ssids_; }
    std::vector<wifi_config::Group> advanced_groups_;
    std::vector<std::string> saved_ssids_;
    int8_t max_tx_power_ = 80;
    bool remember_bssid_ = false;
    bool static_ip_enabled_ = false;
    std::string static_ip_ssid_;
    std::string static_ip_;
    std::string static_gateway_;
    std::string static_netmask_;
    std::string static_dns_;
};
''',
    "esp_event.h": "#pragma once\nusing EventGroupHandle_t = void*;\nusing esp_event_base_t = const char*;\nusing esp_event_handler_instance_t = void*;\n",
    "esp_timer.h": "#pragma once\nusing esp_timer_handle_t = void*;\n",
    "esp_netif.h": "#pragma once\nstruct esp_netif_t;\n",
    "esp_wifi_types_generic.h": "#pragma once\nusing wifi_auth_mode_t = int;\n",
    "esp_wifi.h": r'''
#pragma once
inline int esp_wifi_set_max_tx_power(int8_t) { return ESP_OK; }
''',
    "nvs.h": r'''
#pragma once
#include <cstring>
#include <map>
#include <string>
using nvs_handle_t = int;
constexpr int NVS_READONLY = 0;
constexpr int NVS_READWRITE = 1;
constexpr int ESP_FAIL = -1;
constexpr int ESP_ERR_NVS_NOT_FOUND = -2;
inline std::string g_nvs_fail_key;
inline int g_nvs_commit_count = 0;
inline std::map<std::string, std::string> g_nvs_strings;
inline std::map<std::string, int> g_nvs_ints;
inline int nvs_open(const char*, int, nvs_handle_t* out) { *out = 1; return ESP_OK; }
inline int nvs_set_i8(nvs_handle_t, const char* key, int8_t val) {
    if (g_nvs_fail_key == key) return ESP_FAIL;
    g_nvs_ints[key] = val;
    return ESP_OK;
}
inline int nvs_set_u8(nvs_handle_t, const char* key, uint8_t val) {
    if (g_nvs_fail_key == key) return ESP_FAIL;
    g_nvs_ints[key] = val;
    return ESP_OK;
}
inline int nvs_set_str(nvs_handle_t, const char* key, const char* val) {
    if (g_nvs_fail_key == key) return ESP_FAIL;
    g_nvs_strings[key] = val;
    return ESP_OK;
}
inline int nvs_get_i8(nvs_handle_t, const char* key, int8_t* out) {
    auto it = g_nvs_ints.find(key);
    if (it == g_nvs_ints.end()) return ESP_ERR_NVS_NOT_FOUND;
    *out = static_cast<int8_t>(it->second);
    return ESP_OK;
}
inline int nvs_get_u8(nvs_handle_t, const char* key, uint8_t* out) {
    auto it = g_nvs_ints.find(key);
    if (it == g_nvs_ints.end()) return ESP_ERR_NVS_NOT_FOUND;
    *out = static_cast<uint8_t>(it->second);
    return ESP_OK;
}
inline int nvs_get_str(nvs_handle_t, const char* key, char* out, size_t* len) {
    auto it = g_nvs_strings.find(key);
    if (it == g_nvs_strings.end()) return ESP_ERR_NVS_NOT_FOUND;
    const size_t needed = it->second.size() + 1;
    if (!out) {
        *len = needed;
        return ESP_OK;
    }
    if (*len < needed) return ESP_FAIL;
    std::memcpy(out, it->second.c_str(), needed);
    *len = needed;
    return ESP_OK;
}
inline int nvs_erase_key(nvs_handle_t, const char* key) {
    if (g_nvs_fail_key == key) return ESP_FAIL;
    bool erased = g_nvs_strings.erase(key) > 0 || g_nvs_ints.erase(key) > 0;
    return erased ? ESP_OK : ESP_ERR_NVS_NOT_FOUND;
}
inline int nvs_commit(nvs_handle_t) { ++g_nvs_commit_count; return ESP_OK; }
inline void nvs_close(nvs_handle_t) {}
''',
    "main.cc": r'''
#include "wifi_configuration_ap.h"
#include "wifi_static_ip_storage.h"
#include "nvs.h"
#include <cassert>
#include <iostream>
using namespace wifi_config;

int main() {
    WifiConfigurationAp ap;
    Values last_save;
    unsigned saves = 0;
    static constexpr Translation translations[] = {
        {"zh-CN", "title", "本地"},
        {"de-DE", "title", "Deutsch"},
    };
    const std::vector<Group> config{
        {.id = "test", .title = "Test",
         .fields = {
             {.id = "port", .type = FieldType::Integer, .min = 1, .max = 65535},
             {.id = "bool", .type = FieldType::Boolean},
             {.id = "choices", .type = FieldType::TextList, .options = {{"a", std::string("a"), "A"}}},
             {.id = "key", .widget = Widget::Copy},
             {.id = "text"},
         },
         .translations = translations,
         .load = [] { return Values{{"port", int32_t{22}}, {"key", std::string("pub")}}; },
         .save = [&](const Values& values) {
             ++saves;
             last_save = values;
             return SaveResult{};
         }},
    };
    ap.SetAdvancedGroups(config);
    ap.BuildAdvancedGroups();
    httpd_req_t request;
    ap.GetAdvancedConfig(&request);
    assert(request.status == 200 && request.response.find("本地") != std::string::npos);
    assert(request.response.find("Deutsch") == std::string::npos);
    assert(request.response.find("pub") != std::string::npos);
    auto send = [&](const char* body, int status) {
        request = {.body = body, .content_len = std::strlen(body)};
        ap.SaveAdvancedConfig(&request);
        if (request.status != status) std::cerr << request.response << '\n';
        assert(request.status == status);
    };
    send(R"({"id":"test","values":{"port":22,"bool":false,"choices":[]}})", 200);
    assert(saves == 1 && std::get<int32_t>(last_save.at("port")) == 22);
    assert(!std::get<bool>(last_save.at("bool")));
    assert(std::get<std::vector<std::string>>(last_save.at("choices")).empty());
    send(R"({"id":"test","values":{"port":null}})", 200);
    assert(std::holds_alternative<std::nullptr_t>(last_save.at("port")));
    send(R"({"id":"test","values":{"port":65536}})", 400);
    send(R"({"id":"test","values":{"port":1.5}})", 400);
    send(R"({"id":"test","values":{"key":"modified"}})", 400);
    send(R"({"id":"test","values":{"port":22,"port":23}})", 400);
    send(R"({"id":"test","values":{"choices":["bad"]}})", 400);
    send(R"({"id":"test","values":{"choices":[{"too":"deep"}]}})", 400);
    send(R"({"id":"test","values":{"text":"a\u0000b"}})", 400);
    send(R"({"id":"test","values":{"text":"a\\u0000b"}})", 200);
    assert(saves == 3 && std::get<std::string>(last_save.at("text")) == "a\\u0000b");
    send(R"({"id":"test","values":{}})", 200);
    assert(saves == 3);

    // Wi-Fi group static IP: dynamic saved SSID options, validation, per-SSID scoping, and NVS error handling.
    ap.saved_ssids_ = {"HomeWiFi", "OfficeWiFi"};
    request = {};
    ap.GetAdvancedConfig(&request);
    assert(request.status == 200);
    assert(request.response.find("static_ip_enabled") != std::string::npos);
    assert(request.response.find("HomeWiFi") != std::string::npos);
    assert(request.response.find("OfficeWiFi") != std::string::npos);

    // Reject enabling static IP without a valid network / IP / gateway / netmask / subnet tuple.
    send(R"({"id":"wifi","values":{"static_ip_enabled":true}})", 400);
    assert(request.response.find("static_ip_ssid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"UnknownNet","static_ip":"192.168.1.50","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0"}})", 400);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.999","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_ip.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.255","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_ip.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.0","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_ip.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"127.0.0.1","static_gateway":"127.0.0.2","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_ip.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"224.0.0.1","static_gateway":"224.0.0.2","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_ip.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"10.0.0.1","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_gateway.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"192.168.1.50","static_netmask":"255.255.255.0"}})", 400);
    assert(request.response.find("static_gateway.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"192.168.1.1","static_netmask":"255.0.255.0"}})", 400);
    assert(request.response.find("static_netmask.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"192.168.1.1","static_netmask":"255.255.255.254"}})", 400);
    assert(request.response.find("static_netmask.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0","static_dns":"127.0.0.1"}})", 400);
    assert(request.response.find("static_dns.invalid") != std::string::npos);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0","static_dns":"192.168.1.255"}})", 400);
    assert(request.response.find("static_dns.invalid") != std::string::npos);

    // Reject editing static IP fields when static IP is disabled.
    send(R"({"id":"wifi","values":{"static_ip_enabled":false,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50"}})", 400);
    assert(request.response.find("static_ip_disabled") != std::string::npos);

    // Valid save persists a single atomic NVS record for the selected SSID.
    int commits_before = g_nvs_commit_count;
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"HomeWiFi","static_ip":"192.168.1.50","static_gateway":"192.168.1.1","static_netmask":"255.255.255.0","static_dns":"1.1.1.1"}})", 200);
    assert(g_nvs_commit_count == commits_before + 1);
    assert(ap.static_ip_enabled_ && ap.static_ip_ssid_ == "HomeWiFi");
    wifi_static_ip::StoredStaticIp loaded;
    assert(wifi_static_ip::LoadFromNvs(1, loaded));
    assert(loaded.enabled && loaded.config.ssid == "HomeWiFi" && loaded.config.ip == "192.168.1.50" &&
           loaded.config.gateway == "192.168.1.1" && loaded.config.netmask == "255.255.255.0" &&
           loaded.config.dns == "1.1.1.1");
    assert(loaded.config.AppliesTo("HomeWiFi"));
    assert(!loaded.config.AppliesTo("OfficeWiFi"));
    // Unscoped programmatic config (empty SSID) must never match any network.
    WifiStaticIpConfig unscoped{.ip = "192.168.1.50", .gateway = "192.168.1.1", .netmask = "255.255.255.0"};
    assert(!unscoped.IsValid() && !unscoped.AppliesTo("HomeWiFi") && !unscoped.AppliesTo("OfficeWiFi"));

    // NVS write failure must NOT be masked by nvs_commit(), must NOT mutate RAM, and must leave persisted record intact.
    g_nvs_fail_key = wifi_static_ip::kNvsKey;
    commits_before = g_nvs_commit_count;
    send(R"({"id":"wifi","values":{"static_ip_ssid":"OfficeWiFi","static_ip":"10.0.0.50","static_gateway":"10.0.0.1","static_netmask":"255.255.255.0"}})", 500);
    assert(request.response.find("save_failed") != std::string::npos);
    assert(g_nvs_commit_count == commits_before);
    assert(ap.static_ip_ssid_ == "HomeWiFi" && ap.static_ip_ == "192.168.1.50");
    wifi_static_ip::StoredStaticIp after_fail;
    assert(wifi_static_ip::LoadFromNvs(1, after_fail));
    assert(after_fail.enabled && after_fail.config.ssid == "HomeWiFi" &&
           after_fail.config.ip == "192.168.1.50" && after_fail.config.gateway == "192.168.1.1");
    g_nvs_fail_key.clear();

    // Mixed save failure: static_cfg succeeds, subsequent remember_bssid fails -> static_cfg must roll back to HomeWiFi.
    g_nvs_fail_key = "remember_bssid";
    send(R"({"id":"wifi","values":{"static_ip_ssid":"OfficeWiFi","static_ip":"10.0.0.50","static_gateway":"10.0.0.1","static_netmask":"255.255.255.0","remember_bssid":true}})", 500);
    assert(request.response.find("save_failed") != std::string::npos);
    assert(ap.static_ip_ssid_ == "HomeWiFi" && ap.static_ip_ == "192.168.1.50" && !ap.remember_bssid_);
    assert(wifi_static_ip::LoadFromNvs(1, after_fail));
    assert(after_fail.enabled && after_fail.config.ssid == "HomeWiFi" &&
           after_fail.config.ip == "192.168.1.50" && after_fail.config.gateway == "192.168.1.1");
    g_nvs_fail_key.clear();

    // Disabling static IP persists enabled=false while keeping stored fields for re-enabling.
    send(R"({"id":"wifi","values":{"static_ip_enabled":false}})", 200);
    assert(!ap.static_ip_enabled_);
    assert(wifi_static_ip::LoadFromNvs(1, loaded) && !loaded.enabled && loaded.config.ssid == "HomeWiFi");
    send(R"({"id":"wifi","values":{"static_ip_enabled":true}})", 200);
    assert(ap.static_ip_enabled_ && ap.static_ip_ssid_ == "HomeWiFi");
    assert(wifi_static_ip::LoadFromNvs(1, loaded) && loaded.enabled && loaded.config.ssid == "HomeWiFi");

    // Deleting the bound saved network deactivates & clears the static IP binding so unrelated Wi-Fi settings can still be saved.
    ap.saved_ssids_ = {"OfficeWiFi"};
    request = {};
    ap.GetAdvancedConfig(&request);
    assert(request.status == 200);
    assert(!ap.static_ip_enabled_ && ap.static_ip_ssid_.empty());
    assert(!wifi_static_ip::LoadFromNvs(1, loaded));
    assert(request.response.find(R"("static_ip_enabled":false)") != std::string::npos);
    send(R"({"id":"wifi","values":{"remember_bssid":true}})", 200);
    assert(ap.remember_bssid_);
    send(R"({"id":"wifi","values":{"static_ip_enabled":true}})", 400);
    assert(request.response.find("static_ip_ssid.invalid") != std::string::npos);

    // Mixed save rollback when static_cfg did not previously exist erases the newly written static_cfg.
    g_nvs_fail_key = "remember_bssid";
    send(R"({"id":"wifi","values":{"static_ip_enabled":true,"static_ip_ssid":"OfficeWiFi","static_ip":"10.0.0.50","static_gateway":"10.0.0.1","static_netmask":"255.255.255.0","remember_bssid":false}})", 500);
    assert(request.response.find("save_failed") != std::string::npos);
    assert(!ap.static_ip_enabled_ && ap.remember_bssid_);
    assert(!wifi_static_ip::LoadFromNvs(1, loaded));
    g_nvs_fail_key.clear();

    std::cout << "ESP portal HTTP/config backend accepts fragmented JSON, validates types, and returns only the requested locale.\n";
}
''',
}


STATION_FIXTURES = {
    "freertos/FreeRTOS.h": "#pragma once\n#include <cstdint>\n#define BIT0 1\n#define BIT1 2\n#define BIT2 4\n#define pdFALSE 0\n#define pdTRUE 1\n#define portTICK_PERIOD_MS 1\n",
    "freertos/event_groups.h": r'''
#pragma once
using EventGroupHandle_t = void*;
using EventBits_t = uint32_t;
inline EventGroupHandle_t xEventGroupCreate() { return reinterpret_cast<void*>(1); }
inline void vEventGroupDelete(EventGroupHandle_t) {}
inline EventBits_t xEventGroupClearBits(EventGroupHandle_t, EventBits_t) { return 0; }
inline EventBits_t xEventGroupSetBits(EventGroupHandle_t, EventBits_t) { return 0; }
inline EventBits_t xEventGroupGetBits(EventGroupHandle_t) { return 0; }
inline EventBits_t xEventGroupWaitBits(EventGroupHandle_t, EventBits_t, int, int, int) { return 0; }
''',
    "esp_idf_version.h": "#pragma once\n#define ESP_IDF_VERSION_VAL(a,b,c) ((a)*10000+(b)*100+(c))\n#define ESP_IDF_VERSION ESP_IDF_VERSION_VAL(5,5,0)\n",
    "esp_err.h": "#pragma once\nusing esp_err_t = int;\nconstexpr int ESP_OK = 0;\nconstexpr int ESP_FAIL = -1;\n#define ESP_ERROR_CHECK(x) ((void)(x))\ninline const char* esp_err_to_name(esp_err_t) { return \"ERR\"; }\n",
    "esp_log.h": "#pragma once\n#define ESP_LOGI(...) ((void)0)\n#define ESP_LOGW(...) ((void)0)\n#define ESP_LOGE(...) ((void)0)\n",
    "esp_event.h": "#pragma once\n#include \"esp_err.h\"\n#include \"freertos/FreeRTOS.h\"\n#include \"freertos/event_groups.h\"\nusing esp_event_base_t = const char*;\nusing esp_event_handler_instance_t = void*;\nusing esp_event_handler_t = void(*)(void*, esp_event_base_t, int32_t, void*);\nconstexpr const char* WIFI_EVENT = \"wifi\";\nconstexpr const char* IP_EVENT = \"ip\";\nconstexpr int32_t ESP_EVENT_ANY_ID = -1;\nconstexpr int32_t IP_EVENT_STA_GOT_IP = 1;\ninline esp_err_t esp_event_handler_instance_register(esp_event_base_t, int32_t, esp_event_handler_t, void*, esp_event_handler_instance_t* out) { *out = reinterpret_cast<void*>(1); return ESP_OK; }\ninline esp_err_t esp_event_handler_instance_unregister(esp_event_base_t, int32_t, esp_event_handler_instance_t) { return ESP_OK; }\n",
    "esp_timer.h": "#pragma once\n#include \"esp_err.h\"\nusing esp_timer_handle_t = void*;\nenum { ESP_TIMER_TASK = 0 };\nstruct esp_timer_create_args_t { void (*callback)(void*); void* arg; int dispatch_method; const char* name; bool skip_unhandled_events; };\ninline esp_err_t esp_timer_create(const esp_timer_create_args_t*, esp_timer_handle_t* out) { *out = reinterpret_cast<void*>(1); return ESP_OK; }\ninline esp_err_t esp_timer_start_once(esp_timer_handle_t, uint64_t) { return ESP_OK; }\ninline esp_err_t esp_timer_stop(esp_timer_handle_t) { return ESP_OK; }\ninline esp_err_t esp_timer_delete(esp_timer_handle_t) { return ESP_OK; }\n",
    "esp_system.h": "#pragma once\n",
    "nvs.h": "#pragma once\n#include \"esp_err.h\"\nusing nvs_handle_t = int;\nconstexpr int NVS_READONLY = 0;\ninline esp_err_t nvs_open(const char*, int, nvs_handle_t*) { return ESP_FAIL; }\ninline esp_err_t nvs_get_i8(nvs_handle_t, const char*, int8_t*) { return ESP_FAIL; }\ninline esp_err_t nvs_get_u8(nvs_handle_t, const char*, uint8_t*) { return ESP_FAIL; }\ninline void nvs_close(nvs_handle_t) {}\n",
    "nvs_flash.h": "#pragma once\n#include \"nvs.h\"\n",
    "esp_wifi_types_generic.h": r'''
#pragma once
#include <cstdint>
using wifi_auth_mode_t = int;
enum wifi_mode_t { WIFI_MODE_STA = 1 };
enum wifi_interface_t { WIFI_IF_STA = 0 };
enum wifi_ps_type_t { WIFI_PS_NONE = 0, WIFI_PS_MIN_MODEM = 1, WIFI_PS_MAX_MODEM = 2 };
enum { WIFI_FAST_SCAN = 0, WIFI_ALL_CHANNEL_SCAN = 1 };
enum { WIFI_CONNECT_AP_BY_SIGNAL = 0 };
enum { WIFI_EVENT_STA_START = 1, WIFI_EVENT_SCAN_DONE = 2, WIFI_EVENT_STA_CONNECTED = 3, WIFI_EVENT_STA_DISCONNECTED = 4 };
struct wifi_ap_record_t { uint8_t bssid[6]; uint8_t ssid[33]; uint8_t primary; int8_t rssi; wifi_auth_mode_t authmode; };
struct wifi_sta_config_t { uint8_t ssid[32]; uint8_t password[64]; int scan_method; bool bssid_set; uint8_t bssid[6]; uint8_t channel; uint16_t listen_interval; int sort_method; uint8_t failure_retry_cnt; };
union wifi_config_t { wifi_sta_config_t sta; };
struct wifi_scan_channel_bitmap_t { uint16_t ghz_2_channels; uint32_t ghz_5_channels; };
struct wifi_scan_config_t { uint8_t channel; wifi_scan_channel_bitmap_t channel_bitmap; };
struct wifi_event_sta_disconnected_t { uint8_t reason; };
#define CHANNEL_TO_BIT_NUMBER(ch) ((ch) > 0 ? 1 : 0)
#define CHANNEL_TO_BIT(ch) (1u << ((ch) & 15))
''',
    "esp_wifi.h": r'''
#pragma once
#include "esp_err.h"
#include "esp_wifi_types_generic.h"
inline int g_wifi_connect_calls = 0;
inline esp_err_t esp_wifi_set_mode(wifi_mode_t) { return ESP_OK; }
inline esp_err_t esp_wifi_start() { return ESP_OK; }
inline esp_err_t esp_wifi_stop() { return ESP_OK; }
inline esp_err_t esp_wifi_set_max_tx_power(int8_t) { return ESP_OK; }
inline esp_err_t esp_wifi_scan_start(const wifi_scan_config_t*, bool) { return ESP_OK; }
inline esp_err_t esp_wifi_scan_stop() { return ESP_OK; }
inline esp_err_t esp_wifi_scan_get_ap_num(uint16_t* n) { *n = 0; return ESP_OK; }
inline esp_err_t esp_wifi_scan_get_ap_records(uint16_t*, wifi_ap_record_t*) { return ESP_OK; }
inline esp_err_t esp_wifi_set_config(wifi_interface_t, wifi_config_t*) { return ESP_OK; }
inline esp_err_t esp_wifi_connect() { ++g_wifi_connect_calls; return ESP_OK; }
inline esp_err_t esp_wifi_disconnect() { return ESP_OK; }
inline esp_err_t esp_wifi_sta_get_ap_info(wifi_ap_record_t*) { return ESP_FAIL; }
inline esp_err_t esp_wifi_set_ps(wifi_ps_type_t) { return ESP_OK; }
''',
    "esp_netif.h": r'''
#pragma once
#include "esp_err.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
struct esp_netif_t {};
struct esp_ip4_addr_t { uint32_t addr; };
struct esp_netif_ip_info_t { esp_ip4_addr_t ip; esp_ip4_addr_t netmask; esp_ip4_addr_t gw; };
enum { ESP_IPADDR_TYPE_V4 = 0 };
enum { ESP_NETIF_DNS_MAIN = 0 };
enum esp_netif_dhcp_status_t { ESP_NETIF_DHCP_INIT = 0, ESP_NETIF_DHCP_STARTED = 1, ESP_NETIF_DHCP_STOPPED = 2 };
constexpr int ESP_ERR_ESP_NETIF_DHCP_ALREADY_STARTED = 100;
constexpr int ESP_ERR_ESP_NETIF_DHCP_ALREADY_STOPPED = 101;
struct esp_ip_addr_t { union { esp_ip4_addr_t ip4; } u_addr; uint8_t type; };
struct esp_netif_dns_info_t { esp_ip_addr_t ip; };
struct ip_event_got_ip_t { esp_netif_ip_info_t ip_info; };

struct NetifState {
    esp_netif_dhcp_status_t dhcp_status = ESP_NETIF_DHCP_INIT;
    esp_netif_ip_info_t ip_info = {};
    uint32_t dns_addr = 0;
    int dhcp_stop_calls = 0;
    int dhcp_start_calls = 0;
    int set_ip_calls = 0;
    int set_dns_calls = 0;
};
inline esp_netif_t g_netif_obj;
inline NetifState g_netif;

inline esp_netif_t* esp_netif_create_default_wifi_sta() { g_netif = {}; return &g_netif_obj; }
inline void esp_netif_destroy_default_wifi(void*) {}
inline esp_err_t esp_netif_set_hostname(esp_netif_t*, const char*) { return ESP_OK; }
inline esp_err_t esp_netif_str_to_ip4(const char* s, esp_ip4_addr_t* out) {
    unsigned a, b, c, d;
    if (std::sscanf(s, "%u.%u.%u.%u", &a, &b, &c, &d) != 4 || a > 255 || b > 255 || c > 255 || d > 255) return ESP_FAIL;
    out->addr = (a << 24) | (b << 16) | (c << 8) | d;
    return ESP_OK;
}
inline char* esp_ip4addr_ntoa(const esp_ip4_addr_t*, char* buf, int len) { std::snprintf(buf, len, "0.0.0.0"); return buf; }
inline esp_err_t esp_netif_dhcpc_get_status(esp_netif_t*, esp_netif_dhcp_status_t* out) { *out = g_netif.dhcp_status; return ESP_OK; }
inline esp_err_t esp_netif_dhcpc_stop(esp_netif_t*) {
    ++g_netif.dhcp_stop_calls;
    if (g_netif.dhcp_status == ESP_NETIF_DHCP_STOPPED) return ESP_ERR_ESP_NETIF_DHCP_ALREADY_STOPPED;
    g_netif.dhcp_status = ESP_NETIF_DHCP_STOPPED;
    return ESP_OK;
}
inline esp_err_t esp_netif_dhcpc_start(esp_netif_t*) {
    ++g_netif.dhcp_start_calls;
    if (g_netif.dhcp_status == ESP_NETIF_DHCP_STARTED) return ESP_ERR_ESP_NETIF_DHCP_ALREADY_STARTED;
    g_netif.ip_info = {};
    g_netif.dns_addr = 0;
    g_netif.dhcp_status = ESP_NETIF_DHCP_INIT;
    return ESP_OK;
}
inline esp_err_t esp_netif_set_ip_info(esp_netif_t*, const esp_netif_ip_info_t* info) {
    if (g_netif.dhcp_status != ESP_NETIF_DHCP_STOPPED) return ESP_FAIL;
    ++g_netif.set_ip_calls;
    g_netif.ip_info = *info;
    return ESP_OK;
}
inline esp_err_t esp_netif_set_dns_info(esp_netif_t*, int, esp_netif_dns_info_t* dns) {
    ++g_netif.set_dns_calls;
    g_netif.dns_addr = dns->ip.u_addr.ip4.addr;
    return ESP_OK;
}
''',
    "ssid_manager.h": r'''
#pragma once
#include <cstdint>
#include <string>
#include <vector>
struct SsidItem { std::string ssid; std::string password; uint8_t channel = 0; };
class SsidManager {
public:
    static SsidManager& GetInstance() { static SsidManager m; return m; }
    void AddSsid(const std::string&, const std::string&, uint8_t = 0) {}
    void UpdateSsidChannel(const std::string&, uint8_t) {}
    const std::vector<SsidItem>& GetSsidList() const { return list_; }
    std::vector<uint8_t> GetSavedChannels() const { return {}; }
    std::vector<SsidItem> list_;
};
''',
    "main.cc": r'''
#define private public
#include "wifi_station.h"
#undef private
#include <cassert>
#include <iostream>

static uint32_t ip4(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {
    return (uint32_t(a) << 24) | (uint32_t(b) << 16) | (uint32_t(c) << 8) | uint32_t(d);
}

int main() {
    WifiStation sta;
    sta.SetStaticIp({
        .ssid = "HomeWiFi",
        .ip = "192.168.1.50",
        .gateway = "192.168.1.1",
        .netmask = "255.255.255.0",
        .dns = "1.1.1.1",
    });
    sta.Start();

    // 1. Connect to selected static-IP SSID -> DHCP stopped, static IP + DNS applied.
    sta.connect_queue_ = {
        {.ssid = "HomeWiFi", .password = "pw1", .channel = 6},
        {.ssid = "OfficeWiFi", .password = "pw2", .channel = 11},
        {.ssid = "HomeWiFi", .password = "pw1", .channel = 6},
    };
    sta.StartConnect();
    assert(g_netif.dhcp_status == ESP_NETIF_DHCP_STOPPED);
    assert(g_netif.ip_info.ip.addr == ip4(192, 168, 1, 50));
    assert(g_netif.ip_info.gw.addr == ip4(192, 168, 1, 1));
    assert(g_netif.ip_info.netmask.addr == ip4(255, 255, 255, 0));
    assert(g_netif.dns_addr == ip4(1, 1, 1, 1));

    // 2. Switch to another saved SSID -> DHCP restored and cached static IP cleared.
    sta.StartConnect();
    assert(g_netif.dhcp_status == ESP_NETIF_DHCP_INIT);
    assert(g_netif.ip_info.ip.addr == 0);
    assert(g_netif.dns_addr == 0);
    assert(g_netif.dhcp_start_calls == 1);

    // 3. Switch back to HomeWiFi -> static IP re-applied cleanly.
    sta.StartConnect();
    assert(g_netif.dhcp_status == ESP_NETIF_DHCP_STOPPED);
    assert(g_netif.ip_info.ip.addr == ip4(192, 168, 1, 50));
    assert(g_netif.dns_addr == ip4(1, 1, 1, 1));

    // 4. Invalid static IP (broadcast) on HomeWiFi -> reverts to DHCP.
    sta.SetStaticIp({
        .ssid = "HomeWiFi",
        .ip = "192.168.1.255",
        .gateway = "192.168.1.1",
        .netmask = "255.255.255.0",
    });
    sta.connect_queue_ = {{.ssid = "HomeWiFi", .password = "pw1", .channel = 6}};
    sta.StartConnect();
    assert(g_netif.dhcp_status == ESP_NETIF_DHCP_INIT);
    assert(g_netif.ip_info.ip.addr == 0);

    std::cout << "WifiStation per-SSID static IP <-> DHCP switching verified.\n";
}
''',
}


if __name__ == "__main__":
    unittest.main()
