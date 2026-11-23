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
                "-I", str(build), "-I", str(ROOT / "include"), "-I", str(cjson),
                str(build / "main.cc"), str(ROOT / "wifi_config_group.cc"), str(build / "cjson.o"),
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
    void BuildAdvancedGroups();
    esp_err_t GetAdvancedConfig(httpd_req_t* req);
    esp_err_t SaveAdvancedConfig(httpd_req_t* req);
    std::vector<wifi_config::Group> advanced_groups_;
    int8_t max_tx_power_ = 80;
    bool remember_bssid_ = false;
};
''',
    "esp_wifi.h": r'''
#pragma once
inline int esp_wifi_set_max_tx_power(int8_t) { return ESP_OK; }
''',
    "nvs.h": r'''
#pragma once
using nvs_handle_t = int;
constexpr int NVS_READWRITE = 1;
inline int nvs_open(const char*, int, nvs_handle_t* out) { *out = 1; return ESP_OK; }
inline int nvs_set_i8(nvs_handle_t, const char*, int8_t) { return ESP_OK; }
inline int nvs_set_u8(nvs_handle_t, const char*, uint8_t) { return ESP_OK; }
inline int nvs_commit(nvs_handle_t) { return ESP_OK; }
inline void nvs_close(nvs_handle_t) {}
''',
    "main.cc": r'''
#include "wifi_configuration_ap.h"
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
    std::cout << "ESP portal HTTP/config backend accepts fragmented JSON, validates types, and returns only the requested locale.\n";
}
''',
}


if __name__ == "__main__":
    unittest.main()
