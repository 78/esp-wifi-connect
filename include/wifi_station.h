#ifndef _WIFI_STATION_H_
#define _WIFI_STATION_H_

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>
#include <functional>

#include <esp_event.h>
#include <esp_timer.h>
#include <esp_netif.h>
#include <esp_wifi_types_generic.h>

// WiFi power save level enumeration
enum class WifiPowerSaveLevel {
    LOW_POWER,    // Maximum power saving (WIFI_PS_MAX_MODEM)
    BALANCED,     // Minimum power saving (WIFI_PS_MIN_MODEM)
    PERFORMANCE,  // No power saving (WIFI_PS_NONE) - full power
};

// Validation result for WifiStaticIpConfig.
enum class WifiStaticIpError {
    Ok,
    InvalidSsid,
    InvalidIp,
    InvalidGateway,
    InvalidNetmask,
    InvalidDns,
};

// Optional static IP for station mode. Static IP applies only to the specified
// Wi-Fi network (ssid) and all other saved networks use DHCP. All of
// ssid/ip/gateway/netmask must be set and form a valid IPv4 subnet tuple for it
// to take effect; anything else keeps DHCP. dns is optional and defaults to the
// gateway.
struct WifiStaticIpConfig {
    std::string ssid;
    std::string ip;
    std::string gateway;
    std::string netmask;
    std::string dns;

    // Nothing was configured at all, as opposed to a partially filled config.
    bool IsEmpty() const {
        return ssid.empty() && ip.empty() && gateway.empty() && netmask.empty() && dns.empty();
    }

    static bool ParseIpv4(std::string_view text, uint32_t& out) {
        if (text.empty() || text.size() > 15) return false;
        uint32_t addr = 0;
        size_t pos = 0;
        for (int part = 0; part < 4; ++part) {
            if (pos >= text.size()) return false;
            size_t start = pos;
            uint32_t value = 0;
            while (pos < text.size() && text[pos] != '.') {
                const char ch = text[pos];
                if (ch < '0' || ch > '9') return false;
                value = value * 10 + static_cast<uint32_t>(ch - '0');
                if (value > 255) return false;
                ++pos;
            }
            const size_t digits = pos - start;
            if (digits == 0 || (digits > 1 && text[start] == '0')) return false;
            addr = (addr << 8) | value;
            if (part < 3) {
                if (pos >= text.size() || text[pos] != '.') return false;
                ++pos;
            }
        }
        if (pos != text.size()) return false;
        out = addr;
        return true;
    }

    static bool IsValidUnicastIpv4(uint32_t addr) {
        const uint32_t first = addr >> 24;
        // Reject 0.0.0.0/8, loopback 127.0.0.0/8, multicast/reserved >= 224.0.0.0.
        return first != 0 && first != 127 && first < 224;
    }

    static bool IsValidSubnetMask(uint32_t mask) {
        // Contiguous 1-bits followed by 0-bits, /1 through /30 (at least 2 hosts).
        if (mask == 0 || mask > 0xFFFFFFFCu) return false;
        const uint32_t inv = ~mask;
        return (inv & (inv + 1u)) == 0;
    }

    WifiStaticIpError Validate() const {
        if (ssid.empty() || ssid.size() > 32) return WifiStaticIpError::InvalidSsid;
        uint32_t ip_addr = 0;
        uint32_t gw_addr = 0;
        uint32_t mask_addr = 0;
        if (!ParseIpv4(netmask, mask_addr) || !IsValidSubnetMask(mask_addr)) {
            return WifiStaticIpError::InvalidNetmask;
        }
        const uint32_t host_mask = ~mask_addr;
        if (!ParseIpv4(ip, ip_addr) || !IsValidUnicastIpv4(ip_addr) ||
            (ip_addr & host_mask) == 0 || (ip_addr & host_mask) == host_mask) {
            return WifiStaticIpError::InvalidIp;
        }
        if (!ParseIpv4(gateway, gw_addr) || !IsValidUnicastIpv4(gw_addr) ||
            (gw_addr & host_mask) == 0 || (gw_addr & host_mask) == host_mask ||
            (ip_addr & mask_addr) != (gw_addr & mask_addr) || gw_addr == ip_addr) {
            return WifiStaticIpError::InvalidGateway;
        }
        if (!dns.empty()) {
            uint32_t dns_addr = 0;
            if (!ParseIpv4(dns, dns_addr) || !IsValidUnicastIpv4(dns_addr)) {
                return WifiStaticIpError::InvalidDns;
            }
            if ((dns_addr & mask_addr) == (ip_addr & mask_addr) &&
                ((dns_addr & host_mask) == 0 || (dns_addr & host_mask) == host_mask)) {
                return WifiStaticIpError::InvalidDns;
            }
        }
        return WifiStaticIpError::Ok;
    }

    bool IsValid() const {
        return Validate() == WifiStaticIpError::Ok;
    }

    // Applies only when valid and matching target_ssid; all other networks use DHCP.
    bool AppliesTo(const std::string& target_ssid) const {
        return IsValid() && ssid == target_ssid;
    }
};

struct WifiApRecord {
    std::string ssid;
    std::string password;
    int channel;
    wifi_auth_mode_t authmode;
    uint8_t bssid[6];
};

/**
 * WifiStation - WiFi station mode handler
 * 
 * This class handles connecting to WiFi access points in station mode.
 * Note: WiFi driver must be initialized before using this class.
 */
class WifiStation {
public:
    WifiStation();
    ~WifiStation();

    // Delete copy constructor and assignment operator
    WifiStation(const WifiStation&) = delete;
    WifiStation& operator=(const WifiStation&) = delete;

    void AddAuth(const std::string &&ssid, const std::string &&password);
    void Start();
    void Stop();
    bool IsConnected();
    bool WaitForConnected(int timeout_ms = 10000);
    int8_t GetRssi();
    std::string GetSsid() const { return ssid_; }
    std::string GetIpAddress() const { return ip_address_; }
    uint8_t GetChannel();
    void SetPowerSaveLevel(WifiPowerSaveLevel level);

    void OnConnect(std::function<void(const std::string& ssid)> on_connect);
    void OnConnected(std::function<void(const std::string& ssid)> on_connected);
    void OnDisconnected(std::function<void(int reason)> on_disconnected);
    void OnScanBegin(std::function<void()> on_scan_begin);
    void SetScanIntervalRange(int min_interval_seconds, int max_interval_seconds);
    void SetHostname(const std::string& hostname) { hostname_ = hostname; }

    // Static IP for station mode. Must be set before Start(); an empty or
    // incomplete config leaves the interface on DHCP. When static_ip.ssid is
    // set, static IP is applied only when connecting to that SSID and DHCP is
    // used for all other networks.
    void SetStaticIp(const WifiStaticIpConfig& static_ip) { static_ip_ = static_ip; }

    // How many times to retry the strongest same-SSID AP before falling back to
    // a weaker one. Only effective when remember_bssid is off (default). A value
    // of 3 means the driver will attempt the best AP up to 3 extra times before
    // giving up and trying the next-best BSSID.
    void SetFailureRetryCnt(uint8_t cnt) { failure_retry_cnt_ = cnt; }

private:
    EventGroupHandle_t event_group_;
    esp_timer_handle_t timer_handle_ = nullptr;
    esp_event_handler_instance_t instance_any_id_ = nullptr;
    esp_event_handler_instance_t instance_got_ip_ = nullptr;
    esp_netif_t* station_netif_ = nullptr;
    std::string ssid_;
    std::string password_;
    std::string ip_address_;
    std::string hostname_;
    WifiStaticIpConfig static_ip_;
    int8_t max_tx_power_;
    uint8_t remember_bssid_;
    uint8_t failure_retry_cnt_ = 3;  // Retries on strongest AP before falling back
    int reconnect_count_ = 0;

    // Exponential backoff for scan interval
    int scan_min_interval_microseconds_ = 10 * 1000 * 1000;   // Default 10 seconds
    int scan_max_interval_microseconds_ = 300 * 1000 * 1000;  // Default 5 minutes
    int scan_current_interval_microseconds_ = 10 * 1000 * 1000;  // Current interval
    std::function<void(const std::string& ssid)> on_connect_;
    std::function<void(const std::string& ssid)> on_connected_;
    std::function<void(int reason)> on_disconnected_;
    std::function<void()> on_scan_begin_;
    std::vector<WifiApRecord> connect_queue_;
    bool was_connected_ = false;  // Track if we were connected before disconnection
    bool use_saved_channels_scan_ = true;       // First scan uses saved channels when known
    bool last_scan_used_saved_channels_ = false;

    void StartScan();
    void HandleScanResult();
    void StartConnect();
    void ConfigureIpForSsid(const std::string& ssid);
    void RestoreDhcp();
    void UpdateScanInterval();  // Exponential backoff for scan interval
    static void WifiEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);
    static void IpEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);
};

#endif // _WIFI_STATION_H_
