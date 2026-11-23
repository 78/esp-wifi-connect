message("78/esp_wifi_connect: IDF_VERSION_MAJOR is ${IDF_VERSION_MAJOR}")

if(IDF_VERSION_MAJOR GREATER_EQUAL 6)
    # v6
    message("78/esp_wifi_connect: idf_component_register for v6 used")

    idf_component_register(
        SRCS
            "wifi_manager.cc"
            "wifi_configuration_ap.cc"
            "wifi_station.cc"
            "ssid_manager.cc"
            "dns_server.cc"
            "wifi_config_group.cc"
        INCLUDE_DIRS
            "include"
        EMBED_TXTFILES
            "assets/wifi_configuration.html"
            "assets/wifi_configuration_done.html"
            "assets/wifi_config_group.js"
        REQUIRES "esp_timer" "esp_http_server" "esp_wifi" "nvs_flash"
        PRIV_REQUIRES lwip
    )
else()
    # v5
    message("78/esp_wifi_connect: idf_component_register for v5 used")

    idf_component_register(
        SRCS
            "wifi_manager.cc"
            "wifi_configuration_ap.cc"
            "wifi_station.cc"
            "ssid_manager.cc"
            "dns_server.cc"
            "wifi_config_group.cc"
        INCLUDE_DIRS
            "include"
        EMBED_TXTFILES
            "assets/wifi_configuration.html"
            "assets/wifi_configuration_done.html"
            "assets/wifi_config_group.js"
        REQUIRES "esp_timer" "esp_http_server" "esp_wifi" "nvs_flash" "json"
        PRIV_REQUIRES lwip
    )
endif()

target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_20)
