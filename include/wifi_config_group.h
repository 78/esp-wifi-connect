#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
#include <span>
#include <string>
#include <variant>
#include <vector>

namespace wifi_config {

enum class FieldType { Text, Integer, Boolean, TextList };
enum class Widget { Default, Text, TextArea, Number, Switch, Select, Radio, Checkboxes, Copy };
using Value = std::variant<std::nullptr_t, std::string, int32_t, bool, std::vector<std::string>>;
using Values = std::map<std::string, Value>;
struct Translation {
    const char* locale;
    const char* key;
    const char* text;
};
using Translations = std::span<const Translation>;

struct Option {
    std::string id;
    Value value;
    std::string label;
};

struct Field {
    std::string id;
    FieldType type = FieldType::Text;
    Widget widget = Widget::Default;
    std::string label = {};
    std::string help = {};
    std::string unit = {};
    bool required = false;
    int32_t min = INT32_MIN;
    int32_t max = INT32_MAX;
    size_t max_length = 0;
    std::vector<Option> options = {};
    std::string enabled_by = {};
    bool clearable = false;
};

struct SaveResult {
    std::string field = {};
    std::string error = {};
    // Optional translation key, looked up in the group's locale table.
    std::string key = {};
};

struct Group {
    std::string id;
    std::string title;
    std::string help = {};
    std::vector<Field> fields = {};
    Translations translations = {};
    std::function<Values()> load = {};
    // Receives submitted, validated fields. An absent field keeps its prior value.
    std::function<SaveResult(const Values&)> save = {};
};

} // namespace wifi_config
