'use strict';

const portalAdvanced = (() => {
    const widgets = { string: 'text', integer: 'number', boolean: 'switch', 'string[]': 'checkboxes' };
    const owned = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
    let textUpdates = [];
    let loaded = false;
    let loadGeneration = 0;
    let submitBound = false;
    let handleSubmit = null;
    let groups = [];
    const fetchedLanguages = new Set();
    const selectedLanguage = () => document.getElementById('language').value;

    function element(tag, parent, className) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        parent.append(node);
        return node;
    }

    function localText(group, key, fallback) {
        const locale = selectedLanguage();
        const dictionary = group.translations?.[locale];
        return dictionary && owned(dictionary, key) ? dictionary[key] : fallback;
    }

    function caption(node, group, key, fallback) {
        const update = () => { node.textContent = localText(group, key, fallback); };
        update();
        textUpdates.push(update);
    }

    function fieldControl(parent, group, field, value, index) {
        const widget = field.widget || widgets[field.type];
        const id = `advanced-${group.id}-${index}`;
        const multiple = widget === 'checkboxes';
        const choices = multiple || widget === 'radio';
        const row = element(choices ? 'fieldset' : 'div', parent, 'advanced-field');
        if (widget === 'switch') row.classList.add('advanced-switch-row');
        const label = element(choices ? 'legend' : 'label', row);
        if (!choices) label.htmlFor = id;
        caption(label, group, field.id + '.label', field.label);

        let control;
        let read;
        let inputs;
        if (choices || widget === 'select') {
            const options = [];
            const area = choices ? row : element('select', row, 'advanced-control');
            control = area;
            if (!choices) area.id = id;
            for (const [i, option] of (field.options || []).entries()) {
                const optionKey = field.id + '.options.' + option.id + '.label';
                if (choices) {
                    const line = element('label', area, 'advanced-choice');
                    const input = element('input', line);
                    input.type = multiple ? 'checkbox' : 'radio';
                    input.name = id;
                    input.required = !multiple && !!field.required;
                    input.checked = multiple ? Array.isArray(value) && value.includes(option.value) : value === option.value;
                    options.push(input);
                    caption(element('span', line), group, optionKey, option.label);
                } else {
                    const item = element('option', area);
                    item.value = String(i);
                    caption(item, group, optionKey, option.label);
                }
            }
            if (!choices) {
                const selected = (field.options || []).findIndex(option => option.value === value);
                area.selectedIndex = selected;
                area.required = !!field.required;
            }
            inputs = choices ? options : [area];
            read = () => {
                if (multiple) return field.options.filter((_, i) => options[i].checked).map(option => option.value);
                const selected = choices ? options.findIndex(input => input.checked) : area.selectedIndex;
                return selected < 0 ? undefined : field.options[selected].value;
            };
        } else {
            const isTextarea = widget === 'textarea' || widget === 'copy';
            control = element(isTextarea ? 'textarea' : 'input', row,
                widget === 'switch' ? 'advanced-switch' : 'advanced-control');
            inputs = [control];
            control.id = id;
            if (widget === 'switch') {
                control.type = 'checkbox';
                control.setAttribute('role', 'switch');
                control.checked = value === true;
                read = () => control.checked;
            } else {
                control.spellcheck = false;
                control.autocapitalize = 'none';
                if (!isTextarea) control.type = widget === 'number' ? 'number' : 'text';
                control.value = value ?? '';
                control.required = !!field.required;
                if (widget === 'number') {
                    control.inputMode = 'numeric';
                    control.step = '1';
                    if (field.min !== undefined) control.min = field.min;
                    if (field.max !== undefined) control.max = field.max;
                    read = () => control.value === '' ? null : control.valueAsNumber;
                } else if (widget === 'copy') {
                    control.readOnly = true;
                    control.rows = 3;
                    const copy = element('button', row, 'advanced-copy');
                    copy.type = 'button';
                    caption(copy, group, field.id + '.copy', 'Copy');
                    copy.addEventListener('click', async () => {
                        control.focus();
                        control.select();
                        control.setSelectionRange(0, control.value.length);
                        try {
                            if (navigator.clipboard) await navigator.clipboard.writeText(control.value);
                            else document.execCommand('copy');
                        } catch (_) {
                            // Leave the selection active for the browser's Copy menu.
                        }
                    });
                    read = () => undefined;
                } else {
                    if (field.max_length) control.maxLength = field.max_length;
                    if (field.clearable) {
                        const clear = element('button', row, 'advanced-copy');
                        clear.type = 'button';
                        caption(clear, group, field.id + '.clear', 'Clear');
                        const updateClear = () => { clear.disabled = !control.value; };
                        updateClear();
                        control.addEventListener('input', updateClear);
                        clear.addEventListener('click', () => {
                            control.value = '';
                            control.dispatchEvent(new Event('input', {bubbles: true}));
                        });
                    }
                    read = () => control.value;
                }
            }
        }

        const descriptions = [];
        if (field.unit) {
            const unit = element('span', row, 'advanced-help');
            unit.id = id + '-unit';
            descriptions.push(unit.id);
            caption(unit, group, field.id + '.unit', field.unit);
        }
        if (field.help) {
            const help = element('small', row, 'advanced-help');
            help.id = id + '-help';
            descriptions.push(help.id);
            caption(help, group, field.id + '.help', field.help);
        }
        const error = element('small', row, 'advanced-field-error');
        error.id = id + '-error';
        error.setAttribute('aria-live', 'polite');
        descriptions.push(error.id);
        control.setAttribute('aria-describedby', descriptions.join(' '));
        return {
            read: () => row.hidden ? undefined : read(),
            enable(enabled) {
                row.hidden = !enabled;
                control.disabled = !enabled;
            },
            control, error, inputs
        };
    }

    function renderGroup(parent, group, onEdit) {
        const panel = element('details', parent, 'advanced-group');
        const summary = element('summary', panel, 'advanced-summary');
        caption(element('span', summary), group, 'title', group.title);
        const body = element('div', panel, 'advanced-group-body');
        if (group.help) caption(element('p', body, 'advanced-help'), group, 'help', group.help);
        const fields = new Map(group.fields.map((field, index) =>
            [field.id, fieldControl(body, group, field, group.values[field.id], index)]));
        const baseline = {...group.values};
        const status = element('div', body, 'advanced-feedback');
        status.setAttribute('aria-live', 'polite');
        let currentError;

        function applyDependencies() {
            for (const field of group.fields) {
                if (field.enabled_by) fields.get(field.id).enable(fields.get(field.enabled_by)?.read() === true);
            }
        }
        function clearError() {
            currentError = undefined;
            status.textContent = '';
            for (const field of fields.values()) {
                field.error.textContent = '';
                field.control.removeAttribute('aria-invalid');
            }
        }
        function showError() {
            if (!currentError) return;
            const field = fields.get(currentError.field);
            const message = localText(group, currentError.key || '',
                currentError.error || translate('save_failed'));
            (field?.error || status).textContent = message;
            if (field) field.control.setAttribute('aria-invalid', 'true');
        }
        function changes() {
            const values = Object.create(null);
            for (const [key, field] of fields) {
                const value = field.read();
                if (value !== undefined && JSON.stringify(value) !== JSON.stringify(baseline[key])) values[key] = value;
            }
            return values;
        }
        function validate() {
            for (const field of fields.values()) {
                const invalid = field.inputs.find(input => input.willValidate && !input.validity.valid);
                if (invalid) {
                    panel.open = true;
                    invalid.reportValidity();
                    return false;
                }
            }
            return true;
        }

        textUpdates.push(showError);
        applyDependencies();
        body.addEventListener('input', () => {
            clearError();
            applyDependencies();
            onEdit();
        });
        return {
            changes, validate, clearError,
            async save(values) {
                try {
                    const response = await fetch('/advanced/submit', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({id: group.id, values})
                    });
                    const data = await response.json();
                    if (response.ok && data.success) {
                        Object.assign(baseline, values);
                        return true;
                    }
                    currentError = data;
                } catch (_) {
                    currentError = {key: 'save_failed'};
                }
                panel.open = true;
                showError();
                return false;
            }
        };
    }

    function renderSettings() {
        const form = document.getElementById('advanced-form');
        const parent = document.getElementById('advanced-groups');
        const status = document.getElementById('advanced-feedback');
        const button = document.getElementById('advanced-save');
        let saving = false;
        let feedback = '';
        const hasChanges = () => sections.some(section => Object.keys(section.changes()).length);
        const updateButton = () => { button.disabled = saving || !hasChanges(); };
        const showFeedback = () => {
            status.textContent = feedback ? translate(feedback) : '';
            if (feedback === 'settings_saved') status.setAttribute('data-saved', '');
            else status.removeAttribute('data-saved');
        };
        parent.replaceChildren();
        textUpdates = [showFeedback];
        const sections = groups.map(group => {
            group.translations ||= {};
            return renderGroup(parent, group, () => {
                feedback = '';
                showFeedback();
                updateButton();
            });
        });
        handleSubmit = async event => {
            event.preventDefault();
            if (saving) return;
            const edits = sections.map(section => ({section, values: section.changes()}))
                .filter(({values}) => Object.keys(values).length);
            if (!edits.length) return;
            feedback = '';
            showFeedback();
            if (!edits.every(({section}) => section.validate())) return;

            saving = true;
            updateButton();
            let success = true;
            for (const {section, values} of edits) {
                section.clearError();
                if (!await section.save(values)) success = false;
            }
            saving = false;
            if (!success) feedback = 'save_failed';
            else if (!hasChanges()) feedback = 'settings_saved';
            showFeedback();
            updateButton();
        };
        if (!submitBound) {
            submitBound = true;
            form.addEventListener('submit', event => handleSubmit?.(event));
        }
        updateButton();
        form.hidden = false;
    }

    async function getGroups(locale) {
        const response = await fetch('/advanced/config?lang=' + encodeURIComponent(locale), {cache: 'no-store'});
        if (!response.ok) throw new Error(response.status);
        return response.json();
    }

    async function refreshLanguage() {
        for (const update of textUpdates) update();
        const locale = selectedLanguage();
        if (!groups.length || fetchedLanguages.has(locale)) return;
        fetchedLanguages.add(locale);
        try {
            for (const translated of await getGroups(locale)) {
                const group = groups.find(entry => entry.id === translated.id);
                if (group) Object.assign(group.translations, translated.translations);
            }
            for (const update of textUpdates) update();
        } catch (_) {
            fetchedLanguages.delete(locale);
        }
    }

    return {
        refreshLanguage,
        invalidate() {
            loaded = false;
            ++loadGeneration;
            fetchedLanguages.clear();
        },
        async load() {
            if (loaded) return;
            loaded = true;
            const generation = ++loadGeneration;
            const error = document.getElementById('advanced-load-error');
            error.textContent = '';
            try {
                const locale = selectedLanguage();
                const fetched = await getGroups(locale);
                if (generation !== loadGeneration) return;
                groups = fetched;
                fetchedLanguages.add(locale);
                renderSettings();
                refreshLanguage();
            } catch (_) {
                if (generation !== loadGeneration) return;
                loaded = false;
                error.textContent = translate('save_failed');
            }
        }
    };
})();
