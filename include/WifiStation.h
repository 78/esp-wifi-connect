#ifndef _WIFI_STATION_H_
#define _WIFI_STATION_H_

#include <string>
#include "esp_event.h"

class WifiStation {
public:
    static WifiStation& GetInstance();
    void Start();
    bool IsConnected();
    std::string ssid() const { return ssid_; }
    std::string ip_address() const { return ip_address_; }
    int8_t rssi() const { return rssi_; }
    uint8_t channel() const { return channel_; }

private:
    WifiStation();
    ~WifiStation();
    WifiStation(const WifiStation&) = delete;
    WifiStation& operator=(const WifiStation&) = delete;

    EventGroupHandle_t event_group_;
    std::string ssid_;
    std::string password_;
    std::string ip_address_;
    uint8_t rssi_ = 0;
    uint8_t channel_ = 0;
    int reconnect_count_ = 0;

    static void WifiEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);
    static void IpEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);
};

#endif // _WIFI_STATION_H_
