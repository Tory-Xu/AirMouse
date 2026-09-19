const assert = require('node:assert/strict');
const { test } = require('node:test');
const setupTextInput = require('../static/js/text-input.js');

function editor() {
    const elements = new Map();
    const root = {
        getElementById(id) {
            if (!elements.has(id)) {
                elements.set(id, Object.assign(new EventTarget(), {
                    value: '', textContent: '', dataset: {}, hidden: id === 'recent-text',
                }));
            }
            return elements.get(id);
        },
    };
    const listeners = new Map();
    const calls = [];
    const socket = {
        connected: true,
        on(name, callback) { listeners.set(name, callback); },
        timeout(milliseconds) { this.deadline = milliseconds; return this; },
        get volatile() { this.dropWhenDisconnected = true; return this; },
        emit(name, payload, reply) {
            calls.push({ name, payload, reply, timeout: this.deadline, volatile: this.dropWhenDisconnected });
        },
    };
    setupTextInput(socket, root);
    const get = id => root.getElementById(id);
    return {
        calls, get,
        input: get('text-input'), button: get('send-text'), status: get('send-status'),
        edit(text) {
            get('text-input').value = text;
            get('text-input').dispatchEvent(new Event('input'));
        },
        compose(type) { get('text-input').dispatchEvent(new Event(type)); },
        submit() { get('text-form').dispatchEvent(new Event('submit', { cancelable: true })); },
        clear() { get('clear-text').dispatchEvent(new Event('click')); },
        connection(connected) {
            socket.connected = connected;
            listeners.get(connected ? 'connect' : 'disconnect')();
        },
    };
}

test('Chinese, English, emoji and whitespace stay in the draft until a successful acknowledgement', () => {
    const page = editor();
    const text = '  中文 English 😀\n第二行\n\t ';
    page.edit(text);
    page.submit();
    assert.equal(page.input.value, text);
    assert.equal(page.button.disabled, true);
    assert.deepEqual(page.calls[0].payload, { text });
    assert.equal(page.calls[0].name, 'type_text');
    assert.equal(page.calls[0].timeout, 5000);
    assert.equal(page.calls[0].volatile, true);
    page.calls[0].reply(null, { ok: true });
    assert.equal(page.input.value, '');
    assert.equal(page.get('last-sent-text').textContent, text);
    assert.equal(page.get('recent-text').hidden, false);
    assert.equal(page.status.dataset.kind, 'success');
});

function withRecent() {
    const page = editor();
    page.edit('上次发送');
    page.submit();
    page.calls[0].reply(null, { ok: true });
    page.edit('待清空草稿');
    return page;
}

test('clear removes draft and recent text only after success, with a volatile five-second request', () => {
    const page = withRecent();
    page.clear();
    const request = page.calls[1];
    assert.equal(request.name, 'clear_text');
    assert.deepEqual(request.payload, {});
    assert.equal(request.timeout, 5000);
    assert.equal(request.volatile, true);
    assert.equal(page.input.value, '待清空草稿');
    assert.equal(page.get('last-sent-text').textContent, '上次发送');
    assert.equal(page.button.disabled, true);
    assert.equal(page.get('clear-text').disabled, true);
    assert.equal(page.get('clear-text').textContent, '清空中…');
    request.reply(null, { ok: true });
    assert.equal(page.input.value, '');
    assert.equal(page.get('last-sent-text').textContent, '');
    assert.equal(page.get('recent-text').hidden, true);
    assert.equal(page.get('clear-text').disabled, false);
    assert.equal(page.status.dataset.kind, 'success');
});

test('clear works with an empty page and blocks repeated clears and sends', () => {
    const page = editor();
    assert.equal(page.get('clear-text').disabled, false);
    page.clear();
    page.clear();
    page.edit('新草稿');
    page.submit();
    assert.equal(page.calls.length, 1);
    page.calls[0].reply(null, { ok: true });
    assert.equal(page.input.value, '新草稿');
});

test('clear is blocked during send, IME composition and disconnection', () => {
    const page = editor();
    page.compose('compositionstart');
    assert.equal(page.get('clear-text').disabled, true);
    page.clear();
    assert.equal(page.calls.length, 0);
    page.compose('compositionend');
    page.edit('发送');
    page.submit();
    page.clear();
    assert.equal(page.calls.length, 1);
    page.calls[0].reply(null, { ok: true });
    page.connection(false);
    assert.equal(page.get('clear-text').disabled, true);
    page.clear();
    page.connection(true);
    assert.equal(page.calls.length, 1);
    assert.equal(page.get('clear-text').disabled, false);
});

test('clear success preserves edits, including an edit restored to the original value, and IME composition', () => {
    for (const change of ['edited', 'restored', 'composing']) {
        const page = withRecent();
        page.clear();
        if (change === 'composing') page.compose('compositionstart');
        else {
            page.edit('新草稿');
            if (change === 'restored') page.edit('待清空草稿');
        }
        const draft = page.input.value;
        page.calls[1].reply(null, { ok: true });
        assert.equal(page.input.value, draft);
        assert.equal(page.get('last-sent-text').textContent, '');
        assert.equal(page.get('recent-text').hidden, true);
    }
});

test('failed or invalid clear replies retain all page content', () => {
    for (const reply of [{ ok: false, message: '清空失败' }, { ok: false }, undefined, null, {}, { ok: 'true' }]) {
        const page = withRecent();
        page.clear();
        page.calls[1].reply(null, reply);
        assert.equal(page.input.value, '待清空草稿');
        assert.equal(page.get('last-sent-text').textContent, '上次发送');
        assert.equal(page.get('recent-text').hidden, false);
        assert.notEqual(page.status.dataset.kind, 'success');
        assert.equal(page.get('clear-text').disabled, false);
    }
});

test('clear timeout or disconnect preserves content, never retries, and ignores late replies during a new send', () => {
    for (const failure of ['timeout', 'disconnect']) {
        const page = withRecent();
        page.clear();
        if (failure === 'timeout') page.calls[1].reply(new Error('timeout'));
        else page.connection(false);
        assert.equal(page.input.value, '待清空草稿');
        assert.equal(page.get('last-sent-text').textContent, '上次发送');
        assert.equal(page.get('recent-text').hidden, false);
        assert.equal(page.status.dataset.kind, 'unconfirmed');
        page.connection(true);
        assert.equal(page.calls.length, 2);
        page.calls[1].reply(null, { ok: true });
        assert.equal(page.input.value, '待清空草稿');
        page.edit('新发送');
        page.submit();
        page.calls[1].reply(null, { ok: true });
        assert.equal(page.input.value, '新发送');
        assert.equal(page.get('last-sent-text').textContent, '上次发送');
        assert.equal(page.button.disabled, true);
        page.calls[2].reply(null, { ok: true });
        assert.equal(page.get('last-sent-text').textContent, '新发送');
    }
});

test('IME composition cannot submit before the user finishes selecting a word', () => {
    const page = editor();
    page.compose('compositionstart');
    page.edit('zhongwen');
    page.submit();
    assert.equal(page.button.disabled, true);
    assert.equal(page.calls.length, 0);
    page.edit('中文');
    page.compose('compositionend');
    assert.equal(page.button.disabled, false);
    page.submit();
    assert.deepEqual(page.calls[0].payload, { text: '中文' });
});

test('empty drafts are disabled, while spaces and newlines can be sent', () => {
    const page = editor();
    assert.equal(page.button.disabled, true);
    page.submit();
    assert.equal(page.calls.length, 0);
    page.edit(' \n ');
    page.submit();
    assert.deepEqual(page.calls[0].payload, { text: ' \n ' });
});

test('repeated submissions create only one request while waiting', () => {
    const page = editor();
    page.edit('发送一次');
    page.submit();
    page.submit();
    page.submit();
    assert.equal(page.calls.length, 1);
});

test('success preserves edits made while the previous draft was being sent', () => {
    const page = editor();
    page.edit('已发送的文字');
    page.submit();
    page.edit('等待时新改的草稿');
    page.calls[0].reply(null, { ok: true });
    assert.equal(page.input.value, '等待时新改的草稿');
    assert.equal(page.get('last-sent-text').textContent, '已发送的文字');
    assert.equal(page.button.disabled, false);
});

test('success does not interrupt a new IME composition', () => {
    const page = editor();
    page.edit('草稿');
    page.submit();
    page.compose('compositionstart');
    page.calls[0].reply(null, { ok: true });
    assert.equal(page.input.value, '草稿');
    assert.equal(page.button.disabled, true);
});

test('failure keeps the draft and the last confirmed send', () => {
    const page = editor();
    page.edit('第一次');
    page.submit();
    page.calls[0].reply(null, { ok: true });
    page.edit('失败时保留');
    page.submit();
    page.calls[1].reply(null, { ok: false, message: '系统输入失败' });
    assert.equal(page.input.value, '失败时保留');
    assert.equal(page.get('last-sent-text').textContent, '第一次');
    assert.equal(page.status.textContent, '系统输入失败');
    assert.equal(page.status.dataset.kind, 'error');
    assert.equal(page.button.disabled, false);
});

test('timeout keeps the draft, never retries and ignores late acknowledgements', () => {
    const page = editor();
    page.edit('结果未确认');
    page.submit();
    page.calls[0].reply(new Error('operation has timed out'));
    assert.equal(page.input.value, '结果未确认');
    assert.equal(page.status.dataset.kind, 'unconfirmed');
    assert.equal(page.calls.length, 1);
    page.calls[0].reply(null, { ok: true });
    assert.equal(page.input.value, '结果未确认');
    assert.equal(page.get('recent-text').hidden, true);
});

test('disconnect keeps the draft and an old acknowledgement cannot clear a newer submission', () => {
    const page = editor();
    page.edit('旧发送');
    page.submit();
    page.connection(false);
    assert.equal(page.status.dataset.kind, 'unconfirmed');
    assert.equal(page.button.disabled, true);
    page.connection(true);
    assert.equal(page.calls.length, 1);
    assert.equal(page.status.dataset.kind, 'unconfirmed');
    page.edit('新发送');
    page.submit();
    page.calls[0].reply(null, { ok: true });
    assert.equal(page.input.value, '新发送');
    assert.equal(page.button.disabled, true);
    page.calls[1].reply(null, { ok: true });
    assert.equal(page.input.value, '');
    assert.equal(page.get('last-sent-text').textContent, '新发送');
});

test('offline editing creates no buffered request and reconnecting does not send automatically', () => {
    const page = editor();
    page.connection(false);
    page.edit('离线草稿');
    page.submit();
    assert.equal(page.calls.length, 0);
    assert.equal(page.input.value, '离线草稿');
    page.connection(true);
    assert.equal(page.calls.length, 0);
    assert.equal(page.button.disabled, false);
});

test('missing or malformed acknowledgements never report success', () => {
    for (const reply of [undefined, null, {}, { ok: 'true' }]) {
        const page = editor();
        page.edit('保留');
        page.submit();
        page.calls[0].reply(null, reply);
        assert.equal(page.input.value, '保留');
        assert.equal(page.status.dataset.kind, 'unconfirmed');
    }
});
