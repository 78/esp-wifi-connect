#include "ota_url.h"

#include <strings.h>
#include <cctype>

#include "http_parser.h"

namespace wifi_config {

bool IsValidOtaUrl(std::string_view url) {
    if (url.empty()) {
        return true;
    }
    if (url.size() > kMaxOtaUrlLength ||
        !((url.size() >= 7 && strncasecmp(url.data(), "http://", 7) == 0) ||
          (url.size() >= 8 && strncasecmp(url.data(), "https://", 8) == 0))) {
        return false;
    }

    for (std::size_t i = 0; i < url.size(); ++i) {
        const auto c = static_cast<unsigned char>(url[i]);
        if (c <= ' ' || c >= 0x7f || c == '\\') {
            return false;
        }
        if (c == '%' &&
            (i + 2 >= url.size() || !std::isxdigit(static_cast<unsigned char>(url[i + 1])) ||
             !std::isxdigit(static_cast<unsigned char>(url[i + 2])))) {
            return false;
        }
    }

    http_parser_url parsed{};
    return http_parser_parse_url(url.data(), url.size(), 0, &parsed) == 0 &&
           (parsed.field_set & (1 << UF_SCHEMA)) && (parsed.field_set & (1 << UF_HOST)) &&
           parsed.field_data[UF_HOST].len > 0 &&
           (!(parsed.field_set & (1 << UF_PORT)) || parsed.port > 0);
}

}  // namespace wifi_config
