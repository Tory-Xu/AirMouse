(() => {
    const panel = document.getElementById('connection-panel');
    // 手机横屏也默认折叠；用户手动展开后不随窗口大小反复切换。
    panel.open = !window.matchMedia('(max-width: 700px), (hover: none) and (pointer: coarse)').matches;

    document.querySelectorAll('.refresh-addresses').forEach(button => {
        button.addEventListener('click', () => window.location.reload());
    });

    const interfaces = document.getElementById('connection-interface');
    if (!interfaces) return;
    const address = document.getElementById('connection-url');
    const qr = document.getElementById('connection-qr');
    const feedback = document.getElementById('connection-feedback');

    interfaces.addEventListener('change', () => {
        const selected = interfaces.selectedOptions[0];
        address.value = selected.value;
        qr.src = selected.dataset.qr;
        feedback.textContent = '';
    });

    document.getElementById('copy-address').addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(address.value);
            feedback.textContent = '地址已复制';
        } catch {
            address.focus();
            address.select();
            address.setSelectionRange(0, address.value.length);
            feedback.textContent = '请长按或选中地址复制。';
        }
    });
})();
