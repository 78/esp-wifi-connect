"""Run the real URL parser, portal script, and save handler on the host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / 'tests/url_cases.json').read_text())
PREFIX = 'https://example.com/'
CASES += [dict(url=PREFIX + 'a' * (n - len(PREFIX)), valid=n == 255) for n in (255, 256)]


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        idf = Path(os.environ.get('IDF_PATH', '/nonexistent'))
        cls.parser = idf / 'components/http_parser'
        if not shutil.which('c++') or not (cls.parser / 'http_parser.c').exists():
            raise unittest.SkipTest('requires a host C/C++ compiler and exported ESP-IDF')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.build = Path(cls.tmp.name)
        subprocess.run(['cc', '-c', str(cls.parser / 'http_parser.c'), '-o',
                        str(cls.build / 'parser.o')], check=True)
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-c',
                        str(ROOT / 'ota_url.cc'), '-I', str(ROOT / 'include'), '-I',
                        str(cls.parser), '-o', str(cls.build / 'url.o')], check=True)

    @classmethod
    def compile(cls, name, source, extra=()):
        src = cls.build / (name + '.cc')
        src.write_text(source)
        binary = cls.build / name
        subprocess.run(['c++', '-std=c++17', str(src), str(cls.build / 'parser.o'),
                        str(cls.build / 'url.o'), '-I', str(ROOT / 'include'),
                        *extra, '-o', str(binary)], check=True)
        return binary


class UrlTests(NativeTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.binary = cls.compile('validate', '''
#include <iostream>
#include "ota_url.h"
int main(int argc, char** argv) {
    if (argc != 2) return 1;
    std::cout << wifi_config::IsValidOtaUrl(argv[1]);
}
''')

    def test_url_cases(self):
        for case in CASES:
            with self.subTest(url=case['url']):
                out = subprocess.check_output([str(self.binary), case['url']], text=True)
                self.assertEqual(out, '1' if case['valid'] else '0')


class SaveHandlerTests(NativeTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cjson = Path(os.environ.get('CJSON_DIR', '/nonexistent'))
        if not (cjson / 'cJSON.c').exists():
            raise unittest.SkipTest('set CJSON_DIR to the cJSON source directory')
        subprocess.run(['cc', '-c', str(cjson / 'cJSON.c'), '-o',
                        str(cls.build / 'cjson.o')], check=True)
        source = (ROOT / 'wifi_configuration_ap.cc').read_text()
        start = source.index('.handler = ', source.index('httpd_uri_t advanced_submit'))
        start += len('.handler = ')
        handler = source[start:source.index(',\n        .user_ctx', start)]
        load_start = source.index('// 加载高级配置')
        load_end = source.index('\n}\n', load_start)
        load = source[load_start:load_end]
        driver = r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include "ota_url.h"
#include "cJSON.h"
using esp_err_t = int;
using nvs_handle_t = int;
constexpr int ESP_OK = 0, ESP_FAIL = -1, NVS_READONLY = 0, NVS_READWRITE = 1;
constexpr int HTTPD_400_BAD_REQUEST = 400, HTTPD_500_INTERNAL_SERVER_ERROR = 500;
constexpr int HTTPD_SOCK_ERR_TIMEOUT = -11, HTTPD_RESP_USE_STRLEN = -1;
constexpr int ESP_ERR_NVS_INVALID_LENGTH = -2;
#define ESP_LOGE(...) ((void)0)
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
#define ESP_ERROR_CHECK(value) assert((value) == ESP_OK)
std::string stored = "https://old.example/ota/", pending;
int opens = 0, commits = 0;
bool fail_save = false, fail_commit = false;
struct httpd_req_t {
    size_t content_len; void* user_ctx; std::string body;
    int status = 200; std::string response;
};
int httpd_req_recv(httpd_req_t* req, char* buf, size_t len) {
    memcpy(buf, req->body.data(), len); return static_cast<int>(len);
}
int httpd_resp_send_err(httpd_req_t* req, int code, const char* msg) {
    req->status = code; req->response = msg; return ESP_OK;
}
int httpd_resp_send_408(httpd_req_t* req) {req->status = 408; return ESP_OK;}
int httpd_resp_send(httpd_req_t* req, const char* msg, int) {
    req->response = msg; return ESP_OK;
}
int httpd_resp_set_type(httpd_req_t*, const char*) {return ESP_OK;}
int httpd_resp_set_status(httpd_req_t* req, const char*) {req->status = 400; return ESP_OK;}
int httpd_resp_set_hdr(httpd_req_t*, const char*, const char*) {return ESP_OK;}
int nvs_open(const char*, int, int* handle) {
    ++opens; *handle = 1; pending = stored; return ESP_OK;
}
int nvs_set_str(int, const char*, const char* value) {
    if (fail_save) return ESP_FAIL;
    pending = value; return ESP_OK;
}
int nvs_get_str(int, const char*, char* value, size_t* size) {
    if (stored.size() + 1 > *size) return ESP_ERR_NVS_INVALID_LENGTH;
    memcpy(value, stored.c_str(), stored.size() + 1); return ESP_OK;
}
int nvs_get_i8(int, const char*, int8_t*) {return ESP_FAIL;}
int nvs_get_u8(int, const char*, uint8_t*) {return ESP_FAIL;}
int nvs_set_i8(int, const char*, int8_t) {return ESP_OK;}
int nvs_set_u8(int, const char*, uint8_t) {return ESP_OK;}
int nvs_commit(int) {
    ++commits;
    if (fail_commit) return ESP_FAIL;
    stored = pending; return ESP_OK;
}
void nvs_close(int) {}
int esp_wifi_set_max_tx_power(int8_t) {return ESP_OK;}
int esp_wifi_get_max_tx_power(int8_t* value) {*value = 80; return ESP_OK;}
struct WifiConfigurationAp {
    std::string ota_url_ = "https://old.example/ota/";
    int8_t max_tx_power_ = 80;
    bool remember_bssid_ = false, sleep_mode_ = true;
    void Load() { LOAD_CODE }
};
int main(int argc, char** argv) {
    assert(argc >= 2);
    auto handler = HANDLER_CODE;
    WifiConfigurationAp ap;
    if (std::string(argv[1]) == "--load") {
        stored = argv[2]; ap.Load(); std::cout << ap.ota_url_; return 0;
    }
    if (argc > 2) fail_save = std::string(argv[2]) == "save";
    if (argc > 2) fail_commit = std::string(argv[2]) == "commit";
    std::string body = argv[1];
    httpd_req_t req{body.size(), &ap, body};
    handler(&req);
    std::cout << req.status << '\n' << opens << '\n' << commits << '\n'
              << stored << '\n' << ap.ota_url_ << '\n' << req.response << '\n';
}
'''.replace('LOAD_CODE', load).replace('HANDLER_CODE', handler)
        cls.binary = cls.compile('save', driver, ['-I', str(cjson), str(cls.build / 'cjson.o')])

    def save(self, payload, fail=''):
        return subprocess.check_output([str(self.binary), json.dumps(payload), fail],
                                       text=True).splitlines()

    def test_invalid_values_do_not_open_nvs_or_modify_settings(self):
        invalid = [case['url'] for case in CASES if not case['valid']]
        for value in invalid + [None, 123, False, [], {}]:
            with self.subTest(url=value):
                result = self.save(dict(ota_url=value, max_tx_power=8, sleep_mode=False))
                self.assertEqual(result[:3], ['400', '0', '0'])
                self.assertEqual(result[3:5], ['https://old.example/ota/'] * 2)
                self.assertFalse(json.loads(result[5])['success'])

    def test_valid_and_empty_urls_are_saved(self):
        for case in CASES:
            if case['valid']:
                with self.subTest(url=case['url']):
                    result = self.save(dict(ota_url=case['url'], max_tx_power=80))
                    self.assertEqual(result[:3], ['200', '1', '1'])
                    self.assertEqual(result[3:5], [case['url']] * 2)

    def test_omitted_url_preserves_custom_configuration(self):
        result = self.save(dict(sleep_mode=False))
        self.assertEqual(result[0], '200')
        self.assertEqual(result[3:5], ['https://old.example/ota/'] * 2)

    def test_nvs_failures_do_not_report_success_or_replace_in_memory_url(self):
        for failure in ('save', 'commit'):
            result = self.save(dict(ota_url='https://new.example/ota/'), failure)
            self.assertEqual(result[0], '500')
            self.assertEqual(result[4], 'https://old.example/ota/')

    def test_loaded_invalid_or_oversized_urls_are_ignored(self):
        for case in CASES:
            with self.subTest(url=case['url']):
                result = subprocess.check_output([str(self.binary), '--load', case['url']],
                                                 text=True)
                self.assertEqual(result, case['url'] if case['valid'] else '')


class PortalTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'requires Node.js')
    def test_portal(self):
        subprocess.run(['node', str(ROOT / 'tests/test_portal.js')], check=True)


if __name__ == '__main__':
    unittest.main()
