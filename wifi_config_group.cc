#include "wifi_configuration_ap.h"

#include <algorithm>
#include <cmath>
#include <memory>
#include <string_view>

#include <cJSON.h>
#include <esp_wifi.h>
#include <nvs.h>

namespace {
using namespace wifi_config;
using Json = std::unique_ptr<cJSON, decltype(&cJSON_Delete)>;

constexpr size_t kMaxSubmitBytes = 8192;
constexpr Translation kWifiTranslations[] = {
    {"ar-SA", "title", "تكوين Wi-Fi"},
    {"ar-SA", "max_tx_power.label", "قدرة الإرسال القصوى"},
    {"ar-SA", "remember_bssid.label", "تذكّر BSSID"},
    {"bg-BG", "title", "Конфигурация на Wi-Fi"},
    {"bg-BG", "max_tx_power.label", "Макс. мощност на предаване"},
    {"bg-BG", "remember_bssid.label", "Запомняне на BSSID"},
    {"ca-ES", "title", "Configuració Wi-Fi"},
    {"ca-ES", "max_tx_power.label", "Potència màxima de transmissió"},
    {"ca-ES", "remember_bssid.label", "Recorda el BSSID"},
    {"cs-CZ", "title", "Konfigurace Wi-Fi"},
    {"cs-CZ", "max_tx_power.label", "Max. vysílací výkon"},
    {"cs-CZ", "remember_bssid.label", "Pamatovat si BSSID"},
    {"da-DK", "title", "Wi-Fi-konfiguration"},
    {"da-DK", "max_tx_power.label", "Maks. sendeeffekt"},
    {"da-DK", "remember_bssid.label", "Husk BSSID"},
    {"de-DE", "title", "Wi-Fi-Konfiguration"},
    {"de-DE", "max_tx_power.label", "Max. Sendeleistung"},
    {"de-DE", "remember_bssid.label", "BSSID merken"},
    {"el-GR", "title", "Διαμόρφωση Wi-Fi"},
    {"el-GR", "max_tx_power.label", "Μέγ. ισχύς εκπομπής"},
    {"el-GR", "remember_bssid.label", "Απομνημόνευση BSSID"},
    {"es-ES", "title", "Configuración Wi-Fi"},
    {"es-ES", "max_tx_power.label", "Potencia máxima de transmisión"},
    {"es-ES", "remember_bssid.label", "Recordar BSSID"},
    {"fa-IR", "title", "پیکربندی Wi-Fi"},
    {"fa-IR", "max_tx_power.label", "حداکثر توان ارسال"},
    {"fa-IR", "remember_bssid.label", "ذخیرهٔ BSSID"},
    {"fi-FI", "title", "Wi-Fi-määritys"},
    {"fi-FI", "max_tx_power.label", "Suurin lähetysteho"},
    {"fi-FI", "remember_bssid.label", "Muista BSSID"},
    {"fil-PH", "title", "Pagsasaayos ng Wi-Fi"},
    {"fil-PH", "max_tx_power.label", "Pinakamataas na lakas ng pagpapadala"},
    {"fil-PH", "remember_bssid.label", "Tandaan ang BSSID"},
    {"fr-FR", "title", "Configuration Wi-Fi"},
    {"fr-FR", "max_tx_power.label", "Puissance d'émission maximale "},
    {"fr-FR", "remember_bssid.label", "Mémoriser le BSSID"},
    {"he-IL", "title", "הגדרות Wi-Fi"},
    {"he-IL", "max_tx_power.label", "עוצמת שידור מרבית"},
    {"he-IL", "remember_bssid.label", "שמירת BSSID"},
    {"hi-IN", "title", "Wi-Fi कॉन्फ़िगरेशन"},
    {"hi-IN", "max_tx_power.label", "अधिकतम प्रेषण शक्ति"},
    {"hi-IN", "remember_bssid.label", "BSSID याद रखें"},
    {"hr-HR", "title", "Konfiguracija Wi-Fi"},
    {"hr-HR", "max_tx_power.label", "Maks. snaga odašiljanja"},
    {"hr-HR", "remember_bssid.label", "Zapamti BSSID"},
    {"hu-HU", "title", "Wi-Fi konfiguráció"},
    {"hu-HU", "max_tx_power.label", "Max. adási teljesítmény"},
    {"hu-HU", "remember_bssid.label", "BSSID megjegyzése"},
    {"id-ID", "title", "Konfigurasi Wi-Fi"},
    {"id-ID", "max_tx_power.label", "Daya pancar maksimum"},
    {"id-ID", "remember_bssid.label", "Ingat BSSID"},
    {"it-IT", "title", "Configurazione Wi-Fi"},
    {"it-IT", "max_tx_power.label", "Potenza massima di trasmissione"},
    {"it-IT", "remember_bssid.label", "Ricorda BSSID"},
    {"ja-JP", "title", "Wi-Fi設定"},
    {"ja-JP", "max_tx_power.label", "最大送信電力"},
    {"ja-JP", "remember_bssid.label", "BSSID を記憶"},
    {"ko-KR", "title", "Wi-Fi 구성"},
    {"ko-KR", "max_tx_power.label", "최대 송신 출력"},
    {"ko-KR", "remember_bssid.label", "BSSID 기억"},
    {"ms-MY", "title", "Konfigurasi Wi-Fi"},
    {"ms-MY", "max_tx_power.label", "Kuasa pancaran maksimum"},
    {"ms-MY", "remember_bssid.label", "Ingat BSSID"},
    {"nb-NO", "title", "Wi-Fi-konfigurasjon"},
    {"nb-NO", "max_tx_power.label", "Maks. sendeeffekt"},
    {"nb-NO", "remember_bssid.label", "Husk BSSID"},
    {"nl-NL", "title", "Wi-Fi-configuratie"},
    {"nl-NL", "max_tx_power.label", "Max. zendvermogen"},
    {"nl-NL", "remember_bssid.label", "BSSID onthouden"},
    {"pl-PL", "title", "Konfiguracja Wi-Fi"},
    {"pl-PL", "max_tx_power.label", "Maks. moc nadawania"},
    {"pl-PL", "remember_bssid.label", "Zapamiętaj BSSID"},
    {"pt-PT", "title", "Configuração Wi-Fi"},
    {"pt-PT", "max_tx_power.label", "Potência máxima de transmissão"},
    {"pt-PT", "remember_bssid.label", "Memorizar BSSID"},
    {"ro-RO", "title", "Configurare Wi-Fi"},
    {"ro-RO", "max_tx_power.label", "Putere maximă de transmisie"},
    {"ro-RO", "remember_bssid.label", "Memorează BSSID"},
    {"ru-RU", "title", "Настройка Wi-Fi"},
    {"ru-RU", "max_tx_power.label", "Макс. мощность передачи"},
    {"ru-RU", "remember_bssid.label", "Запомнить BSSID"},
    {"sk-SK", "title", "Konfigurácia Wi-Fi"},
    {"sk-SK", "max_tx_power.label", "Max. vysielací výkon"},
    {"sk-SK", "remember_bssid.label", "Zapamätať BSSID"},
    {"sl-SI", "title", "Konfiguracija Wi-Fi"},
    {"sl-SI", "max_tx_power.label", "Največja oddajna moč"},
    {"sl-SI", "remember_bssid.label", "Zapomni si BSSID"},
    {"sr-RS", "title", "Конфигурација Wi-Fi"},
    {"sr-RS", "max_tx_power.label", "Макс. снага предаје"},
    {"sr-RS", "remember_bssid.label", "Запамти BSSID"},
    {"sv-SE", "title", "Wi-Fi-konfiguration"},
    {"sv-SE", "max_tx_power.label", "Max. sändningseffekt"},
    {"sv-SE", "remember_bssid.label", "Kom ihåg BSSID"},
    {"th-TH", "title", "การกำหนดค่า Wi-Fi"},
    {"th-TH", "max_tx_power.label", "กำลังส่งสูงสุด"},
    {"th-TH", "remember_bssid.label", "จดจำ BSSID"},
    {"tr-TR", "title", "Wi-Fi Yapılandırması"},
    {"tr-TR", "max_tx_power.label", "En yüksek iletim gücü"},
    {"tr-TR", "remember_bssid.label", "BSSID'yi hatırla"},
    {"uk-UA", "title", "Налаштування Wi-Fi"},
    {"uk-UA", "max_tx_power.label", "Макс. потужність передавання"},
    {"uk-UA", "remember_bssid.label", "Запам'ятати BSSID"},
    {"vi-VN", "title", "Cấu hình Wi-Fi"},
    {"vi-VN", "max_tx_power.label", "Công suất phát tối đa"},
    {"vi-VN", "remember_bssid.label", "Ghi nhớ BSSID"},
    {"zh-CN", "title", "Wi-Fi 配置"},
    {"zh-CN", "max_tx_power.label", "最大发射功率"},
    {"zh-CN", "remember_bssid.label", "记住 BSSID"},
    {"zh-TW", "title", "Wi-Fi 設定"},
    {"zh-TW", "max_tx_power.label", "最大發射功率"},
    {"zh-TW", "remember_bssid.label", "記住 BSSID"},
};
constexpr const char* kTypes[] = {"string", "integer", "boolean", "string[]"};
constexpr const char* kWidgets[] = {"", "text", "textarea", "number", "switch",
                                     "select", "radio", "checkboxes", "copy"};

cJSON* EncodeValue(const Value& value) {
    if (auto text = std::get_if<std::string>(&value)) return cJSON_CreateString(text->c_str());
    if (auto number = std::get_if<int32_t>(&value)) return cJSON_CreateNumber(*number);
    if (auto boolean = std::get_if<bool>(&value)) return cJSON_CreateBool(*boolean);
    if (auto list = std::get_if<std::vector<std::string>>(&value)) {
        auto* array = cJSON_CreateArray();
        for (const auto& item : *list) cJSON_AddItemToArray(array, cJSON_CreateString(item.c_str()));
        return array;
    }
    return cJSON_CreateNull();
}

bool HasOption(const Field& field, const Value& value) {
    return std::any_of(field.options.begin(), field.options.end(),
                       [&](const Option& option) { return option.value == value; });
}

bool DecodeValue(const cJSON* node, const Field& field, Value& value) {
    if (cJSON_IsNull(node)) {
        value = nullptr;
        return field.type == FieldType::Integer && !field.required && field.options.empty();
    }
    switch (field.type) {
        case FieldType::Text:
            if (!cJSON_IsString(node)) return false;
            value = std::string(node->valuestring);
            {
                auto size = std::get<std::string>(value).size();
                if ((field.required && size == 0) || (field.max_length && size > field.max_length)) return false;
            }
            break;
        case FieldType::Integer:
            if (!cJSON_IsNumber(node) || !std::isfinite(node->valuedouble) ||
                node->valuedouble < field.min || node->valuedouble > field.max ||
                node->valuedouble != std::trunc(node->valuedouble)) return false;
            value = static_cast<int32_t>(node->valuedouble);
            break;
        case FieldType::Boolean:
            if (!cJSON_IsBool(node)) return false;
            value = cJSON_IsTrue(node) != 0;
            break;
        case FieldType::TextList: {
            if (!cJSON_IsArray(node) || cJSON_GetArraySize(node) > static_cast<int>(field.options.size())) return false;
            std::vector<std::string> selected;
            const cJSON* item = nullptr;
            cJSON_ArrayForEach(item, node) {
                if (!cJSON_IsString(item) || !HasOption(field, std::string(item->valuestring)) ||
                    std::find(selected.begin(), selected.end(), item->valuestring) != selected.end()) return false;
                selected.emplace_back(item->valuestring);
            }
            if (field.required && selected.empty()) return false;
            value = std::move(selected);
            return true;
        }
    }
    return field.options.empty() || HasOption(field, value);
}

bool IsSettingsBody(std::string_view body) {
    unsigned depth = 0;
    bool in_string = false;
    for (size_t i = 0; i < body.size(); ++i) {
        const char character = body[i];
        if (character == '"') {
            in_string = !in_string;
        } else if (in_string && character == '\\') {
            // cJSON stores decoded strings as NUL-terminated text.
            if (body.substr(i, 6) == "\\u0000") return false;
            ++i;
        } else if (!in_string && (character == '{' || character == '[')) {
            if (++depth > 3) return false;
        } else if (!in_string && (character == '}' || character == ']')) {
            if (!depth) return false;
            --depth;
        }
    }
    return !in_string && !depth;
}

esp_err_t SendJson(httpd_req_t* req, const cJSON* document) {
    std::unique_ptr<char, decltype(&cJSON_free)> body(cJSON_PrintUnformatted(document), cJSON_free);
    if (!body) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Cannot encode settings");
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    return httpd_resp_sendstr(req, body.get());
}

esp_err_t SendResult(httpd_req_t* req, const SaveResult& result) {
    Json document(cJSON_CreateObject(), cJSON_Delete);
    if (!document) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Cannot encode settings");
    cJSON_AddBoolToObject(document.get(), "success", result.error.empty());
    if (!result.error.empty()) {
        httpd_resp_set_status(req, result.key == "save_failed" ? "500 Internal Server Error" : "400 Bad Request");
        cJSON_AddStringToObject(document.get(), "error", result.error.c_str());
        cJSON_AddStringToObject(document.get(), "key", result.key.c_str());
        cJSON_AddStringToObject(document.get(), "field", result.field.c_str());
    }
    return SendJson(req, document.get());
}

bool AddGroup(cJSON* list, const Group& group, const std::string& locale) {
    auto* entry = cJSON_CreateObject();
    if (!entry || !cJSON_AddItemToArray(list, entry)) {
        cJSON_Delete(entry);
        return false;
    }
    cJSON_AddStringToObject(entry, "id", group.id.c_str());
    cJSON_AddStringToObject(entry, "title", group.title.c_str());
    if (!group.help.empty()) cJSON_AddStringToObject(entry, "help", group.help.c_str());
    auto* fields = cJSON_AddArrayToObject(entry, "fields");
    if (!fields) return false;
    for (const auto& field : group.fields) {
        auto* item = cJSON_CreateObject();
        if (!item || !cJSON_AddItemToArray(fields, item)) {
            cJSON_Delete(item);
            return false;
        }
        cJSON_AddStringToObject(item, "id", field.id.c_str());
        cJSON_AddStringToObject(item, "type", kTypes[static_cast<size_t>(field.type)]);
        if (field.widget != Widget::Default) {
            cJSON_AddStringToObject(item, "widget", kWidgets[static_cast<size_t>(field.widget)]);
        }
        cJSON_AddStringToObject(item, "label", field.label.c_str());
        if (!field.help.empty()) cJSON_AddStringToObject(item, "help", field.help.c_str());
        if (!field.unit.empty()) cJSON_AddStringToObject(item, "unit", field.unit.c_str());
        if (field.required) cJSON_AddTrueToObject(item, "required");
        if (field.min != INT32_MIN) cJSON_AddNumberToObject(item, "min", field.min);
        if (field.max != INT32_MAX) cJSON_AddNumberToObject(item, "max", field.max);
        if (field.max_length) cJSON_AddNumberToObject(item, "max_length", field.max_length);
        if (!field.enabled_by.empty()) cJSON_AddStringToObject(item, "enabled_by", field.enabled_by.c_str());
        if (field.clearable) cJSON_AddTrueToObject(item, "clearable");
        if (field.options.empty()) continue;
        auto* options = cJSON_AddArrayToObject(item, "options");
        if (!options) return false;
        for (const auto& option : field.options) {
            auto* node = cJSON_CreateObject();
            if (!node || !cJSON_AddItemToArray(options, node)) {
                cJSON_Delete(node);
                return false;
            }
            cJSON_AddStringToObject(node, "id", option.id.c_str());
            cJSON_AddStringToObject(node, "label", option.label.c_str());
            cJSON_AddItemToObject(node, "value", EncodeValue(option.value));
        }
    }
    auto* values = cJSON_AddObjectToObject(entry, "values");
    if (!values) return false;
    if (group.load) {
        auto loaded = group.load();
        for (const auto& field : group.fields) {
            if (auto it = loaded.find(field.id); it != loaded.end()) {
                cJSON_AddItemToObject(values, field.id.c_str(), EncodeValue(it->second));
            }
        }
    }
    cJSON* language = nullptr;
    for (const auto& translation : group.translations) {
        if (locale != translation.locale) continue;
        if (!language) {
            auto* translations = cJSON_AddObjectToObject(entry, "translations");
            if (!translations) return false;
            language = cJSON_AddObjectToObject(translations, locale.c_str());
            if (!language) return false;
        }
        cJSON_AddStringToObject(language, translation.key, translation.text);
    }
    return true;
}
} // namespace

void WifiConfigurationAp::SetAdvancedGroups(const std::vector<wifi_config::Group>& groups) {
    advanced_groups_ = groups;
}

void WifiConfigurationAp::BuildAdvancedGroups() {
    std::erase_if(advanced_groups_, [](const auto& group) { return group.id == "wifi"; });
    using namespace wifi_config;
    Field power{.id = "max_tx_power", .type = FieldType::Integer, .widget = Widget::Select,
                .label = "Max TX power"};
    for (int32_t setting : {8, 20, 28, 34, 44, 52, 56, 60, 66, 72, 80}) {
        auto id = std::to_string(setting);
        power.options.push_back({id, setting, std::to_string(setting / 4) + " dBm"});
    }
    const auto current = static_cast<int32_t>(max_tx_power_);
    if (!HasOption(power, current) && current >= 8) {
        power.options.push_back({std::to_string(current), current, std::to_string(current / 4) + " dBm"});
    }
    advanced_groups_.insert(advanced_groups_.begin(), {
        .id = "wifi", .title = "Wi-Fi",
        .fields = {std::move(power), {.id = "remember_bssid", .type = FieldType::Boolean, .label = "Remember BSSID"}},
        .translations = kWifiTranslations,
        .load = [this] {
            return Values{{"max_tx_power", static_cast<int32_t>(max_tx_power_)}, {"remember_bssid", remember_bssid_}};
        },
        .save = [this](const Values& values) -> SaveResult {
            const auto power = values.find("max_tx_power");
            const auto bssid = values.find("remember_bssid");
            const auto requested = power == values.end() ? max_tx_power_ : std::get<int32_t>(power->second);
            if (requested != max_tx_power_ && esp_wifi_set_max_tx_power(requested) != ESP_OK) {
                return {"max_tx_power", "The radio rejected this transmit power."};
            }
            nvs_handle_t nvs;
            auto err = nvs_open("wifi", NVS_READWRITE, &nvs);
            if (err == ESP_OK) {
                if (power != values.end()) err = nvs_set_i8(nvs, "max_tx_power", requested);
                if (err == ESP_OK && bssid != values.end()) {
                    err = nvs_set_u8(nvs, "remember_bssid", std::get<bool>(bssid->second));
                }
                if (err == ESP_OK) err = nvs_commit(nvs);
                nvs_close(nvs);
            }
            if (err != ESP_OK) {
                if (requested != max_tx_power_) esp_wifi_set_max_tx_power(max_tx_power_);
                return {"", "Could not save Wi-Fi settings.", "save_failed"};
            }
            max_tx_power_ = requested;
            if (bssid != values.end()) remember_bssid_ = std::get<bool>(bssid->second);
            return {};
        }
    });
}

esp_err_t WifiConfigurationAp::GetAdvancedConfig(httpd_req_t* req) {
    char query[48] = {};
    char locale[20] = {};
    if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK) {
        httpd_query_key_value(query, "lang", locale, sizeof(locale));
    }
    Json document(cJSON_CreateArray(), cJSON_Delete);
    if (!document || std::any_of(advanced_groups_.begin(), advanced_groups_.end(),
                                [&](const auto& group) { return !AddGroup(document.get(), group, locale); })) {
        return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Cannot load settings");
    }
    return SendJson(req, document.get());
}

esp_err_t WifiConfigurationAp::SaveAdvancedConfig(httpd_req_t* req) {
    using namespace wifi_config;
    if (!req->content_len || req->content_len > kMaxSubmitBytes) {
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid settings size");
    }
    // A JSON request requires an explicit preflight from cross-origin browser clients.
    char content_type[48] = {};
    if (httpd_req_get_hdr_value_str(req, "Content-Type", content_type, sizeof(content_type)) != ESP_OK ||
        (std::string_view(content_type) != "application/json" &&
         std::string_view(content_type).compare(0, 17, "application/json;") != 0)) {
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Expected application/json");
    }
    std::string body(req->content_len, '\0');
    size_t received = 0;
    while (received < body.size()) {
        int count = httpd_req_recv(req, body.data() + received, body.size() - received);
        if (count == HTTPD_SOCK_ERR_TIMEOUT) return httpd_resp_send_408(req);
        if (count <= 0) return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Incomplete settings");
        received += count;
    }
    if (!IsSettingsBody(body)) {
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid settings text");
    }
    const char* end = nullptr;
    Json document(cJSON_ParseWithLengthOpts(body.c_str(), body.size() + 1, &end, true), cJSON_Delete);
    if (!cJSON_IsObject(document.get()) || end != body.data() + body.size()) {
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid settings");
    }
    auto* id = cJSON_GetObjectItemCaseSensitive(document.get(), "id");
    auto* proposed = cJSON_GetObjectItemCaseSensitive(document.get(), "values");
    if (!cJSON_IsString(id) || !cJSON_IsObject(proposed)) {
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid settings group");
    }
    auto group = std::find_if(advanced_groups_.begin(), advanced_groups_.end(),
                              [&](const Group& entry) { return entry.id == id->valuestring; });
    if (group == advanced_groups_.end() || !group->save) {
        return httpd_resp_send_err(req, HTTPD_404_NOT_FOUND, "Unknown settings group");
    }
    Values values;
    const cJSON* node = nullptr;
    cJSON_ArrayForEach(node, proposed) {
        auto field = std::find_if(group->fields.begin(), group->fields.end(),
                                  [&](const Field& entry) { return entry.id == node->string; });
        Value value;
        if (field == group->fields.end() || field->widget == Widget::Copy ||
            !DecodeValue(node, *field, value) || !values.emplace(node->string, std::move(value)).second) {
            return SendResult(req, {node->string, "Invalid field value.", "invalid_field"});
        }
    }
    return SendResult(req, values.empty() ? SaveResult{} : group->save(values));
}
