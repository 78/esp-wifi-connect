const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'assets/wifi_configuration.html'), 'utf8');
const script = html.match(/<script type="text\/javascript">([\s\S]*?)<\/script>/)[1];
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, 'url_cases.json')));
const prefix = 'https://example.com/';
cases.push({url: prefix + 'a'.repeat(255 - prefix.length), valid: true});
cases.push({url: prefix + 'a'.repeat(256 - prefix.length), valid: false});
const elements = new Map();
function element(id) {
    if (!elements.has(id)) elements.set(id, {
        value: '', checked: false, disabled: false, textContent: '', style: {},
        attributes: new Map(),
        classList: {add() {}, remove() {}}, addEventListener() {},
        setAttribute(key, value) {this.attributes.set(key, value);},
        getAttribute(key) {return this.attributes.get(key) || null;},
        removeAttribute(key) {this.attributes.delete(key);}, blur() {}, focus() {}
    });
    return elements.get(id);
}
let requests = [];
let config = {};
let responseFailure = null;
let networkFailure = false;
const context = vm.createContext({
    console, URL, URLSearchParams, setTimeout() {},
    localStorage: {setItem() {}},
    window: {location: {href: 'http://192.168.4.1/'}, addEventListener() {}},
    document: {
        documentElement: {}, getElementById: element, addEventListener() {},
        querySelectorAll(selector) {
            return selector === '[data-lang-message]' ? [...elements.values()].filter(el => el.getAttribute('data-lang-message')) : [];
        }
    },
    fetch: async (url, options) => {
        requests.push({url, body: options && options.body});
        if (networkFailure) throw new TypeError('Failed to fetch');
        return {json: async () => url === '/advanced/config' ? config : responseFailure || {success: true}};
    }
});
vm.runInContext(script, context);

(async () => {
    const catalogs = vm.runInContext('translations', context);
    const referenceKeys = Object.keys(catalogs['en-US']).sort();
    for (const [locale, catalog] of Object.entries(catalogs)) {
        assert.deepEqual(Object.keys(catalog).sort(), referenceKeys, locale);
        for (const key of referenceKeys) assert.ok(typeof catalog[key] === 'string' && catalog[key].trim(), `${locale}: ${key}`);
    }
    element('language').value = 'ru-RU';
    element('max_tx_power').value = '80';
    for (const test of cases) {
        context.testUrl = test.url;
        assert.equal(vm.runInContext('isValidOtaUrl(testUrl)', context), test.valid, test.url);
        requests = [];
        element('ota_url').value = test.url;
        await vm.runInContext('submitAdvancedForm({preventDefault() {}})', context);
        const submits = requests.filter(x => x.url === '/advanced/submit');
        assert.equal(submits.length, test.valid ? 1 : 0, test.url);
        assert.equal(element('advanced_button').disabled, false);
        if (test.valid) assert.equal(JSON.parse(submits[0].body).ota_url, test.url);
        else assert.ok(element('advanced_error').textContent.length > 0);
    }

    for (const data of [{}, {ota_url: ''}, {ota_url: 'Huawei-1ct5dn'}, {ota_url: null}]) {
        config = data;
        element('ota_url').value = 'Huawei-1ct5dn';
        await vm.runInContext('loadAdvancedConfig()', context);
        assert.equal(element('ota_url').value, '');
    }
    config = {ota_url: 'https://custom.example/ota/'};
    await vm.runInContext('loadAdvancedConfig()', context);
    assert.equal(element('ota_url').value, config.ota_url);
    vm.runInContext('clearOtaUrl()', context);
    assert.equal(element('ota_url').value, '');

    async function loadSleep(overrides = {}) {
        config = {show_sleep_config: true, sleep_mode: true,
            sleep_dim_minutes: null, sleep_off_minutes: null, ...overrides};
        await vm.runInContext('loadAdvancedConfig()', context);
    }
    async function saveAdvanced() {
        requests = [];
        await vm.runInContext('submitAdvancedForm({preventDefault() {}})', context);
        return requests.filter(x => x.url === '/advanced/submit').map(x => JSON.parse(x.body));
    }
    function assertNoTimers(payload) {
        assert.equal(Object.hasOwn(payload, 'sleep_dim_minutes'), false);
        assert.equal(Object.hasOwn(payload, 'sleep_off_minutes'), false);
    }

    // Hidden/disabled controls cannot block unrelated saves or install overrides.
    await loadSleep({show_sleep_config: false});
    assert.equal(element('sleep_config_row').style.display, 'none');
    assert.equal(element('sleep_timers_row').style.display, 'none');
    for (const key of ['sleep_dim_minutes', 'sleep_off_minutes']) {
        assert.equal(element(key).disabled, true);
        element(key).value = 'invalid';
    }
    assertNoTimers((await saveAdvanced())[0]);

    // Missing overrides stay blank; saving a different setting preserves board defaults.
    await loadSleep();
    assert.equal(element('sleep_timers_row').style.display, 'block');
    assert.equal(element('sleep_dim_minutes').value, '');
    assert.equal(element('sleep_off_minutes').value, '');
    assert.equal(element('sleep_dim_minutes').disabled, false);
    element('max_tx_power').value = '20';
    assertNoTimers((await saveAdvanced())[0]);

    element('sleep_dim_minutes').value = '3';
    let payload = (await saveAdvanced())[0];
    assert.equal(payload.sleep_dim_minutes, 3);
    assert.equal(Object.hasOwn(payload, 'sleep_off_minutes'), false);
    assertNoTimers((await saveAdvanced())[0]); // Successful saves update the baseline.
    element('sleep_dim_minutes').value = '';
    payload = (await saveAdvanced())[0];
    assert.equal(payload.sleep_dim_minutes, null); // Erase just this override.
    assertNoTimers((await saveAdvanced())[0]);

    await loadSleep({sleep_dim_minutes: 3, sleep_off_minutes: 10});
    element('sleep_off_minutes').value = '20';
    payload = (await saveAdvanced())[0];
    assert.equal(payload.sleep_off_minutes, 20);
    assert.equal(Object.hasOwn(payload, 'sleep_dim_minutes'), false);

    for (const value of ['-1', '-0.5', '1.9', '1441', 'Infinity', 'invalid']) {
        await loadSleep();
        element('sleep_dim_minutes').value = value;
        assert.deepEqual(await saveAdvanced(), []);
        assert.ok(element('sleep_timers_error').textContent.length > 0);
        assert.equal(element('advanced_error').textContent, '');
        assert.equal(element('advanced_button').disabled, false);
    }
    await loadSleep();
    element('sleep_dim_minutes').value = '0';
    element('sleep_off_minutes').value = '0';
    payload = (await saveAdvanced())[0];
    assert.equal(payload.sleep_dim_minutes, 0);
    assert.equal(payload.sleep_off_minutes, 0);

    await loadSleep();
    element('sleep_dim_minutes').value = '10';
    element('sleep_off_minutes').value = '5';
    assert.deepEqual(await saveAdvanced(), []);
    assert.ok(element('sleep_timers_error').textContent.length > 0);
    vm.runInContext('clearSleepTimerError()', context);
    assert.equal(element('sleep_timers_error').textContent, '');
    element('sleep_mode').checked = false;
    vm.runInContext('toggleSleepTimers()', context);
    assert.equal(element('sleep_dim_minutes').disabled, true);
    payload = (await saveAdvanced())[0];
    assert.equal(payload.sleep_mode, false);
    assertNoTimers(payload); // Invalid unsaved timers do not prevent disabling sleep.

    // Connecting Wi-Fi must never submit or save an unrelated OTA field.
    requests = [];
    element('ssid').value = 'Huawei-1ct5dn';
    element('password').value = 'test-password';
    element('ota_url').value = 'Huawei-1ct5dn';
    await vm.runInContext('submitForm({preventDefault() {}})', context);
    assert.deepEqual(requests.map(x => x.url), ['/submit']);
    assert.deepEqual(JSON.parse(requests[0].body), {
        ssid: 'Huawei-1ct5dn', password: 'test-password'
    });
    assert.match(html, /type="url" id="ota_url"[^>]*maxlength="255"/);

    // Every locale renders feedback without an English API/browser error leaking through.
    await loadSleep();
    element('ota_url').value = '';
    for (const [locale, catalog] of Object.entries(catalogs)) {
        element('language').value = locale;
        vm.runInContext('changeLanguage()', context);
        assert.equal(context.document.documentElement.lang, locale);
        assert.equal(context.document.documentElement.dir, ['ar-SA', 'fa-IR', 'he-IL'].includes(locale) ? 'rtl' : 'ltr');
        await saveAdvanced();
        assert.equal(element('advanced_status').textContent, catalog.settings_saved, locale);
        element('sleep_dim_minutes').value = '1441';
        await saveAdvanced();
        assert.equal(element('sleep_timers_error').textContent, catalog.invalid_sleep_minutes, locale);
        assert.equal(element('advanced_status').textContent, '');
        element('sleep_dim_minutes').value = '';
        responseFailure = {success: false, error: 'Failed to save sleep timer values'};
        await saveAdvanced();
        assert.equal(element('advanced_error').textContent, catalog.save_failed, locale);
        responseFailure = {success: false, error: 'Invalid sleep timer values'};
        await saveAdvanced();
        assert.equal(element('advanced_error').textContent, catalog.invalid_sleep_timers, locale);
        responseFailure = {success: false, error: 'OTA URL must be empty or a valid HTTP(S) URL (max 255 bytes)'};
        await saveAdvanced();
        assert.equal(element('advanced_error').textContent, catalog.invalid_ota_url, locale);
        responseFailure = {success: false, error: 'Invalid SSID'};
        await vm.runInContext('submitForm({preventDefault() {}})', context);
        assert.equal(element('error').textContent, catalog.invalid_ssid, locale);
        responseFailure = null;
        networkFailure = true;
        await saveAdvanced();
        assert.equal(element('advanced_error').textContent, catalog.save_failed, locale);
        await vm.runInContext('submitForm({preventDefault() {}})', context);
        assert.equal(element('error').textContent, catalog.connection_failed, locale);
        networkFailure = false;
    }
    element('language').value = 'en-US';
    await saveAdvanced();
    element('language').value = 'zh-CN';
    vm.runInContext('changeLanguage()', context);
    assert.equal(element('advanced_status').textContent, catalogs['zh-CN'].settings_saved);
    vm.runInContext('clearAdvancedStatus()', context);
    element('language').value = 'ru-RU';
    vm.runInContext('changeLanguage()', context);
    assert.equal(element('advanced_status').textContent, '');
    console.log(`Portal: ${cases.length} URL cases, timer behavior, Wi-Fi form isolation, and ${Object.keys(catalogs).length} complete locale catalogs with live feedback passed.`);
})().catch(error => {console.error(error); process.exitCode = 1;});
