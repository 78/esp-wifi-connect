#include "ssid_manager.h"
#include "wifi_static_ip_storage.h"

#include <algorithm>
#include <esp_log.h>
#include <nvs_flash.h>

#define TAG "SsidManager"
#define NVS_NAMESPACE "wifi"
#define MAX_WIFI_SSID_COUNT 10

static std::string MakeWifiKey(const char* prefix, int index) {
    if (index <= 0) {
        return prefix;
    }
    return std::string(prefix) + std::to_string(index);
}

SsidManager::SsidManager() {
    LoadFromNvs();
}

SsidManager::~SsidManager() {
}

void SsidManager::Clear() {
    ssid_list_.clear();
    SaveToNvs();
}

void SsidManager::LoadFromNvs() {
    ssid_list_.clear();

    // Load ssid / password / channel from NVS namespace "wifi"
    // ssid, ssid1, ... ssid9
    // password, password1, ... password9
    // channel, channel1, ... channel9 (uint8, optional; missing means unknown)
    nvs_handle_t nvs_handle;
    auto ret = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (ret != ESP_OK) {
        // The namespace doesn't exist, just return
        ESP_LOGW(TAG, "NVS namespace %s doesn't exist", NVS_NAMESPACE);
        return;
    }
    for (int i = 0; i < MAX_WIFI_SSID_COUNT; i++) {
        auto ssid_key = MakeWifiKey("ssid", i);
        auto password_key = MakeWifiKey("password", i);
        auto channel_key = MakeWifiKey("channel", i);

        char ssid[33];
        char password[65];
        size_t length = sizeof(ssid);
        if (nvs_get_str(nvs_handle, ssid_key.c_str(), ssid, &length) != ESP_OK) {
            continue;
        }
        length = sizeof(password);
        if (nvs_get_str(nvs_handle, password_key.c_str(), password, &length) != ESP_OK) {
            continue;
        }
        uint8_t channel = 0;
        nvs_get_u8(nvs_handle, channel_key.c_str(), &channel);
        ssid_list_.push_back({ssid, password, channel});
    }
    nvs_close(nvs_handle);
}

void SsidManager::SaveToNvs() {
    nvs_handle_t nvs_handle;
    ESP_ERROR_CHECK(nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs_handle));
    for (int i = 0; i < MAX_WIFI_SSID_COUNT; i++) {
        auto ssid_key = MakeWifiKey("ssid", i);
        auto password_key = MakeWifiKey("password", i);
        auto channel_key = MakeWifiKey("channel", i);

        if (i < ssid_list_.size()) {
            nvs_set_str(nvs_handle, ssid_key.c_str(), ssid_list_[i].ssid.c_str());
            nvs_set_str(nvs_handle, password_key.c_str(), ssid_list_[i].password.c_str());
            nvs_set_u8(nvs_handle, channel_key.c_str(), ssid_list_[i].channel);
        } else {
            nvs_erase_key(nvs_handle, ssid_key.c_str());
            nvs_erase_key(nvs_handle, password_key.c_str());
            nvs_erase_key(nvs_handle, channel_key.c_str());
        }
    }
    wifi_static_ip::StoredStaticIp stored_static;
    if (wifi_static_ip::LoadFromNvs(nvs_handle, stored_static) && !stored_static.config.ssid.empty()) {
        const bool still_saved = std::any_of(
            ssid_list_.begin(), ssid_list_.end(),
            [&](const SsidItem& item) { return item.ssid == stored_static.config.ssid; });
        if (!still_saved) {
            ESP_LOGI(TAG, "Clearing static IP binding for removed SSID %s", stored_static.config.ssid.c_str());
            nvs_erase_key(nvs_handle, wifi_static_ip::kNvsKey);
        }
    }
    nvs_commit(nvs_handle);
    nvs_close(nvs_handle);
}

void SsidManager::AddSsid(const std::string& ssid, const std::string& password, uint8_t channel) {
    for (auto& item : ssid_list_) {
        ESP_LOGI(TAG, "compare [%s:%d] [%s:%d]", item.ssid.c_str(), item.ssid.size(), ssid.c_str(),
                 ssid.size());
        if (item.ssid == ssid) {
            ESP_LOGW(TAG, "SSID %s already exists, overwrite it", ssid.c_str());
            item.password = password;
            if (channel != 0) {
                item.channel = channel;
            }
            SaveToNvs();
            return;
        }
    }

    if (ssid_list_.size() >= MAX_WIFI_SSID_COUNT) {
        ESP_LOGW(TAG, "SSID list is full, pop one");
        ssid_list_.pop_back();
    }
    // Add the new ssid to the front of the list
    ssid_list_.insert(ssid_list_.begin(), {ssid, password, channel});
    SaveToNvs();
}

void SsidManager::UpdateSsidChannel(const std::string& ssid, uint8_t channel) {
    if (channel == 0) {
        return;
    }
    for (auto& item : ssid_list_) {
        if (item.ssid != ssid) {
            continue;
        }
        if (item.channel != channel) {
            ESP_LOGI(TAG, "Updated channel for %s: %u -> %u", ssid.c_str(), item.channel, channel);
            item.channel = channel;
            SaveToNvs();
        }
        return;
    }
}

void SsidManager::RemoveSsid(int index) {
    if (index < 0 || index >= ssid_list_.size()) {
        ESP_LOGW(TAG, "Invalid index %d", index);
        return;
    }
    ssid_list_.erase(ssid_list_.begin() + index);
    SaveToNvs();
}

void SsidManager::SetDefaultSsid(int index) {
    if (index < 0 || index >= ssid_list_.size()) {
        ESP_LOGW(TAG, "Invalid index %d", index);
        return;
    }
    // Move the ssid at index to the front of the list
    auto item = ssid_list_[index];
    ssid_list_.erase(ssid_list_.begin() + index);
    ssid_list_.insert(ssid_list_.begin(), item);
    SaveToNvs();
}

std::vector<uint8_t> SsidManager::GetSavedChannels() const {
    std::vector<uint8_t> channels;
    for (const auto& item : ssid_list_) {
        if (item.channel == 0) {
            continue;
        }
        if (std::find(channels.begin(), channels.end(), item.channel) == channels.end()) {
            channels.push_back(item.channel);
        }
    }
    return channels;
}
