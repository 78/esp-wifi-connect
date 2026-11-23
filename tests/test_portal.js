const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'assets/wifi_configuration.html'), 'utf8');
const script = html.match(/<script type="text\/javascript">([\s\S]*?)<\/script>/)[1];
const renderer = fs.readFileSync(path.join(root, 'assets/wifi_config_group.js'), 'utf8');

class Element {
    constructor(tag) {
        this.tag = tag;
        this.children = [];
        this.attributes = new Map();
        this.events = {};
        this.value = '';
        this.textContent = '';
        this.checked = false;
        this.classList = {add() {}, remove() {}};
    }
    append(child) { child.parent = this; this.children.push(child); }
    replaceChildren() { this.children = []; }
    get firstChild() { return this.children[0]; }
    get valueAsNumber() { return Number(this.value); }
    addEventListener(name, callback) { this.events[name] = callback; }
    dispatchEvent(event) {
        this.events[event.type]?.(event);
        if (event.bubbles) this.parent?.dispatchEvent(event);
    }
    setAttribute(name, value) { this.attributes.set(name, value); }
    getAttribute(name) { return this.attributes.get(name); }
    removeAttribute(name) { this.attributes.delete(name); }
    querySelector() { return null; }
    blur() {}
}

const elements = new Map();
function element(id) {
    if (!elements.has(id)) elements.set(id, new Element('div'));
    return elements.get(id);
}
const payloads = [];
let responseError;
let failGroup;
let failNetwork = false;
const english = {
    id: 'demo', title: 'Demo',
    fields: [
        {id: 'on', type: 'boolean', label: 'Enabled'},
        {id: 'number', type: 'integer', label: 'Minutes', help: 'Enter 0 to disable.', enabled_by: 'on', min: 0, max: 1440},
        {id: 'choices', type: 'string[]', label: 'Choices', options: [{id: 'a', value: 'a', label: 'A'}]},
        {id: 'public', type: 'string', widget: 'copy', label: 'Public key'}
    ],
    values: {on: true, number: null, choices: ['a'], public: 'ssh-key'}
};
const chinese = {
    ...english,
    translations: {'zh-CN': {'title': '示例', 'number.label': '分钟', 'number.help': '填 0 可关闭。', 'number.error': '分钟数无效。'}}
};
const secondGroup = {
    id: 'ssh', title: 'SSH',
    fields: [
        {id: 'port', type: 'integer', label: 'SSH port', min: 1, max: 65535},
        {id: 'fingerprint', type: 'string', label: 'Trusted fingerprint', clearable: true}
    ],
    values: {port: 22, fingerprint: 'SHA256:known-fingerprint'}
};
const context = vm.createContext({
    console, URL, URLSearchParams, Event, setTimeout() {},
    localStorage: {setItem() {}},
    window: {location: {href: 'http://192.168.4.1/'}, addEventListener() {}},
    document: {
        documentElement: {},
        getElementById: element,
        createElement: tag => new Element(tag),
        addEventListener() {},
        querySelectorAll(selector) {
            const key = selector.slice(1, -1);
            return [...elements.values()].filter(el => el.getAttribute(key));
        }
    },
    fetch: async (url, options) => {
        if (failNetwork) throw new TypeError('Failed to fetch');
        if (url.startsWith('/advanced/config')) return {
            ok: true, json: async () => structuredClone([url.endsWith('zh-CN') ? chinese : english, secondGroup])
        };
        const body = JSON.parse(options.body);
        payloads.push({url, body});
        const error = !failGroup || failGroup === body.id ? responseError : undefined;
        return {ok: !error, json: async () => error || {success: true}};
    }
});
vm.runInContext(renderer, context);
vm.runInContext(script, context);
const preventDefault = () => {};

(async () => {
    const catalogs = vm.runInContext('translations', context);
    const referenceKeys = Object.keys(catalogs['en-US']).sort();
    for (const [locale, catalog] of Object.entries(catalogs)) {
        assert.deepEqual(Object.keys(catalog).sort(), referenceKeys, locale);
        for (const key of referenceKeys) assert.ok(catalog[key]?.trim(), `${locale}: ${key}`);
    }
    element('language').value = 'en-US';
    await vm.runInContext('portalAdvanced.load()', context);
    const [panel, otherPanel] = element('advanced-groups').children;
    const [summary, body] = panel.children;
    const [on, number, choices, publicKey] = body.children;
    const [port, fingerprint] = otherPanel.children[1].children;
    const form = element('advanced-form');
    const button = element('advanced-save');
    const save = () => form.events.submit({preventDefault});
    const change = () => body.events.input();
    assert.equal(panel.tag, 'details');
    assert.equal(otherPanel.tag, 'details');
    assert.ok(!panel.open && !otherPanel.open);
    assert.equal(summary.tag, 'summary');
    assert.equal(button.disabled, true);
    assert.equal(number.children[1].value, '');
    assert.equal(publicKey.children[1].readOnly, true);
    assert.equal(publicKey.children[1].value, 'ssh-key');

    number.children[1].value = '0';
    choices.children[1].children[0].checked = false;
    await save();
    assert.deepEqual(payloads.at(-1).body, {id: 'demo', values: {number: 0, choices: []}});
    number.children[1].value = '';
    await save();
    assert.deepEqual(payloads.at(-1).body, {id: 'demo', values: {number: null}});
    on.children[1].checked = false;
    number.children[1].value = '10';
    change();
    assert.equal(number.hidden, true);
    await save();
    assert.deepEqual(payloads.at(-1).body, {id: 'demo', values: {on: false}});

    on.children[1].checked = true;
    change();
    element('language').value = 'zh-CN';
    await vm.runInContext('portalAdvanced.refreshLanguage()', context);
    assert.equal(summary.children[0].textContent, '示例');
    assert.equal(number.children[0].textContent, '分钟');
    assert.equal(number.children[1].value, '10');
    assert.equal(choices.children[0].textContent, 'Choices');

    port.children[1].value = '2222';
    otherPanel.children[1].events.input();
    assert.equal(button.disabled, false);
    failGroup = 'demo';
    responseError = {success: false, field: 'number', key: 'number.error', error: 'Invalid minutes'};
    const before = payloads.length;
    await save();
    assert.deepEqual(payloads.slice(before).map(item => item.body), [
        {id: 'demo', values: {on: true, number: 10}},
        {id: 'ssh', values: {port: 2222}}
    ]);
    assert.equal(panel.open, true);
    assert.ok(!otherPanel.open);
    assert.equal(number.children.at(-1).textContent, '分钟数无效。');
    assert.equal(number.children[1].getAttribute('aria-invalid'), 'true');
    change();
    assert.equal(number.children.at(-1).textContent, '');
    responseError = undefined;
    const beforeRetry = payloads.length;
    await save();
    assert.deepEqual(payloads.slice(beforeRetry).map(item => item.body), [
        {id: 'demo', values: {on: true, number: 10}}
    ]);
    assert.equal(button.disabled, true);
    assert.equal(element('advanced-feedback').textContent, catalogs['zh-CN'].settings_saved);
    failGroup = undefined;
    const clear = fingerprint.children[2];
    const beforeClear = payloads.length;
    assert.equal(clear.disabled, false);
    clear.events.click();
    assert.equal(fingerprint.children[1].value, '');
    assert.equal(clear.disabled, true);
    assert.equal(button.disabled, false);
    assert.equal(payloads.length, beforeClear);
    await save();
    assert.deepEqual(payloads.at(-1).body, {id: 'ssh', values: {fingerprint: ''}});
    responseError = {success: false, error: 'Invalid SSID'};
    await vm.runInContext('submitForm({preventDefault() {}})', context);
    assert.equal(element('error').textContent, catalogs['zh-CN'].invalid_ssid);
    failNetwork = true;
    await vm.runInContext('submitForm({preventDefault() {}})', context);
    assert.equal(element('error').textContent, catalogs['zh-CN'].connection_failed);

    // A scan started in one language renders in the language selected before it returns.
    let finishScan;
    context.fetch = () => new Promise(resolve => {finishScan = resolve;});
    element('language').value = 'en-US';
    vm.runInContext('loadAPList()', context);
    element('language').value = 'zh-CN';
    finishScan({json: async () => ({support_5g: false, aps: []})});
    await new Promise(setImmediate);
    assert.ok(element('ap_list').innerHTML.includes(catalogs['zh-CN'].select_wifi));
    console.log(`Portal rendering, typed saves, translation fallback and live switching across ${Object.keys(catalogs).length} built-in locales passed.`);
})().catch(error => {console.error(error); process.exitCode = 1;});
