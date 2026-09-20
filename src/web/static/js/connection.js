window.addEventListener('keydown', (e) => {
    if (e.key === 'Shift') document.body.classList.add('shift-move-active');
});
window.addEventListener('keyup', (e) => {
    if (e.key === 'Shift') document.body.classList.remove('shift-move-active');
});
window.addEventListener('blur', () => {
    document.body.classList.remove('shift-move-active');
});

// Native NiceGUI Socket.IO connection monitor
(function initNiceGUIStatusMonitor() {
    function updateBadge(online) {
        const badge = document.getElementById('gui-status-badge');
        const text = document.getElementById('gui-status-text');
        if (badge) {
            if (online) {
                badge.classList.remove('gui-status-offline');
            } else {
                badge.classList.add('gui-status-offline');
            }
        }
        if (text) {
            text.textContent = online ? 'Online' : 'Offline';
        }
    }

    function hookSocket() {
        if (window.socket) {
            updateBadge(window.socket.connected);
            window.socket.on('connect', () => updateBadge(true));
            window.socket.on('disconnect', () => updateBadge(false));
            window.socket.on('connect_error', () => updateBadge(false));
        } else {
            setTimeout(hookSocket, 100);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hookSocket);
    } else {
        hookSocket();
    }

    window.addEventListener('online', () => {
        if (window.socket) updateBadge(window.socket.connected);
    });
    window.addEventListener('offline', () => updateBadge(false));
})();
