function setupTextInput(socket, root = document) {
    const input = root.getElementById('text-input');
    const form = root.getElementById('text-form');
    const sendButton = root.getElementById('send-text');
    const status = root.getElementById('send-status');
    const connection = root.getElementById('text-connection');
    const compositionHint = root.getElementById('composition-hint');
    const recent = root.getElementById('recent-text');
    const lastSent = root.getElementById('last-sent-text');
    let composing = false;
    let revision = 0;
    let pending = null;

    function showStatus(message, kind) {
        status.textContent = message;
        status.dataset.kind = kind;
    }

    function update() {
        sendButton.disabled = composing || pending !== null || !socket.connected || input.value.length === 0;
        sendButton.textContent = pending ? '发送中…' : '发送到电脑';
        connection.textContent = socket.connected ? '已连接' : '连接中断';
        connection.dataset.connected = String(socket.connected);
        compositionHint.textContent = composing ? '请先完成输入法选词' : '支持多行，保留空格和换行';
    }

    input.addEventListener('compositionstart', () => {
        composing = true;
        update();
    });
    input.addEventListener('compositionend', () => {
        composing = false;
        update();
    });
    input.addEventListener('input', () => {
        revision += 1;
        update();
    });

    form.addEventListener('submit', event => {
        event.preventDefault();
        if (composing || event.isComposing || pending || input.value.length === 0) return;
        if (!socket.connected) {
            showStatus('连接已断开，草稿已保留。恢复连接后可手动发送。', 'error');
            update();
            return;
        }

        const request = { text: input.value, revision };
        pending = request;
        showStatus('正在发送，等待电脑确认…', 'pending');
        update();

        function onReply(error, reply) {
            // 超时、断线或后续发送之后到达的旧回执不能清空当前草稿。
            if (pending !== request) return;
            pending = null;
            if (error || !reply || typeof reply.ok !== 'boolean') {
                const reason = error ? '5 秒内未收到回执' : '未收到有效回执';
                showStatus(`${reason}，发送结果未确认。草稿已保留，请先检查电脑内容再决定是否重发。`, 'unconfirmed');
            } else if (!reply.ok) {
                showStatus(typeof reply.message === 'string' && reply.message
                    ? reply.message : '输入未完成，请检查电脑内容后再试。草稿已保留。', 'error');
            } else {
                lastSent.textContent = request.text;
                recent.hidden = false;
                // 发送等待期间仍允许编辑；回执只清除未被改动的那份草稿。
                const unchanged = !composing && revision === request.revision && input.value === request.text;
                if (unchanged) {
                    input.value = '';
                    revision += 1;
                }
                showStatus(unchanged ? '已发送，草稿已清空。' : '已发送；新修改的草稿已保留。', 'success');
            }
            update();
        }

        // volatile 防止断线期间排队并在重连后自动输入；timeout 同时清理回调。
        socket.timeout(5000).volatile.emit('type_text', { text: request.text }, onReply);
    });

    socket.on('connect', update);
    socket.on('disconnect', () => {
        if (pending) {
            pending = null;
            showStatus('连接中断，发送结果未确认。草稿已保留，请先检查电脑内容再决定是否重发。', 'unconfirmed');
        }
        update();
    });
    socket.on('connect_error', update);
    update();
}

if (typeof module !== 'undefined' && module.exports) module.exports = setupTextInput;
