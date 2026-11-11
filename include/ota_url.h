#pragma once

#include <cstddef>
#include <string_view>

namespace wifi_config {

// Matches the config portal's 256-byte NVS read buffer, including the terminator.
inline constexpr std::size_t kMaxOtaUrlLength = 255;

// Accept an absolute HTTP(S) URL, or an empty value to use the application's default.
// URLs must be ASCII; non-ASCII characters must be percent-encoded.
bool IsValidOtaUrl(std::string_view url);

}  // namespace wifi_config
