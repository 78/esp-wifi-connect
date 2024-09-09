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
    ~WifiStation() = default;
    WifiStation(const WifiStation&) = delete;
    WifiStation& operator=(const WifiStation&) = delete;

    EventGroupHandle_t event_group_;
    std::string ssid_;
    std::string password_;
    std::string ip_address_;
    uint8_t rssi_ = 0;
    uint8_t channel_ = 0;
    int reconnect_count_ = 0;
};

#endif // _WIFI_STATION_H_
