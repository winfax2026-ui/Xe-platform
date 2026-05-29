/**
 * XE Platform - Core JavaScript
 * Dark theme fintech platform
 */

// =================== DOM Shortcut ===================
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// =================== API Helpers ===================
async function apiGet(url) {
    try {
        const res = await fetch(url, {
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
        });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || errData.message || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (err) {
        console.error(`GET ${url} error:`, err);
        throw err;
    }
}

async function apiPost(url, data = {}) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || errData.message || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (err) {
        console.error(`POST ${url} error:`, err);
        throw err;
    }
}

// =================== Toast System ===================
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) {
        // Auto-create container if missing
        const newContainer = document.createElement('div');
        newContainer.id = 'toastContainer';
        newContainer.className = 'toast-container';
        document.body.appendChild(newContainer);
    }

    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    const icons = {
        success: '\u2705',
        error: '\u274C',
        warning: '\u26A0\uFE0F',
        info: '\u2139\uFE0F'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || '\u2139\uFE0F'}</span><span>${message}</span>`;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 350);
    }, 4000);
}

// =================== Formatting ===================
function formatCurrency(amount, currency = 'USD') {
    const num = Number(amount) || 0;
    const symbols = { USD: '$', HKD: 'HK$', CNY: '\u00A5', TC: '' };
    const sym = symbols[currency] || '$';
    return `${sym}${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatCrypto(amount) {
    const num = Number(amount) || 0;
    if (num < 0.0001) return num.toExponential(4);
    if (num < 1) return num.toFixed(6);
    if (num < 1000) return num.toFixed(4);
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatTime(isoString) {
    if (!isoString) return '---';
    const d = new Date(isoString);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return '\u525B\u525B';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}\u5206\u949F\u524D`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}\u5C0F\u65F6\u524D`;

    return d.toLocaleDateString('zh-HK', {
        month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
    });
}

// =================== Sidebar Toggle ===================
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('open');
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
}

// =================== Auth Check ===================
async function checkAuth() {
    try {
        const data = await apiGet('/api/user/profile');
        if (data && data.id) {
            // Update sidebar user info
            const userNameEl = document.getElementById('sidebarUserName');
            const avatarEl = document.getElementById('sidebarUserAvatar');
            if (userNameEl && data.username) userNameEl.textContent = data.username;
            if (avatarEl && data.username) avatarEl.textContent = data.username.charAt(0).toUpperCase();

            // Update topbar username
            const topbarUser = document.getElementById('topbarUserName');
            if (topbarUser && data.username) topbarUser.textContent = data.username;

            return data;
        }
    } catch (e) {
        // Not logged in
        if (window.location.pathname !== '/' &&
            window.location.pathname !== '/auth/login' &&
            window.location.pathname !== '/auth/register') {
            // Redirect to login
            window.location.href = '/auth/login';
        }
    }
    return null;
}

// =================== Logout ===================
async function logout() {
    try {
        await apiPost('/auth/logout');
        showToast('\u5DF2\u5B89\u5168\u767B\u51FA', 'success');
        setTimeout(() => window.location.href = '/', 1000);
    } catch (err) {
        showToast('\u767B\u51FA\u5931\u8D25', 'error');
    }
}

// =================== Initialize ===================
document.addEventListener('DOMContentLoaded', () => {
    // Check auth on pages that need it
    const publicPages = ['/', '/auth/login', '/auth/register', '/public-records'];
    if (!publicPages.includes(window.location.pathname)) {
        checkAuth();
    }

    // Sidebar overlay click to close
    const overlay = document.getElementById('sidebarOverlay');
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // Close sidebar on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeSidebar();
    });
});

// =================== Animated Counter ===================
function animateCounter(elementId, target, decimals = 0, duration = 1800) {
    const el = document.getElementById(elementId);
    if (!el) return;

    let current = 0;
    const steps = 60;
    const step = target / steps;
    const interval = duration / steps;

    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        if (decimals === 0) {
            el.textContent = Math.floor(current).toLocaleString();
        } else {
            el.textContent = current.toLocaleString(undefined, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
        }
    }, interval);
}
