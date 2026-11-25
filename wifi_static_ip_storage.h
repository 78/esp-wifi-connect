#pragma once

#include <cstddef>
#include <memory>
#include <string>

#include <cJSON.h>
#include <nvs.h>

#include "wifi_station.h"

namespace wifi_static_ip {

inline constexpr const char* kNvsKey = "static_cfg";

struct StoredStaticIp {
    bool enabled = false;
    WifiStaticIpConfig config;
};

inline std::string EncodeRecord(const StoredStaticIp& record) {
    using Json = std::unique_ptr<cJSON, decltype(&cJSON_Delete)>;
    Json root(cJSON_CreateObject(), cJSON_Delete);
    if (!root ||
        !cJSON_AddBoolToObject(root.get(), "en", record.enabled) ||
        !cJSON_AddStringToObject(root.get(), "ssid", record.config.ssid.c_str()) ||
        !cJSON_AddStringToObject(root.get(), "ip", record.config.ip.c_str()) ||
        !cJSON_AddStringToObject(root.get(), "gw", record.config.gateway.c_str()) ||
        !cJSON_AddStringToObject(root.get(), "mask", record.config.netmask.c_str()) ||
        !cJSON_AddStringToObject(root.get(), "dns", record.config.dns.c_str())) {
        return {};
    }
    std::unique_ptr<char, decltype(&cJSON_free)> text(cJSON_PrintUnformatted(root.get()), cJSON_free);
    return text ? std::string(text.get()) : std::string{};
}

inline bool DecodeRecord(const std::string& json, StoredStaticIp& out) {
    using Json = std::unique_ptr<cJSON, decltype(&cJSON_Delete)>;
    Json root(cJSON_Parse(json.c_str()), cJSON_Delete);
    if (!cJSON_IsObject(root.get())) return false;
    StoredStaticIp parsed;
    const auto* en = cJSON_GetObjectItemCaseSensitive(root.get(), "en");
    if (!cJSON_IsBool(en)) return false;
    parsed.enabled = cJSON_IsTrue(en) != 0;
    auto read_str = [&](const char* key, std::string& dst, size_t max_len) {
        const auto* item = cJSON_GetObjectItemCaseSensitive(root.get(), key);
        if (!item) return true;
        if (!cJSON_IsString(item) || !item->valuestring) return false;
        std::string val = item->valuestring;
        if (val.size() > max_len) return false;
        dst = std::move(val);
        return true;
    };
    if (!read_str("ssid", parsed.config.ssid, 32) ||
        !read_str("ip", parsed.config.ip, 15) ||
        !read_str("gw", parsed.config.gateway, 15) ||
        !read_str("mask", parsed.config.netmask, 15) ||
        !read_str("dns", parsed.config.dns, 15)) {
        return false;
    }
    out = std::move(parsed);
    return true;
}

inline bool LoadFromNvs(nvs_handle_t nvs, StoredStaticIp& out) {
    size_t len = 0;
    if (nvs_get_str(nvs, kNvsKey, nullptr, &len) != ESP_OK || len <= 1 || len > 512) {
        return false;
    }
    std::string buf(len, '\0');
    if (nvs_get_str(nvs, kNvsKey, buf.data(), &len) != ESP_OK || len <= 1) {
        return false;
    }
    buf.resize(len - 1);
    return DecodeRecord(buf, out);
}

} // namespace wifi_static_ip
