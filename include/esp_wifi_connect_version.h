#pragma once

#define ESP_WIFI_CONNECT_VERSION_MAJOR 3
#define ESP_WIFI_CONNECT_VERSION_MINOR 2
#define ESP_WIFI_CONNECT_VERSION_PATCH 2

#define ESP_WIFI_CONNECT_VERSION \
    (ESP_WIFI_CONNECT_VERSION_MAJOR * 10000 + \
     ESP_WIFI_CONNECT_VERSION_MINOR * 100 + \
     ESP_WIFI_CONNECT_VERSION_PATCH)

#define ESP_WIFI_CONNECT_VERSION_STRING "3.2.2"

/**
 * Compile-time check that the installed component is at least the given version.
 *
 * Example:
 *   ESP_WIFI_CONNECT_VERSION_MIN_CHECK(3, 2, 2)
 */
#define ESP_WIFI_CONNECT_VERSION_MIN_CHECK(major, minor, patch) \
    static_assert( \
        ESP_WIFI_CONNECT_VERSION >= ((major) * 10000 + (minor) * 100 + (patch)), \
        "esp-wifi-connect version " #major "." #minor "." #patch " or later required" \
    )
