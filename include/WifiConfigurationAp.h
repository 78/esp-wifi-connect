#ifndef _WIFI_CONFIGURATION_AP_H_
#define _WIFI_CONFIGURATION_AP_H_

#include <string>
#include "esp_http_server.h"

class WifiConfigurationAp {
public:
    static WifiConfigurationAp& GetInstance();
    void Start(const std::string ssid_prefix);

    // 删除拷贝构造函数和赋值运算符
    WifiConfigurationAp(const WifiConfigurationAp&) = delete;
    WifiConfigurationAp& operator=(const WifiConfigurationAp&) = delete;

private:
    // 将构造函数设为私有
    WifiConfigurationAp();
    ~WifiConfigurationAp() = default;

    httpd_handle_t server_ = NULL;
    EventGroupHandle_t event_group_;
    std::string ssid_prefix_;

    std::string GetSsid();
    void StartAccessPoint();
    void StartWebServer();
    bool ConnectToWifi(const std::string &ssid, const std::string &password);
    void Save(const std::string &ssid, const std::string &password);
    static std::string UrlDecode(const std::string &url);
};

#endif // _WIFI_CONFIGURATION_AP_H_
