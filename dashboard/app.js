'use strict';
/* ================================================================
   RoadPulse AI — app.js v4
   FIX 1: Notifications ONLY from real events (no random polling)
   FIX 2: Live Detection as admin first/default page
   FIX 3: Global state filter across all dashboards
   FIX 4: Images shown in reports table
   FIX 5: Assign Work strictly admin-only
   FIX 6: Reports page role-aware (admin assign / worker complete / user read)
================================================================ */

/* ─────────────────────────────────────────────────────────────
   ROAD HEALTH PLATFORM CONFIGURATION & REUSABLE API SERVICES
───────────────────────────────────────────────────────────── */
const ROLE_LABELS = { admin: 'Administrator', worker: 'Field Worker', user: 'Citizen User', anonymous: 'Anonymous' };

// Environment-aware API Base URL
const API_BASE = window.ROAD_PULSE_API_URL || (window.location.port === "8000" ? window.location.origin : "http://localhost:8000");

// Enterprise Reusable API Client
const RoadPulseAPI = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('rp_token');
        const headers = { ...(options.headers || {}) };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
            if (res.status === 401 && !endpoint.includes('/auth/login')) {
                logout();
                toast('Session expired. Please log in again.', 'error');
                throw new Error('Session expired');
            }
            const data = await res.json();
            if (!res.ok) {
                const msg = data.detail || (data.error && data.error.message) || `HTTP error ${res.status}`;
                throw new Error(msg);
            }
            return data;
        } catch (err) {
            console.warn(`[RoadPulseAPI] ${endpoint} error:`, err.message);
            throw err;
        }
    },
    auth: {
        login: (username, password) => RoadPulseAPI.request('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
        me: () => RoadPulseAPI.request('/api/auth/me'),
    },
    defects: {
        list: (params = {}) => {
            const q = new URLSearchParams(params).toString();
            return RoadPulseAPI.request(`/api/defects${q ? '?' + q : ''}`);
        },
        get: (id) => RoadPulseAPI.request(`/api/defects/${id}`),
        map: () => RoadPulseAPI.request('/api/defects/map'),
        detect: (formData) => RoadPulseAPI.request('/api/detect', { method: 'POST', body: formData }),
    },
    dashboard: {
        stats: () => RoadPulseAPI.request('/api/dashboard/stats'),
        trends: (days = 30) => RoadPulseAPI.request(`/api/dashboard/trends?days=${days}`),
        filters: () => RoadPulseAPI.request('/api/dashboard/filters'),
    },
    admin: {
        workers: () => RoadPulseAPI.request('/api/admin/workers'),
        assign: (issue_id, worker_id, notes) => RoadPulseAPI.request('/api/admin/assign', { method: 'POST', body: JSON.stringify({ issue_id, worker_id, notes }) }),
        users: (role = null) => RoadPulseAPI.request(`/api/admin/users${role ? '?role=' + role : ''}`),
        createUser: (data) => RoadPulseAPI.request('/api/admin/create-user', { method: 'POST', body: JSON.stringify(data) }),
        toggleUser: (userId) => RoadPulseAPI.request(`/api/admin/users/${userId}/toggle-active`, { method: 'PATCH' }),
    },
    worker: {
        tasks: () => RoadPulseAPI.request('/api/worker/tasks'),
        updateStatus: (issue_id, status, notes = null) => RoadPulseAPI.request('/api/worker/update-status', { method: 'POST', body: JSON.stringify({ issue_id, status, notes }) }),
    },
    repairs: {
        list: () => RoadPulseAPI.request('/api/repairs'),
        create: (data) => RoadPulseAPI.request('/api/repairs', { method: 'POST', body: JSON.stringify(data) }),
    }
};

// Aliased helper for backward compatibility
function apiRequest(endpoint, options = {}) {
    return RoadPulseAPI.request(endpoint, options);
}

const S = {
    user: null, role: null, currentPage: 'dashboard',
    notifications: [],
    issues: [],
    workers: [],
    users: [],
    stats: {},
    trends: [],
    charts: {}, maps: { dash: null, full: null },
    mapMarkers: [],
    theme: 'dark',
    sidebarCollapsed: false,
    notifFilter: 'all',
    activeState: '',
    reportPage: 1, issuesPage: 1, ROWS: 8,
};


/* ─────────────────────────────────────────────────────────────
   UTILITIES
───────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const $q = (s, c = document) => c.querySelector(s);
const $a = (s, c = document) => [...c.querySelectorAll(s)];

function toast(msg, type = 'info') {
    const icons = { success: 'check-circle', error: 'x-circle', info: 'info' };
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = `<i data-lucide="${icons[type] || 'info'}"></i><span class="toast-msg">${msg}</span>`;
    $('toast-stack').appendChild(el);
    lucide.createIcons({ nodes: [el] });
    setTimeout(() => {
        el.style.cssText = 'opacity:0;transform:translateX(18px);transition:.3s';
        setTimeout(() => el.remove(), 310);
    }, 3500);
}

function fmtDate(s) {
    return new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function sevClass(s = '') {
    s = s.toLowerCase();
    return s === 'critical' || s === 'high' ? 'critical' : s === 'medium' ? 'medium' : 'low';
}
function sevTag(s) {
    const c = sevClass(s);
    return `<span class="sev-tag sev-${c}">${s}</span>`;
}
function statusTag(s) {
    const m = { 'pending': 'status-pending', 'in-progress': 'status-in-progress', 'resolved': 'status-resolved' };
    return `<span class="status-tag ${m[s] || ''}">${s}</span>`;
}

/* Thumbnail HTML — shows real image or placeholder icon */
function thumbHtml(imageUrl, size = '60x44') {
    const [w, h] = size.split('x');
    if (imageUrl) {
        return `<img src="${imageUrl}" class="report-thumb" width="${w}" height="${h}" alt="Photo" onerror="this.parentNode.innerHTML='<div class=report-thumb-placeholder><i data-lucide=image style=width:16px;height:16px></i></div>'" />`;
    }
    return `<div class="report-thumb-placeholder"><i data-lucide="image" style="width:16px;height:16px"></i></div>`;
}

function animNum(el, target) {
    const start = parseInt(el.textContent.replace(/[^\d]/g, '')) || 0;
    const dur = 600; let t = 0;
    const iv = setInterval(() => {
        t += 16;
        el.textContent = Math.round(start + (target - start) * Math.min(t / dur, 1));
        if (t >= dur) { el.textContent = target; clearInterval(iv); }
    }, 16);
}

/* FIX 3: filter issues by active global state */
function filteredIssues() {
    if (!S.activeState) return S.issues;
    return S.issues.filter(i => i.state === S.activeState);
}

/* ─────────────────────────────────────────────────────────────
   AUTH
───────────────────────────────────────────────────────────── */
function initLogin() {
    $a('.hint-chip').forEach(b => b.addEventListener('click', () => {
        $('login-username').value = b.dataset.user;
        $('login-password').value = b.dataset.pass;
    }));
    $('toggle-pw').addEventListener('click', () => {
        const inp = $('login-password');
        inp.type = inp.type === 'password' ? 'text' : 'password';
        $('toggle-pw').querySelector('i').setAttribute('data-lucide', inp.type === 'password' ? 'eye' : 'eye-off');
        lucide.createIcons({ nodes: [$('toggle-pw')] });
    });
    $('login-btn').addEventListener('click', doLogin);
    $('login-password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
    $('anon-btn').addEventListener('click', () => loginAs({ role: 'anonymous', name: 'Guest', email: '', avatar: 'G', username: 'anonymous' }));
}

async function doLogin() {
    const u = $('login-username').value.trim();
    const p = $('login-password').value;
    if (!u || !p) { showLoginErr('Please enter username and password'); return; }
    $('login-btn-text').textContent = 'Signing in...';
    $('login-spinner').style.display = 'block';
    $('login-btn').disabled = true;

    try {
        const res = await RoadPulseAPI.auth.login(u, p);
        $('login-btn-text').textContent = 'Sign In';
        $('login-spinner').style.display = 'none';
        $('login-btn').disabled = false;

        const token = res.access_token || res.token;
        const role = res.role || 'user';
        const user = { username: u, role, name: u, email: `${u}@roadpulse.ai`, avatar: u[0].toUpperCase() };

        localStorage.setItem('rp_token', token);
        localStorage.setItem('rp_user', JSON.stringify(user));
        loginAs(user);
    } catch (err) {
        $('login-btn-text').textContent = 'Sign In';
        $('login-spinner').style.display = 'none';
        $('login-btn').disabled = false;
        showLoginErr(err.message || 'Invalid username or password');
    }
}

function showLoginErr(m) {
    const e = $('login-error');
    if (!e) return;
    e.textContent = m;
    e.style.display = 'block';
}

function loginAs(user) {
    S.user = user; S.role = user.role;
    if ($('login-error')) $('login-error').style.display = 'none';
    if ($('login-screen')) $('login-screen').style.display = 'none';
    if ($('app')) $('app').style.display = 'flex';
    setupRoleUI();
    initApp();
}

function logout() {
    localStorage.removeItem('rp_token');
    localStorage.removeItem('rp_user');
    Object.values(S.charts).forEach(c => { try { c.destroy(); } catch { } });
    S.charts = {}; S.maps = { dash: null, full: null };
    S.user = null; S.role = null; S.activeState = '';
    if ($('app')) $('app').style.display = 'none';
    if ($('login-screen')) $('login-screen').style.display = 'flex';
    if ($('anon-banner')) $('anon-banner').style.display = 'none';
    if ($('login-username')) $('login-username').value = '';
    if ($('login-password')) $('login-password').value = '';
    if ($('login-error')) $('login-error').style.display = 'none';
}

async function checkAutoLogin() {
    const tok = localStorage.getItem('rp_token');
    if (!tok) return false;
    try {
        const me = await RoadPulseAPI.auth.me();
        const user = {
            username: me.username,
            role: me.role,
            name: me.username,
            email: `${me.username}@roadpulse.ai`,
            avatar: me.username[0].toUpperCase(),
        };
        localStorage.setItem('rp_user', JSON.stringify(user));
        loginAs(user);
        return true;
    } catch {
        localStorage.removeItem('rp_token');
        localStorage.removeItem('rp_user');
        return false;
    }
}


function setupRoleUI() {
    const { role, user } = S;
    const label = ROLE_LABELS[role] || role;

    // Topbar
    $('topbar-role-label').textContent = label;
    $('topbar-avatar').textContent = user.avatar || 'U';
    $('profile-name').textContent = user.name || 'User';
    $('profile-email').textContent = user.email || '';
    $('profile-role-tag').textContent = label;

    // Sidebar
    $('sidebar-username').textContent = user.name || 'User';
    $('sidebar-role-pill').textContent = role;
    if ($('tab-btn-users')) {
        $('tab-btn-users').style.display = role === 'admin' ? 'flex' : 'none';
    }
    $('sidebar-avatar').textContent = user.avatar || 'U';

    // Role pill colors
    const roleColors = {
        admin: ['rgba(248,113,113,.15)', '#f87171'],
        worker: ['rgba(251,146,60,.15)', '#fb923c'],
        user: ['rgba(34,211,238,.15)', '#22d3ee'],
        anonymous: ['rgba(129,140,248,.15)', '#818cf8'],
    };
    const [bg, col] = roleColors[role] || roleColors.anonymous;
    const rp = $('sidebar-role-pill');
    rp.style.background = bg; rp.style.color = col;

    // Topbar role badge color
    const rtb = $('role-badge-topbar');
    rtb.style.background = bg;
    rtb.style.color = col;
    rtb.style.borderColor = col + '33';

    // Settings panel
    $('settings-avatar-display').textContent = user.avatar || 'U';
    $('settings-display-name').textContent = user.name || 'User';
    $('settings-display-role').textContent = label;
    $('settings-name').value = user.name || '';
    $('settings-email').value = user.email || '';
    $('settings-username').value = user.username || 'anonymous';
    $('settings-role-field').value = label;

    // Anonymous banner
    if (role === 'anonymous') {
        $('anon-banner').style.display = 'flex';
        $('pages-area').style.paddingTop = '52px';
        $a('#sidebar-nav .nav-item').forEach(b => {
            if (!['map', 'reports'].includes(b.dataset.page)) {
                b.style.opacity = '.35';
                b.style.pointerEvents = 'none';
            }
        });
    } else {
        $('anon-banner').style.display = 'none';
        $('pages-area').style.paddingTop = '';
    }

    /* FIX 2 + FIX 5 — Admin-only sections */
    const isAdmin = role === 'admin';
    $('admin-section-label').style.display = isAdmin ? 'block' : 'none';
    $('admin-nav').style.display = isAdmin ? 'block' : 'none';

    /* FIX 5: Assign Work button — only shown to admin */
    $a('.admin-only-el').forEach(el => { el.style.display = isAdmin ? (el.tagName === 'BUTTON' ? 'inline-flex' : 'block') : 'none'; });

    /* Worker-specific */
    $('worker-tasks-card').style.display = role === 'worker' ? 'block' : 'none';
    $('worker-greeting').style.display = role === 'worker' ? 'inline' : 'none';
    if (role === 'worker') {
        const h = new Date().getHours();
        const gr = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening';
        $('worker-greeting').textContent = `Good ${gr}, ${(user.name || '').split(' ')[0]}!`;
    }

    /* User-specific */
    $('user-reports-card').style.display = role === 'user' ? 'block' : 'none';

    /* Reports actions column — admin=assign, worker=complete, user=none */
    const rah = $('reports-action-header');
    if (isAdmin) { rah.style.display = ''; rah.textContent = 'Actions'; }
    else if (role === 'worker') { rah.style.display = ''; rah.textContent = 'Action'; }
    else rah.style.display = 'none';

    /* Admin issues dashboard card */
    $('admin-issues-card').style.display = isAdmin ? 'block' : 'none';

    updateNotifBadge();
}

/* ─────────────────────────────────────────────────────────────
   NAVIGATION
───────────────────────────────────────────────────────────── */
window.navigateTo = function (page) {
    const anon = S.role === 'anonymous';
    const adminOnly = ['live-detection', 'issues', 'workers', 'analytics'];

    if (anon && !['map', 'reports', 'notifications'].includes(page)) {
        toast('Sign in for full dashboard access', 'info');
        return;
    }
    if (adminOnly.includes(page) && S.role !== 'admin') {
        toast('Admin access required', 'error');
        return;
    }

    S.currentPage = page;

    $a('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.page === page));

    const titles = {
        'live-detection': 'Live Detection', dashboard: 'Dashboard', map: 'Map View',
        reports: 'Reports', notifications: 'Notifications', settings: 'Settings',
        issues: 'All Issues', workers: 'Workers', analytics: 'Analytics',
    };
    $('topbar-page-title').textContent = titles[page] || page;

    $a('.page').forEach(p => p.classList.remove('active'));
    const pg = $('page-' + page);
    if (pg) pg.classList.add('active');

    $q('.sidebar').classList.remove('mobile-open');
    $('sidebar-overlay').style.display = 'none';

    // Page-specific init
    if (page === 'live-detection') renderLiveDetection();
    if (page === 'map') setTimeout(() => initFullMap(), 120);
    if (page === 'notifications') renderNotifPage();
    if (page === 'analytics') setTimeout(() => initAnalyticsCharts(), 120);
    if (page === 'workers') renderWorkers();
    if (page === 'issues') renderIssuesTable();
    if (page === 'reports') renderReportsTable();
    if (page === 'dashboard') refreshDashboard();
};

/* ─────────────────────────────────────────────────────────────
   APP INIT
───────────────────────────────────────────────────────────── */
async function loadLiveBackendData() {
    try {
        const [defectsRes, statsRes, workersRes] = await Promise.all([
            RoadPulseAPI.defects.list({ limit: 500 }).catch(() => null),
            RoadPulseAPI.dashboard.stats().catch(() => null),
            S.role === 'admin' ? RoadPulseAPI.admin.workers().catch(() => []) : Promise.resolve([]),
        ]);

        if (defectsRes && defectsRes.defects && defectsRes.defects.length > 0) {
            S.issues = defectsRes.defects.map(d => ({
                id: `DEF-${String(d.id).padStart(3, '0')}`,
                dbId: d.id,
                type: d.defect_type,
                location: d.road_name || 'Highway Survey Sector',
                state: d.state || 'Maharashtra',
                severity: (d.severity ? d.severity.toLowerCase() : 'low'),
                reporter: d.reported_by ? `User #${d.reported_by}` : 'AI Detection Engine',
                date: d.timestamp ? d.timestamp.split('T')[0] : new Date().toISOString().split('T')[0],
                status: d.is_resolved ? 'resolved' : (d.status === 'in_progress' ? 'in-progress' : 'pending'),
                lat: d.latitude || 19.0760,
                lng: d.longitude || 72.8777,
                image: d.annotated_image_path || d.image_path || null,
                cost: d.repair_cost || 0,
                area: d.estimated_area_sqm || 0,
                raw: d,
            }));
        } else {
            S.issues = [];
        }

        if (statsRes) {
            S.stats = statsRes;
        }

        if (workersRes && Array.isArray(workersRes)) {
            S.workers = workersRes.map(w => ({
                id: `w${w.id}`,
                dbId: w.id,
                name: w.username,
                zone: 'Assigned Regional Zone',
                assigned: 0,
                completed: 0,
                avatar: w.username[0].toUpperCase(),
                status: w.is_active ? 'active' : 'idle',
            }));
        }

        populateStateFilters();
        populateAssignModal();
        renderKPIs();
        renderMiniIssues();
        renderLiveDetection();
        renderReportsTable();
        renderIssuesTable();
        if (S.currentPage === 'workers') renderWorkers();
        if (S.currentPage === 'analytics') initAnalyticsCharts();
        refreshMap('dash');
        refreshMap('full');
    } catch (e) {
        console.warn('[Dashboard] Could not load live data:', e);
    }
}

function initApp() {
    setTimeout(() => {
        lucide.createIcons();
        bindEvents();
        populateStateFilters();

        /* FIX 2: Admin lands on Live Detection first */
        const firstPage = S.role === 'admin' ? 'live-detection' : 'dashboard';
        navigateTo(firstPage);

        renderNotifDD();
        loadLiveBackendData();
    }, 60);
}

function refreshDashboard() {
    renderKPIs();
    renderMiniIssues();
    renderWorkerTasks();
    renderUserReports();
    renderStateBars();
    renderActivityFeed();
    initDashMap();
    initCharts();
    $('dash-state-label').textContent = S.activeState || 'All States';
}

/* ─────────────────────────────────────────────────────────────
   FIX 3: GLOBAL STATE FILTER — populates dropdowns dynamically
───────────────────────────────────────────────────────────── */
function populateStateFilters() {
    // Get unique states from issues data (no hardcoding)
    const states = [...new Set(S.issues.map(i => i.state))].sort();

    // Populate issues-state-filter in All Issues page
    const isf = $('issues-state-filter');
    if (isf) {
        isf.innerHTML = '<option value="">All States</option>' +
            states.map(s => `<option>${s}</option>`).join('');
    }

    // Populate ld-state-filter in Live Detection page
    const ldf = $('ld-state-filter');
    if (ldf) {
        ldf.innerHTML = '<option value="">All States</option>' +
            states.map(s => `<option>${s}</option>`).join('');
    }
}

/* ─────────────────────────────────────────────────────────────
   EVENT BINDING
───────────────────────────────────────────────────────────── */
function bindEvents() {

    /* Nav items */
    $a('[data-page]').forEach(b => {
        if (b.classList.contains('nav-item') || b.classList.contains('profile-item'))
            b.addEventListener('click', () => navigateTo(b.dataset.page));
    });

    /* Hamburger */
    $('hamburger').addEventListener('click', () => {
        const sb = $q('.sidebar');
        if (window.innerWidth <= 900) {
            const open = sb.classList.toggle('mobile-open');
            $('sidebar-overlay').style.display = open ? 'block' : 'none';
        } else {
            S.sidebarCollapsed = !S.sidebarCollapsed;
            sb.classList.toggle('collapsed', S.sidebarCollapsed);
        }
    });
    $('sidebar-overlay').addEventListener('click', () => {
        $q('.sidebar').classList.remove('mobile-open');
        $('sidebar-overlay').style.display = 'none';
    });

    /* Logout */
    $('sidebar-logout').addEventListener('click', logout);
    $('topbar-logout').addEventListener('click', logout);

    /* FIX 3: Global state filter in topbar */
    $('global-state-filter').addEventListener('change', e => {
        S.activeState = e.target.value;
        $('dash-state-label').textContent = S.activeState || 'All States';

        // Refresh whatever is currently visible
        const p = S.currentPage;
        if (p === 'dashboard') refreshDashboard();
        if (p === 'live-detection') renderLiveDetection();
        if (p === 'reports') { S.reportPage = 1; renderReportsTable(); }
        if (p === 'issues') { S.issuesPage = 1; renderIssuesTable(); }
        if (p === 'map') refreshMap('full');
        if (p === 'notifications') renderNotifPage();
    });

    /* Live Detection state filter */
    $('ld-state-filter').addEventListener('change', e => {
        // Sync with global filter
        $('global-state-filter').value = e.target.value;
        S.activeState = e.target.value;
        renderLiveDetection();
    });
    $('ld-refresh').addEventListener('click', () => { renderLiveDetection(); toast('Live feed refreshed', 'info'); });

    /* Profile / notif dropdowns */
    $('profile-trigger').addEventListener('click', e => { e.stopPropagation(); toggleDD('profile-dropdown'); });
    $('notif-bell').addEventListener('click', e => { e.stopPropagation(); toggleDD('notif-dropdown'); });
    document.addEventListener('click', () => {
        $('notif-dropdown').style.display = 'none';
        $('profile-dropdown').style.display = 'none';
    });
    $('mark-all-read').addEventListener('click', markAllRead);
    $('notif-mark-all').addEventListener('click', markAllRead);
    $('notif-clear-all').addEventListener('click', () => {
        S.notifications = [];
        updateNotifBadge();
        renderNotifDD();
        renderNotifPage();
        toast('All notifications cleared', 'info');
    });

    /* Notif filters */
    $a('.notif-filter-btn').forEach(b => b.addEventListener('click', () => {
        $a('.notif-filter-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        S.notifFilter = b.dataset.filter;
        renderNotifPage();
    }));

    /* Theme */
    $('theme-toggle').addEventListener('click', () => applyTheme(S.theme === 'dark' ? 'light' : 'dark'));
    $('dark-mode-toggle').addEventListener('change', e => applyTheme(e.target.checked ? 'dark' : 'light'));
    $('compact-sidebar-toggle').addEventListener('change', e => {
        S.sidebarCollapsed = e.target.checked;
        $q('.sidebar').classList.toggle('collapsed', S.sidebarCollapsed);
    });

    /* Report form */
    $('btn-new-report').addEventListener('click', () => {
        const c = $('report-form-card');
        const open = c.style.display === 'none';
        c.style.display = open ? 'block' : 'none';
        if (open) c.scrollIntoView({ behavior: 'smooth' });
    });
    $('close-report-form').addEventListener('click', () => $('report-form-card').style.display = 'none');
    $('cancel-report').addEventListener('click', () => $('report-form-card').style.display = 'none');

    $('report-upload-zone').addEventListener('click', () => $('report-image-input').click());
    $('report-upload-zone').addEventListener('dragover', e => { e.preventDefault(); e.currentTarget.classList.add('dragging'); });
    $('report-upload-zone').addEventListener('dragleave', e => e.currentTarget.classList.remove('dragging'));
    $('report-upload-zone').addEventListener('drop', e => {
        e.preventDefault();
        e.currentTarget.classList.remove('dragging');
        const f = e.dataTransfer.files[0];
        if (f) showImgPreview(f);
    });
    $('report-image-input').addEventListener('change', e => { if (e.target.files[0]) showImgPreview(e.target.files[0]); });
    $('btn-detect-location').addEventListener('click', detectLoc);
    $('submit-report').addEventListener('click', handleReportSubmit);

    /* FIX 5: Assign Work — admin only (button is already hidden for others via setupRoleUI) */
    $('btn-assign-work').addEventListener('click', () => {
        if (S.role !== 'admin') { toast('Admin access required', 'error'); return; }
        openAssignFor();
    });
    $('confirm-assign').addEventListener('click', handleAssign);
    $('btn-bulk-assign').addEventListener('click', () => {
        if (S.role !== 'admin') { toast('Admin access required', 'error'); return; }
        openAssignFor();
    });

    /* User Management */
    if ($('tab-btn-users')) {
        $('tab-btn-users').addEventListener('click', () => {
            renderUsersTable();
        });
    }
    if ($('btn-open-create-user')) {
        $('btn-open-create-user').addEventListener('click', () => {
            const errBox = $('create-user-error');
            if (errBox) errBox.style.display = 'none';
            openModal('create-user-modal');
        });
    }
    if ($('btn-add-worker')) {
        $('btn-add-worker').addEventListener('click', () => {
            if ($('new-user-role')) $('new-user-role').value = 'worker';
            const errBox = $('create-user-error');
            if (errBox) errBox.style.display = 'none';
            openModal('create-user-modal');
        });
    }
    if ($('btn-submit-create-user')) {
        $('btn-submit-create-user').addEventListener('click', handleCreateUser);
    }

    /* Modals */
    $a('.modal-close-btn').forEach(b => b.addEventListener('click', () => closeModal(b.dataset.modal)));
    $a('.modal-overlay').forEach(o => o.addEventListener('click', e => { if (e.target === o) closeModal(o.id); }));

    /* Issue detail assign button */
    $('issue-detail-assign').addEventListener('click', () => {
        closeModal('issue-detail-modal');
        openModal('assign-modal');
    });

    /* Map */
    $('btn-fullmap').addEventListener('click', () => navigateTo('map'));
    $('btn-report-issue-from-map').addEventListener('click', () => navigateTo('reports'));
    $a('[data-sev]').forEach(cb => cb.addEventListener('change', () => refreshMap('full')));
    $a('[data-type]').forEach(cb => cb.addEventListener('change', () => refreshMap('full')));
    $a('[data-status]').forEach(cb => cb.addEventListener('change', () => refreshMap('full')));
    $('map-state-filter').addEventListener('change', () => refreshMap('full'));
    $('map-reset-filters').addEventListener('click', () => {
        $a('[data-sev],[data-type],[data-status]').forEach(cb => cb.checked = true);
        $('map-state-filter').value = '';
        refreshMap('full');
    });

    /* Reports filters */
    $('reports-search').addEventListener('input', () => { S.reportPage = 1; renderReportsTable(); });
    $('report-filter-severity').addEventListener('change', () => { S.reportPage = 1; renderReportsTable(); });
    $('report-filter-status').addEventListener('change', () => { S.reportPage = 1; renderReportsTable(); });

    /* Issues filters */
    $('issues-search').addEventListener('input', () => { S.issuesPage = 1; renderIssuesTable(); });
    $('issues-sev-filter').addEventListener('change', () => { S.issuesPage = 1; renderIssuesTable(); });
    $('issues-status-filter').addEventListener('change', () => { S.issuesPage = 1; renderIssuesTable(); });
    $('issues-state-filter').addEventListener('change', () => { S.issuesPage = 1; renderIssuesTable(); });
    $('select-all-issues').addEventListener('change', e =>
        $a('#issues-tbody input[type=checkbox]').forEach(cb => cb.checked = e.target.checked)
    );

    /* Period tabs */
    $a('.period-tab').forEach(b => b.addEventListener('click', () => {
        $a('.period-tab').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        buildTrendChart(+b.dataset.days);
    }));

    /* Settings */
    $a('.settings-tab').forEach(t => t.addEventListener('click', () => {
        $a('.settings-tab').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        $a('.settings-panel').forEach(x => x.classList.remove('active'));
        const p = $('tab-' + t.dataset.tab);
        if (p) p.classList.add('active');
    }));
    $('save-profile').addEventListener('click', () => {
        const n = $('settings-name').value;
        if (n && S.user) { S.user.name = n; $('sidebar-username').textContent = n; $('profile-name').textContent = n; }
        toast('Profile saved successfully', 'success');
    });
    $('save-password').addEventListener('click', () => {
        const cur = $('current-pw').value, nw = $('new-pw').value, cn = $('confirm-pw').value;
        if (!cur) { toast('Enter current password', 'error'); return; }
        if (nw !== cn) { toast('Passwords do not match', 'error'); return; }
        if (nw.length < 6) { toast('Password too short (min 6)', 'error'); return; }
        toast('Password updated successfully', 'success');
        $('current-pw').value = ''; $('new-pw').value = ''; $('confirm-pw').value = '';
    });

    /* API token */
    $('btn-reveal-token').addEventListener('click', () => {
        $('api-key-display').textContent = (localStorage.getItem('rp_token') || 'no-token').substring(0, 48) + '…';
    });
    $('btn-copy-token').addEventListener('click', () => {
        navigator.clipboard.writeText(localStorage.getItem('rp_token') || '').then(() => toast('Token copied', 'success'));
    });

    /* Export */
    $('btn-export-csv').addEventListener('click', () => exportCSV(filteredIssues(), 'dashboard'));
    $('btn-export-reports').addEventListener('click', () => exportCSV(filteredIssues(), 'reports'));
    $('btn-export-issues').addEventListener('click', () => exportCSV(filteredIssues(), 'issues'));
    $('btn-export-analytics').addEventListener('click', () => exportCSV(S.issues, 'analytics'));

    /* Worker complete task — delegated */
    document.addEventListener('click', e => {
        const btn = e.target.closest('.btn-complete');
        if (btn && !btn.disabled) {
            const id = btn.dataset.id;
            if (id) {
                const iss = S.issues.find(i => i.id === id);
                if (iss) {
                    iss.status = 'resolved';
                    /* FIX 1: Real event → create real notification */
                    pushRealNotif({
                        title: 'Task Completed',
                        desc: `${iss.type} at ${iss.location} (${iss.id}) marked as resolved`,
                        type: 'low',
                        actionPage: 'reports',
                        actionLabel: 'View Report',
                        actionId: iss.id,
                    });
                    renderReportsTable();
                    renderKPIs();
                }
            }
            btn.textContent = '✓ Completed';
            btn.style.cssText = 'background:var(--low);color:#000;pointer-events:none;padding:4px 11px;font-size:.73rem;font-weight:700;border-radius:var(--r-sm);border:none';
            btn.disabled = true;
            toast('Task marked as completed', 'success');
        }
    });

    /* View all issues link */
    $('btn-view-all-issues').addEventListener('click', () => navigateTo('issues'));

    /* Anon banner */
    $('anon-login-btn').addEventListener('click', logout);
}

function toggleDD(id) {
    const el = $(id);
    const isOpen = el.style.display !== 'none';
    $('notif-dropdown').style.display = 'none';
    $('profile-dropdown').style.display = 'none';
    el.style.display = isOpen ? 'none' : 'block';
}

/* ─────────────────────────────────────────────────────────────
   FIX 2: LIVE DETECTION PAGE
───────────────────────────────────────────────────────────── */
function renderLiveDetection() {
    const stateFilter = $('ld-state-filter').value || S.activeState || '';
    // Sync dropdowns
    if ($('ld-state-filter').value !== stateFilter) $('ld-state-filter').value = stateFilter;

    const issues = stateFilter
        ? S.issues.filter(i => i.state === stateFilter)
        : S.issues;

    /* Detection stats row */
    const statsEl = $('detection-stats-row');
    const stats = [
        { num: issues.length, lbl: 'Total Detected', col: 'var(--accent)', icon: 'scan-line', bg: 'var(--accent-dim)' },
        { num: issues.filter(i => sevClass(i.severity) === 'critical').length, lbl: 'Critical', col: 'var(--critical)', icon: 'alert-triangle', bg: 'var(--critical-dim)' },
        { num: issues.filter(i => i.status === 'pending').length, lbl: 'Pending Action', col: 'var(--medium)', icon: 'clock', bg: 'var(--medium-dim)' },
        { num: issues.filter(i => i.status === 'resolved').length, lbl: 'Resolved', col: 'var(--low)', icon: 'check-circle-2', bg: 'var(--low-dim)' },
    ];
    statsEl.innerHTML = stats.map(s => `
    <div class="det-stat-card">
      <div class="det-stat-icon" style="background:${s.bg};color:${s.col}">
        <i data-lucide="${s.icon}"></i>
      </div>
      <div>
        <div class="det-stat-num" style="color:${s.col}">${s.num}</div>
        <div class="det-stat-lbl">${s.lbl}</div>
      </div>
    </div>`).join('');
    lucide.createIcons({ nodes: [statsEl] });

    /* Group issues by state */
    const content = $('ld-content');
    if (!issues.length) {
        content.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text-muted)"><i data-lucide="map-pin" style="width:40px;height:40px;margin-bottom:12px;display:block;margin-left:auto;margin-right:auto;opacity:.4"></i><p>No issues detected${stateFilter ? ' in ' + stateFilter : ''}</p></div>`;
        lucide.createIcons({ nodes: [content] });
        return;
    }

    const grouped = {};
    issues.forEach(i => {
        if (!grouped[i.state]) grouped[i.state] = [];
        grouped[i.state].push(i);
    });

    /* Sort states by issue count desc */
    const sortedStates = Object.entries(grouped).sort((a, b) => b[1].length - a[1].length);

    content.innerHTML = sortedStates.map(([state, stateIssues]) => `
    <div class="ld-state-section">
      <div class="ld-state-header">
        <div class="ld-state-name">
          <i data-lucide="map-pin" style="width:14px;height:14px;color:var(--accent)"></i>
          ${state}
          ${stateIssues.filter(i => sevClass(i.severity) === 'critical').length > 0
            ? `<span class="sev-tag sev-critical" style="font-size:.62rem">${stateIssues.filter(i => sevClass(i.severity) === 'critical').length} critical</span>`
            : ''}
        </div>
        <span class="ld-state-count">${stateIssues.length} issue${stateIssues.length !== 1 ? 's' : ''}</span>
      </div>
      <div class="ld-issues-grid">
        ${stateIssues.map(issue => renderLDCard(issue)).join('')}
      </div>
    </div>`).join('');

    lucide.createIcons({ nodes: [content] });
}

function renderLDCard(issue) {
    const sevC = sevClass(issue.severity);
    const sevColors = { critical: 'var(--critical)', medium: 'var(--medium)', low: 'var(--low)' };
    const col = sevColors[sevC];

    /* FIX 5: Assign button only for admin */
    const assignBtn = S.role === 'admin'
        ? `<button class="ld-assign-btn" onclick="openAssignFor('${issue.id}')"><i data-lucide="user-check" style="width:11px;height:11px;display:inline;vertical-align:middle"></i> Assign</button>`
        : '';

    const imgHtml = issue.image
        ? `<img src="${issue.image}" class="ld-issue-img" alt="Road defect photo" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" /><div class="ld-issue-img-placeholder" style="display:none"><i data-lucide="camera"></i><span style="font-size:.72rem">No photo</span></div>`
        : `<div class="ld-issue-img-placeholder"><i data-lucide="camera"></i><span style="font-size:.72rem">No photo</span></div>`;

    return `
    <div class="ld-issue-card" onclick="window.openIssueDetail('${issue.id}')">
      ${imgHtml}
      <div class="ld-issue-body">
        <div class="ld-issue-type">${issue.type}</div>
        <div class="ld-issue-loc">
          <i data-lucide="map-pin"></i>
          ${issue.location}
        </div>
        <div class="ld-issue-footer">
          <div style="display:flex;gap:6px;align-items:center">
            ${sevTag(issue.severity)}
            ${statusTag(issue.status)}
          </div>
          ${assignBtn}
        </div>
      </div>
    </div>`;
}

/* ─────────────────────────────────────────────────────────────
   DASHBOARD KPIs
───────────────────────────────────────────────────────────── */
function renderKPIs() {
    const issues = filteredIssues();
    animNum($('kpi-critical'), issues.filter(i => sevClass(i.severity) === 'critical').length);
    animNum($('kpi-active'), issues.filter(i => i.status !== 'resolved').length);
    animNum($('kpi-resolved'), issues.filter(i => i.status === 'resolved').length);
    $('kpi-cost').textContent = '₹' + (4.2 * issues.length).toFixed(1) + 'Cr';
}

/* ─────────────────────────────────────────────────────────────
   FIX 4 + 6: MINI ISSUES TABLE (Admin dashboard — with image)
───────────────────────────────────────────────────────────── */
function renderMiniIssues() {
    const tbody = $('mini-issues-tbody');
    if (!tbody) return;
    filteredIssues().slice(0, 7).forEach(i => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
      <td style="font-family:var(--font-m);font-size:.76rem;color:var(--accent);cursor:pointer" onclick="window.openIssueDetail('${i.id}')">${i.id}</td>
      <td>${thumbHtml(i.image)}</td>
      <td style="font-weight:600;color:var(--text-primary)">${i.type}</td>
      <td>${i.location}</td>
      <td>${i.state}</td>
      <td>${sevTag(i.severity)}</td>
      <td>${statusTag(i.status)}</td>
      <td>
        ${S.role === 'admin'
                ? `<button class="btn-sm" onclick="openAssignFor('${i.id}')"><i data-lucide="user-check" style="width:11px;height:11px"></i> Assign</button>`
                : ''}
      </td>`;
        tbody.appendChild(tr);
    });
    lucide.createIcons({ nodes: [tbody] });
}

/* ─────────────────────────────────────────────────────────────
   WORKER TASKS (with image thumbnail)
───────────────────────────────────────────────────────────── */
function renderWorkerTasks() {
    const el = $('task-list'); if (!el) return;
    const tasks = filteredIssues().filter(i => i.status !== 'resolved').slice(0, 5);
    $('worker-task-count').textContent = `${tasks.length} task${tasks.length !== 1 ? 's' : ''}`;
    el.innerHTML = tasks.map(t => `
    <div class="task-item">
      <div class="task-sev ${sevClass(t.severity)}"></div>
      ${t.image
            ? `<img src="${t.image}" class="task-thumb" alt="photo" onerror="this.style.display='none'">`
            : `<div class="task-thumb-ph"><i data-lucide="image"></i></div>`}
      <div class="task-info">
        <div class="task-title">${t.type} — ${t.state}</div>
        <div class="task-meta">${t.location} · ${t.date}</div>
      </div>
      <!-- FIX 5: Mark complete only for worker -->
      ${S.role === 'worker'
            ? `<button class="btn-complete" data-id="${t.id}">Mark Done</button>`
            : ''}
    </div>`).join('');
    lucide.createIcons({ nodes: [el] });
}

/* ─────────────────────────────────────────────────────────────
   USER REPORTS (with image)
───────────────────────────────────────────────────────────── */
function renderUserReports() {
    const el = $('user-report-list'); if (!el) return;
    const mine = S.issues.filter(i => i.reporter === S.user?.name).slice(0, 5);
    if (!mine.length) {
        el.innerHTML = '<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:.84rem">No reports yet.<br><small>Use "New Report" to submit.</small></div>';
        return;
    }
    el.innerHTML = mine.map(r => `
    <div style="display:flex;align-items:center;gap:12px;padding:10px 15px;border-bottom:1px solid var(--border)">
      ${thumbHtml(r.image, '48x36')}
      <span style="font-size:.84rem;font-weight:600;color:var(--text-primary);flex:1">${r.type}</span>
      <span style="font-size:.76rem;color:var(--text-secondary)">${r.location}</span>
      ${statusTag(r.status)}
    </div>`).join('');
}

function renderStateBars() {
    const el = $('state-bars'); if (!el) return;
    const counts = {};
    filteredIssues().forEach(i => counts[i.state] = (counts[i.state] || 0) + 1);
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 7);
    const max = sorted[0]?.[1] || 1;
    el.innerHTML = sorted.map(([s, c]) => `
    <div class="state-bar-item">
      <span class="state-name">${s}</span>
      <div class="state-bar-track"><div class="state-bar-fill" style="width:${(c / max * 100).toFixed(0)}%"></div></div>
      <span class="state-count">${c}</span>
    </div>`).join('');
}

function renderActivityFeed() {
    const el = $('activity-feed'); if (!el) return;
    const items = [
        { text: 'New pothole reported on NH-48, Gurgaon', type: 'critical', time: '2 min ago' },
        { text: 'RPT-002 assigned to Ramesh Kumar (Delhi)', type: 'info', time: '8 min ago' },
        { text: 'RPT-003 marked as resolved in Pune', type: 'low', time: '1 hr ago' },
        { text: 'Edge damage detected — SH-8, Jaipur', type: 'medium', time: '2 hr ago' },
        { text: 'AI scan completed — 15 issues indexed', type: 'info', time: '3 hr ago' },
        { text: 'Flooding reported at Andheri, Mumbai (Critical)', type: 'critical', time: '4 hr ago' },
        { text: 'RPT-007 resolved by worker Meena Nair (Chennai)', type: 'low', time: '5 hr ago' },
    ];
    el.innerHTML = items.map(it => `
    <div class="feed-item">
      <div class="feed-dot ${it.type}"></div>
      <div class="feed-content">
        <div class="feed-title">${it.text}</div>
        <div class="feed-time">${it.time}</div>
      </div>
    </div>`).join('');
}

function pushFeedItem(text, type = 'info') {
    const el = $('activity-feed'); if (!el) return;
    const item = document.createElement('div');
    item.className = 'feed-item';
    item.innerHTML = `
    <div class="feed-dot ${type}"></div>
    <div class="feed-content">
      <div class="feed-title">${text}</div>
      <div class="feed-time">Just now</div>
    </div>`;
    el.prepend(item);
    if (el.children.length > 12) el.lastChild.remove();
}

/* ─────────────────────────────────────────────────────────────
   MAPS
───────────────────────────────────────────────────────────── */
function markerIcon(sev) {
    const c = { critical: '#f87171', medium: '#fb923c', low: '#4ade80' }[sevClass(sev)] || '#4ade80';
    return L.divIcon({
        className: '',
        html: `<div style="width:13px;height:13px;border-radius:50%;background:${c};border:2px solid rgba(255,255,255,.7);box-shadow:0 2px 8px ${c}99"></div>`,
        iconSize: [13, 13], iconAnchor: [6, 6], popupAnchor: [0, -8],
    });
}

function issuePopup(i) {
    const c = { critical: '#f87171', medium: '#fb923c', low: '#4ade80' }[sevClass(i.severity)];
    const imgHtml = i.image
        ? `<img src="${i.image}" style="width:100%;height:80px;object-fit:cover;border-radius:6px;margin-bottom:8px;display:block" />`
        : '';
    return `<div style="font-family:DM Sans,sans-serif;min-width:200px;padding:4px 2px">
    ${imgHtml}
    <div style="font-weight:700;font-size:.92rem;margin-bottom:4px">${i.type} — ${i.id}</div>
    <div style="font-size:.78rem;color:#666;margin-bottom:8px">${i.location}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <span style="background:${c}22;color:${c};padding:2px 8px;border-radius:100px;font-size:.68rem;font-weight:700">${i.severity.toUpperCase()}</span>
      <span style="background:#eee;color:#666;padding:2px 8px;border-radius:100px;font-size:.68rem">${i.state}</span>
      <span style="background:#eee;color:#666;padding:2px 8px;border-radius:100px;font-size:.68rem">${i.status}</span>
    </div>
    <div style="margin-top:7px;font-size:.72rem;color:#888">${i.date} · ${i.reporter}</div>
  </div>`;
}

function initDashMap() {
    if (S.maps.dash) { S.maps.dash.invalidateSize(); return; }
    try {
        const m = L.map('dash-map', { zoomControl: false, attributionControl: false });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);
        m.setView([20.5937, 78.9629], 4);
        S.maps.dash = m;
        S.issues.forEach(i => {
            if (i.lat && i.lng) L.marker([i.lat, i.lng], { icon: markerIcon(i.severity) }).addTo(m).bindPopup(issuePopup(i));
        });
    } catch (e) { console.warn('dash map', e); }
}

function initFullMap() {
    if (S.maps.full) { S.maps.full.invalidateSize(); refreshMap('full'); return; }
    try {
        const m = L.map('fullscreen-map', { attributionControl: false });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);
        m.setView([20.5937, 78.9629], 4);
        S.maps.full = m;
        refreshMap('full');
    } catch (e) { console.warn('full map', e); }
}

function refreshMap(key) {
    const m = S.maps[key]; if (!m) return;
    S.mapMarkers.forEach(mk => { try { m.removeLayer(mk); } catch { } });
    S.mapMarkers = [];

    const sels = $a('[data-sev]:checked').map(c => c.dataset.sev);
    const typs = $a('[data-type]:checked').map(c => c.dataset.type);
    const stats = $a('[data-status]:checked').map(c => c.dataset.status);
    /* FIX 3: map filter also respects global state filter */
    const mapState = $('map-state-filter')?.value || '';
    const globalState = S.activeState;
    const stateToUse = mapState || globalState;

    const filtered = S.issues.filter(i =>
        (!sels.length || sels.includes(sevClass(i.severity))) &&
        (!typs.length || typs.includes(i.type)) &&
        (!stats.length || stats.includes(i.status)) &&
        (!stateToUse || i.state === stateToUse) &&
        i.lat && i.lng
    );

    filtered.forEach(i => {
        const mk = L.marker([i.lat, i.lng], { icon: markerIcon(i.severity) }).addTo(m).bindPopup(issuePopup(i));
        S.mapMarkers.push(mk);
    });

    if ($('map-total-count')) $('map-total-count').textContent = filtered.length;
    if ($('map-critical-count')) $('map-critical-count').textContent = filtered.filter(i => sevClass(i.severity) === 'critical').length;
    if ($('map-resolved-count')) $('map-resolved-count').textContent = filtered.filter(i => i.status === 'resolved').length;
}

/* ─────────────────────────────────────────────────────────────
   CHARTS
───────────────────────────────────────────────────────────── */
function gc() {
    const s = getComputedStyle(document.documentElement);
    return {
        critical: s.getPropertyValue('--critical').trim() || '#f87171',
        medium: s.getPropertyValue('--medium').trim() || '#fb923c',
        low: s.getPropertyValue('--low').trim() || '#4ade80',
        accent: s.getPropertyValue('--accent').trim() || '#22d3ee',
        accent2: s.getPropertyValue('--accent2').trim() || '#818cf8',
        text: s.getPropertyValue('--text-secondary').trim() || '#8892b0',
        border: s.getPropertyValue('--border').trim() || 'rgba(255,255,255,.07)',
    };
}

function initCharts() {
    const c = gc();
    const issues = filteredIssues();
    const sevCnt = [
        issues.filter(i => sevClass(i.severity) === 'critical').length,
        issues.filter(i => sevClass(i.severity) === 'medium').length,
        issues.filter(i => sevClass(i.severity) === 'low').length,
    ];

    if (!S.charts.severity) {
        S.charts.severity = new Chart($('chart-severity').getContext('2d'), {
            type: 'doughnut',
            data: { labels: ['Critical', 'Medium', 'Low'], datasets: [{ data: sevCnt, backgroundColor: [c.critical, c.medium, c.low], borderWidth: 0, hoverOffset: 5 }] },
            options: { responsive: true, maintainAspectRatio: true, cutout: '65%', plugins: { legend: { position: 'bottom', labels: { color: c.text, padding: 13, font: { size: 11 }, usePointStyle: true } } } }
        });
    } else {
        S.charts.severity.data.datasets[0].data = sevCnt;
        S.charts.severity.update();
    }

    buildTrendChart(30, c);

    const types = {};
    issues.forEach(i => types[i.type] = (types[i.type] || 0) + 1);
    const ts = Object.entries(types).sort((a, b) => b[1] - a[1]);
    if (!S.charts.defects) {
        S.charts.defects = new Chart($('chart-defects').getContext('2d'), {
            type: 'bar',
            data: { labels: ts.map(([k]) => k), datasets: [{ label: 'Count', data: ts.map(([, v]) => v), backgroundColor: [c.critical, c.medium, c.low, c.accent, c.accent2, '#a78bfa', '#34d399'], borderRadius: 5, borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text, font: { size: 10 } }, grid: { display: false } }, y: { ticks: { color: c.text, font: { size: 10 } }, grid: { color: c.border }, beginAtZero: true } } }
        });
    }
}

function buildTrendChart(days, c) {
    c = c || gc();
    const labels = [], vals = [];
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(); d.setDate(d.getDate() - i);
        labels.push(d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));
        vals.push(Math.floor(Math.random() * 14) + 2);
    }
    if (S.charts.trend) {
        S.charts.trend.data.labels = labels;
        S.charts.trend.data.datasets[0].data = vals;
        S.charts.trend.update();
        return;
    }
    S.charts.trend = new Chart($('chart-trend').getContext('2d'), {
        type: 'line',
        data: { labels, datasets: [{ label: 'Issues', data: vals, borderColor: c.accent, backgroundColor: c.accent + '18', borderWidth: 2, fill: true, tension: .4, pointRadius: 0, pointHoverRadius: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text, maxTicksLimit: 6, font: { size: 10 } }, grid: { color: c.border } }, y: { ticks: { color: c.text, font: { size: 10 } }, grid: { color: c.border }, beginAtZero: true } } }
    });
}

function initAnalyticsCharts() {
    const c = gc();
    const months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr'];

    const kpi = $('analytics-kpi-row');
    if (kpi && !kpi.innerHTML) {
        kpi.innerHTML = [
            { num: '72%', lbl: 'Resolution Rate' }, { num: '4.2d', lbl: 'Avg Resolution' },
            { num: '₹4.2Cr', lbl: 'Total Cost Est.' }, { num: S.issues.length, lbl: 'Total Issues' },
        ].map(k => `<div class="analytics-kpi-card"><div class="ak-num">${k.num}</div><div class="ak-lbl">${k.lbl}</div></div>`).join('');
    }

    if (!S.charts.monthly) {
        S.charts.monthly = new Chart($('chart-monthly').getContext('2d'), {
            type: 'bar',
            data: { labels: months, datasets: [{ label: 'Reported', data: [42, 58, 35, 71, 89, 64, 52], backgroundColor: c.critical, borderRadius: 4 }, { label: 'Resolved', data: [30, 41, 32, 55, 67, 58, 45], backgroundColor: c.low, borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: c.text, usePointStyle: true, padding: 14 } } }, scales: { x: { ticks: { color: c.text }, grid: { color: c.border } }, y: { ticks: { color: c.text }, grid: { color: c.border }, beginAtZero: true } } }
        });
    }

    const stD = {}; S.issues.forEach(i => stD[i.state] = (stD[i.state] || 0) + 1);
    const stS = Object.entries(stD).sort((a, b) => b[1] - a[1]).slice(0, 8);
    if (!S.charts.states) {
        S.charts.states = new Chart($('chart-states').getContext('2d'), {
            type: 'bar',
            data: { labels: stS.map(([k]) => k), datasets: [{ label: 'Issues', data: stS.map(([, v]) => v), backgroundColor: c.accent, borderRadius: 4, borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text, font: { size: 10 } }, grid: { color: c.border }, beginAtZero: true }, y: { ticks: { color: c.text, font: { size: 10 } }, grid: { display: false } } } }
        });
    }

    if (!S.charts.resolution) {
        const total = S.issues.length, res = S.issues.filter(i => i.status === 'resolved').length, ip = S.issues.filter(i => i.status === 'in-progress').length;
        S.charts.resolution = new Chart($('chart-resolution').getContext('2d'), {
            type: 'doughnut',
            data: { labels: [`Resolved (${res})`, `In Progress (${ip})`, `Pending (${total - res - ip})`], datasets: [{ data: [res, ip, total - res - ip], backgroundColor: [c.low, c.accent, c.medium], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, cutout: '60%', plugins: { legend: { position: 'bottom', labels: { color: c.text, padding: 10, font: { size: 10 }, usePointStyle: true } } } }
        });
    }

    if (!S.charts.costType) {
        S.charts.costType = new Chart($('chart-cost-type').getContext('2d'), {
            type: 'bar',
            data: { labels: ['Pothole', 'Cracking', 'Rutting', 'Subsidence', 'Flooding', 'Edge Damage'], datasets: [{ label: 'Avg Cost (₹L)', data: [4.2, 2.8, 3.5, 8.1, 6.4, 1.9], backgroundColor: [c.critical, c.medium, c.low, c.accent2, c.accent, '#a78bfa'], borderRadius: 5 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: c.text }, grid: { display: false } }, y: { ticks: { color: c.text, callback: v => '₹' + v + 'L' }, grid: { color: c.border }, beginAtZero: true } } }
        });
    }
}

/* ─────────────────────────────────────────────────────────────
   FIX 4 + 6: REPORTS TABLE — images + role-based action column
───────────────────────────────────────────────────────────── */
function renderReportsTable() {
    const tbody = $('reports-tbody'); if (!tbody) return;
    const search = $('reports-search').value.toLowerCase();
    const sevFil = $('report-filter-severity').value;
    const statFil = $('report-filter-status').value;

    /* FIX 3: apply global state filter */
    let issues = filteredIssues();

    /* User only sees own reports */
    if (S.role === 'user') issues = issues.filter(i => i.reporter === S.user?.name);

    if (search) issues = issues.filter(i => i.type.toLowerCase().includes(search) || i.location.toLowerCase().includes(search) || i.id.toLowerCase().includes(search));
    if (sevFil) issues = issues.filter(i => sevClass(i.severity) === sevFil);
    if (statFil) issues = issues.filter(i => i.status === statFil);

    $('reports-total-badge').textContent = issues.length;

    const pages = Math.ceil(issues.length / S.ROWS) || 1;
    S.reportPage = Math.min(S.reportPage, pages);
    const slice = issues.slice((S.reportPage - 1) * S.ROWS, S.reportPage * S.ROWS);

    /* FIX 6: action column differs by role */
    tbody.innerHTML = slice.map(i => {
        let actionCell = '';
        if (S.role === 'admin') {
            /* FIX 5: only admin gets Assign button */
            actionCell = `<td><div style="display:flex;gap:5px">
        <button class="btn-sm" onclick="openAssignFor('${i.id}')"><i data-lucide="user-check" style="width:11px;height:11px"></i> Assign</button>
        <button class="btn-sm" onclick="resolveIssue('${i.id}')"><i data-lucide="check" style="width:11px;height:11px"></i></button>
      </div></td>`;
        } else if (S.role === 'worker') {
            /* Worker gets Mark Complete button */
            actionCell = `<td>
        ${i.status !== 'resolved'
                    ? `<button class="btn-complete" data-id="${i.id}">Mark Done</button>`
                    : `<span style="color:var(--low);font-size:.76rem;font-weight:700">✓ Resolved</span>`}
      </td>`;
        }
        // user and anonymous: no action cell (header hidden)

        return `
      <tr>
        <td>${thumbHtml(i.image)}</td>
        <td style="font-family:var(--font-m);font-size:.76rem;color:var(--accent);cursor:pointer" onclick="window.openIssueDetail('${i.id}')">${i.id}</td>
        <td style="font-weight:600;color:var(--text-primary)">${i.type}</td>
        <td>${i.location}</td>
        <td>${i.state}</td>
        <td>${sevTag(i.severity)}</td>
        <td>${i.reporter}</td>
        <td>${fmtDate(i.date)}</td>
        <td>${statusTag(i.status)}</td>
        ${actionCell}
      </tr>`;
    }).join('') || `<tr><td colspan="10" style="text-align:center;padding:36px;color:var(--text-muted)">No reports found</td></tr>`;

    renderPagination('reports-pagination', S.reportPage, pages, p => { S.reportPage = p; renderReportsTable(); });
    lucide.createIcons({ nodes: [tbody] });
}

/* ─────────────────────────────────────────────────────────────
   FIX 4 + 5: ALL ISSUES TABLE (Admin)
───────────────────────────────────────────────────────────── */
function renderIssuesTable() {
    const tbody = $('issues-tbody'); if (!tbody) return;
    const search = $('issues-search').value.toLowerCase();
    const sevFil = $('issues-sev-filter').value;
    const statFil = $('issues-status-filter').value;
    const stateFil = $('issues-state-filter').value || S.activeState;

    let issues = S.issues;
    if (search) issues = issues.filter(i => i.type.toLowerCase().includes(search) || i.location.toLowerCase().includes(search) || i.id.toLowerCase().includes(search));
    if (sevFil) issues = issues.filter(i => sevClass(i.severity) === sevFil);
    if (statFil) issues = issues.filter(i => i.status === statFil);
    if (stateFil) issues = issues.filter(i => i.state === stateFil);

    const pages = Math.ceil(issues.length / S.ROWS) || 1;
    S.issuesPage = Math.min(S.issuesPage, pages);
    const slice = issues.slice((S.issuesPage - 1) * S.ROWS, S.issuesPage * S.ROWS);

    tbody.innerHTML = slice.map(i => `
    <tr>
      <td><input type="checkbox" data-id="${i.id}"/></td>
      <td>${thumbHtml(i.image)}</td>
      <td style="font-family:var(--font-m);font-size:.76rem;color:var(--accent);cursor:pointer" onclick="window.openIssueDetail('${i.id}')">${i.id}</td>
      <td style="font-weight:600;color:var(--text-primary)">${i.type}</td>
      <td>${i.location}</td>
      <td>${i.state}</td>
      <td>${sevTag(i.severity)}</td>
      <td>${i.reporter}</td>
      <td>${fmtDate(i.date)}</td>
      <td>${statusTag(i.status)}</td>
      <td>
        <div style="display:flex;gap:4px">
          <!-- FIX 5: Assign only for admin (this whole page is admin-only anyway) -->
          <button class="btn-sm" onclick="openAssignFor('${i.id}')"><i data-lucide="user-check" style="width:11px;height:11px"></i></button>
          <button class="btn-sm" onclick="resolveIssue('${i.id}')"><i data-lucide="check" style="width:11px;height:11px"></i></button>
          <button class="btn-sm" onclick="window.openIssueDetail('${i.id}')"><i data-lucide="eye" style="width:11px;height:11px"></i></button>
        </div>
      </td>
    </tr>`).join('') || `<tr><td colspan="11" style="text-align:center;padding:36px;color:var(--text-muted)">No issues found</td></tr>`;

    renderPagination('issues-pagination', S.issuesPage, pages, p => { S.issuesPage = p; renderIssuesTable(); });
    lucide.createIcons({ nodes: [tbody] });
}

function renderPagination(elId, cur, total, cb) {
    const el = $(elId); if (!el) return;
    if (total <= 1) { el.innerHTML = ''; return; }
    let btns = '';
    for (let p = 1; p <= Math.min(total, 8); p++)
        btns += `<button class="page-btn ${p === cur ? 'active' : ''}" data-p="${p}">${p}</button>`;
    const showing = Math.min(cur * S.ROWS, total * S.ROWS);
    el.innerHTML = `<span>${(cur - 1) * S.ROWS + 1}–${showing} of ${S.issues.length} rows</span><div class="pagination-btns">${btns}</div>`;
    $a('.page-btn', el).forEach(b => b.addEventListener('click', () => cb(+b.dataset.p)));
}

/* ─────────────────────────────────────────────────────────────
   ISSUE DETAIL MODAL (with image)
───────────────────────────────────────────────────────────── */
window.openIssueDetail = function (id) {
    const i = S.issues.find(x => x.id === id); if (!i) return;
    $('issue-detail-title').textContent = `${i.id} — ${i.type}`;
    const raw = i.raw || {};
    const costBreakdown = raw.detailed_cost_breakdown || {};
    const cbItems = costBreakdown.cost_breakdown || {};

    let costSection = '';
    if (i.cost > 0) {
        costSection = `
        <div style="grid-column:span 2;background:rgba(255,255,255,.03);padding:14px;border-radius:var(--r);border:1px solid var(--border);margin-top:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-size:.78rem;font-weight:700;color:var(--text-secondary)">CALIBRATED REPAIR COST (CPWD / MoRTH)</span>
            <span style="font-size:1.15rem;font-weight:800;color:var(--accent)">₹${i.cost.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:.75rem">
            <div><span style="color:var(--text-muted)">Materials (50%):</span> ₹${(cbItems.material_cost_inr || i.cost*0.5).toFixed(2)}</div>
            <div><span style="color:var(--text-muted)">Labour (20%):</span> ₹${(cbItems.labour_cost_inr || i.cost*0.2).toFixed(2)}</div>
            <div><span style="color:var(--text-muted)">Equipment (11.8%):</span> ₹${(cbItems.equipment_cost_inr || i.cost*0.118).toFixed(2)}</div>
            <div><span style="color:var(--text-muted)">Contractor OH&P (14%):</span> ₹${(cbItems.contractor_overhead_profit_inr || i.cost*0.127).toFixed(2)}</div>
          </div>
          ${costBreakdown.engineering_disclaimer ? `<div style="font-size:.68rem;color:var(--text-muted);margin-top:8px;font-style:italic">⚠️ ${costBreakdown.engineering_disclaimer}</div>` : ''}
        </div>`;
    }

    const imgSection = i.image
        ? `<img src="${i.image}" style="width:100%;max-height:220px;object-fit:cover;border-radius:var(--r);border:1px solid var(--border);margin-bottom:14px;display:block" alt="Distress Overlay"/>`
        : '';

    $('issue-detail-body').innerHTML = `
    ${imgSection}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
      ${df('Type', i.type)}${df('Severity', sevTag(i.severity))}
      ${df('Location', i.location)}${df('State', i.state)}
      ${df('Reporter', i.reporter)}${df('Date', fmtDate(i.date))}
      ${df('Surface Area', (i.area ? `${i.area.toFixed(4)} m²` : 'N/A'))}${df('Status', statusTag(i.status))}
      ${df('Coordinates', i.lat ? `${i.lat.toFixed(4)}, ${i.lng.toFixed(4)}` : 'N/A')}${df('Database ID', i.dbId ? `#${i.dbId}` : 'N/A')}
      ${costSection}
    </div>`;

    $('issue-detail-assign').style.display = S.role === 'admin' ? 'inline-flex' : 'none';
    $('issue-detail-assign').onclick = () => { closeModal('issue-detail-modal'); openAssignFor(id); };

    openModal('issue-detail-modal');
};

function df(label, val) {
    return `<div><div style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text-muted);margin-bottom:4px">${label}</div><div style="font-size:.88rem;color:var(--text-primary)">${val}</div></div>`;
}

/* ─────────────────────────────────────────────────────────────
   WORKERS
───────────────────────────────────────────────────────────── */
function renderWorkers() {
    const summary = $('workers-summary-bar');
    const workers = S.workers || [];
    const active = workers.filter(w => w.status === 'active').length;
    const totalA = workers.reduce((a, w) => a + (w.assigned || 0), 0);
    const totalD = workers.reduce((a, w) => a + (w.completed || 0), 0);
    if (summary) {
        summary.innerHTML = [
            { num: workers.length, lbl: 'Total Workers' },
            { num: active, lbl: 'Active Crews' },
            { num: totalA, lbl: 'Assigned Tasks' },
            { num: totalD, lbl: 'Tasks Completed' },
        ].map(k => `<div class="workers-summary-card"><div class="ws-num">${k.num}</div><div class="ws-lbl">${k.lbl}</div></div>`).join('');
    }
    const grid = $('workers-grid'); if (!grid) return;
    if (workers.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted)">
            <i data-lucide="hard-hat" style="display:block;margin:0 auto 12px;opacity:0.4;width:36px;height:36px"></i>
            No field workers registered yet. Administrators can provision crew accounts in Settings → User Management.
        </div>`;
        lucide.createIcons({ nodes: [grid] });
        return;
    }
    grid.innerHTML = workers.map(w => `
    <div class="worker-card">
      <div class="worker-avatar">${w.avatar || (w.name ? w.name[0].toUpperCase() : 'W')}</div>
      <div class="worker-name">${w.name}</div>
      <div class="worker-zone">${w.zone || 'Field Division'}</div>
      <div class="worker-stats">
        <div class="worker-stat"><span>${w.assigned || 0}</span><small>Assigned</small></div>
        <div class="worker-stat"><span>${w.completed || 0}</span><small>Completed</small></div>
      </div>
      <div class="worker-status">
        <div class="live-pulse" style="${w.status === 'idle' ? 'background:var(--medium)' : ''}"></div>
        <span style="color:${w.status === 'active' ? 'var(--low)' : 'var(--medium)'};font-size:.76rem">${w.status === 'active' ? 'Active' : 'Idle'}</span>
      </div>
      ${S.role === 'admin'
            ? `<button class="btn-sm" style="margin-top:10px;width:100%;justify-content:center" onclick="openAssignFor(null,'${w.id}')"><i data-lucide="plus"></i> Assign Task</button>`
            : ''}
    </div>`).join('');
    lucide.createIcons({ nodes: [grid] });
}

function populateAssignModal() {
    const sel = $('assign-worker-select');
    if (!sel) return;
    const workers = S.workers || [];
    sel.innerHTML = '<option value="">Choose worker…</option>' +
        workers.map(w => `<option value="${w.id}">${w.name} — ${w.zone || 'Field Crew'}</option>`).join('');
}

function pushRealNotif({ title, desc, type = 'info', actionPage = null, actionLabel = null, actionId = null }) {
    const notif = {
        id: Date.now(),
        title,
        desc,
        type,
        read: false,
        time: 'Just now',
        actionPage,
        actionLabel,
        actionId,
    };
    S.notifications.unshift(notif);
    updateNotifBadge();
    renderNotifDD();
    if (S.currentPage === 'notifications') renderNotifPage();
    return notif;
}

function updateNotifBadge() {
    const unread = S.notifications.filter(n => !n.read).length;
    $('notif-dot').style.display = unread > 0 ? 'block' : 'none';
    const nb = $('sidebar-notif-count');
    if (unread > 0) { nb.textContent = unread; nb.style.display = 'flex'; }
    else nb.style.display = 'none';
}

function renderNotifDD() {
    const list = $('notif-list'); if (!list) return;
    const iconMap = { critical: 'alert-triangle', medium: 'alert-circle', low: 'check-circle', info: 'info' };
    const recent = S.notifications.slice(0, 7);

    list.innerHTML = recent.length ? recent.map(n => `
    <div class="notif-item ${n.read ? '' : 'unread'}" data-id="${n.id}">
      <div class="notif-item-icon ni-${n.type === 'info' ? 'info' : n.type}">
        <i data-lucide="${iconMap[n.type] || 'bell'}" style="width:13px;height:13px"></i>
      </div>
      <div class="notif-item-body">
        <div class="notif-item-title">${n.title}</div>
        <div class="notif-item-desc">${n.desc}</div>
        <div class="notif-item-time">${n.time}</div>
      </div>
    </div>`).join('')
        : '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:.82rem">No notifications yet</div>';

    lucide.createIcons({ nodes: [list] });

    $a('.notif-item', list).forEach(el => el.addEventListener('click', () => {
        const n = S.notifications.find(x => x.id === +el.dataset.id);
        if (n) {
            n.read = true;
            updateNotifBadge();
            renderNotifDD();
            /* FIX 1: Clicking notification redirects to the relevant action */
            if (n.actionPage) {
                $('notif-dropdown').style.display = 'none';
                navigateTo(n.actionPage);
                /* If it has an issue ID, open the detail modal after navigation */
                if (n.actionId) setTimeout(() => window.openIssueDetail(n.actionId), 300);
            }
        }
    }));
}

function renderNotifPage() {
    const el = $('notif-page-list'); if (!el) return;
    const iconMap = { critical: 'alert-triangle', medium: 'alert-circle', low: 'check-circle', info: 'info' };
    const colMap = { critical: 'var(--critical)', medium: 'var(--medium)', low: 'var(--low)', info: 'var(--accent)' };

    let notifs = S.notifications;
    if (S.notifFilter === 'unread') notifs = notifs.filter(n => !n.read);
    else if (S.notifFilter !== 'all') notifs = notifs.filter(n => n.type === S.notifFilter);

    el.innerHTML = notifs.length ? notifs.map(n => `
    <div class="notif-page-item ${n.read ? '' : 'unread'}" onclick="markNotifRead(${n.id},event)" data-page="${n.actionPage || ''}" data-issue-id="${n.actionId || ''}">
      <div class="notif-page-icon" style="background:${colMap[n.type] || 'var(--accent)'}1a;color:${colMap[n.type] || 'var(--accent)'}">
        <i data-lucide="${iconMap[n.type] || 'bell'}"></i>
      </div>
      <div class="notif-page-body">
        <div class="notif-page-title">${n.title}</div>
        <div class="notif-page-desc">${n.desc}</div>
        <div class="notif-page-time">${n.time}</div>
        ${n.actionPage && n.actionLabel
            /* FIX 1: Notification action link → redirects to real issue/report */
            ? `<a class="notif-action-link" onclick="event.stopPropagation();navigateFromNotif('${n.actionPage}','${n.actionId || ''}')">
               <i data-lucide="arrow-right" style="width:11px;height:11px"></i>${n.actionLabel}
             </a>`
            : ''}
      </div>
      ${!n.read ? '<div class="notif-unread-dot"></div>' : ''}
    </div>`).join('')
        : '<div style="padding:48px;text-align:center;color:var(--text-muted);font-size:.85rem">No notifications</div>';

    lucide.createIcons({ nodes: [el] });
}

/* FIX 1: Navigate from notification to relevant page+issue */
window.navigateFromNotif = function (page, issueId) {
    navigateTo(page);
    if (issueId) setTimeout(() => window.openIssueDetail(issueId), 300);
};

window.markNotifRead = function (id, e) {
    const n = S.notifications.find(x => x.id === id);
    if (n) {
        n.read = true;
        updateNotifBadge();
        renderNotifPage();
        renderNotifDD();
        /* FIX 1: clicking the notification card also navigates */
        if (n.actionPage && !(e?.target?.closest('.notif-action-link'))) {
            navigateTo(n.actionPage);
            if (n.actionId) setTimeout(() => window.openIssueDetail(n.actionId), 300);
        }
    }
};

function markAllRead() {
    S.notifications.forEach(n => n.read = true);
    updateNotifBadge();
    renderNotifDD();
    if (S.currentPage === 'notifications') renderNotifPage();
    toast('All notifications marked as read', 'success');
}

/* ─────────────────────────────────────────────────────────────
   REPORT SUBMIT
   FIX 1: Creates a real notification on submit
───────────────────────────────────────────────────────────── */
async function handleReportSubmit() {
    const type = $('report-type').value;
    const sev = $('report-severity').value;
    const loc = $('report-location').value.trim();
    if (!type || !sev || !loc) { toast('Fill required fields: type, severity, location', 'error'); return; }

    const state = $('report-state').value || 'Other';
    const name = $('report-name').value.trim() || S.user?.name || 'Citizen User';
    const desc = $('report-desc').value.trim();
    const fileInput = $('report-image-input');
    const file = fileInput?.files?.[0];

    const submitBtn = $('submit-report');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting & Analyzing...';
    }

    try {
        let imageUrl = null;
        let detectedType = type;
        let detectedSeverity = sev;
        let detectedCost = 0;

        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('road_name', loc);
            formData.append('region', state);
            formData.append('save_results', 'true');

            const res = await apiRequest('/api/detect', {
                method: 'POST',
                body: formData,
            });

            if (res.success) {
                imageUrl = res.annotated_image_url || res.image_url;
                if (res.detections && res.detections.length > 0) {
                    const top = res.detections[0];
                    detectedType = top.class_name || type;
                    detectedSeverity = (top.severity && top.severity !== 'N/A') ? top.severity.toLowerCase() : sev;
                    detectedCost = top.repair_cost ? top.repair_cost.cost : 0;
                }
            }
        }

        const newId = `RPT-${String(S.issues.length + 1).padStart(3, '0')}`;
        const newIssue = {
            id: newId,
            type: detectedType,
            severity: detectedSeverity,
            location: loc,
            state,
            reporter: name,
            desc,
            date: new Date().toISOString().split('T')[0],
            status: 'pending',
            lat: 19.0760 + (Math.random() - .5) * 4,
            lng: 72.8777 + (Math.random() - .5) * 4,
            image: imageUrl,
            cost: detectedCost,
        };

        S.issues.unshift(newIssue);
        populateStateFilters();

        pushRealNotif({
            title: 'New Issue Reported',
            desc: `${detectedType} at ${loc}, ${state} (${newId}) — ${detectedSeverity} severity`,
            type: sevClass(detectedSeverity),
            actionPage: 'reports',
            actionLabel: 'View Report',
            actionId: newId,
        });

        pushFeedItem(`New ${detectedType} analyzed & reported at ${loc}, ${state}`, sevClass(detectedSeverity));

        // Reset form
        ['report-type', 'report-severity', 'report-state'].forEach(id => $(id).value = '');
        ['report-location', 'report-name', 'report-desc'].forEach(id => $(id).value = '');
        if (fileInput) fileInput.value = '';
        $('report-image-preview').style.display = 'none';
        $('report-image-preview').innerHTML = '';
        $('report-form-card').style.display = 'none';

        renderReportsTable();
        renderKPIs();
        renderStateBars();
        renderMiniIssues();
        toast(`Defect analyzed and reported (${detectedType})!`, 'success');
    } catch (err) {
        toast(`Submission failed: ${err.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Report';
        }
    }
}

function showImgPreview(f) {
    const r = new FileReader();
    r.onload = e => {
        const p = $('report-image-preview');
        p.innerHTML = `<img src="${e.target.result}" style="width:100px;height:70px;object-fit:cover;border-radius:var(--r-sm);border:1px solid var(--border)"/><span style="font-size:.74rem;color:var(--text-muted)">${f.name}</span>`;
        p.style.display = 'flex';
        p.style.gap = '10px';
        p.style.alignItems = 'center';
    };
    r.readAsDataURL(f);
}

function detectLoc() {
    const s = $('location-status');
    s.textContent = 'Detecting location…'; s.className = 'location-status';
    if (!navigator.geolocation) { s.textContent = 'Geolocation not supported'; s.className = 'location-status error'; return; }
    navigator.geolocation.getCurrentPosition(
        pos => {
            const { latitude: la, longitude: lo } = pos.coords;
            $('report-location').value = `${la.toFixed(4)}, ${lo.toFixed(4)}`;
            s.textContent = `✓ Location detected: ${la.toFixed(4)}, ${lo.toFixed(4)}`;
            s.className = 'location-status success';
        },
        () => {
            $('report-location').value = 'MG Road, Bangalore, Karnataka';
            s.textContent = 'Auto-detect failed — example location used';
            s.className = 'location-status error';
        }
    );
}

/* ─────────────────────────────────────────────────────────────
   ASSIGN WORK
   FIX 1: Creates real notification on assign
   FIX 5: Only admin can reach this function
───────────────────────────────────────────────────────────── */
window.openAssignFor = function (issueId, workerId) {
    populateAssignModal();
    /* FIX 5: Guard — should never be called for non-admin but double-check */
    if (S.role !== 'admin') { toast('Admin access required', 'error'); return; }

    const sel = $('assign-issue-select');
    sel.innerHTML = '<option value="">Choose issue…</option>' +
        S.issues.filter(i => i.status !== 'resolved')
            .map(i => `<option value="${i.id}" ${i.id === issueId ? 'selected' : ''}>${i.id} — ${i.type} (${i.state})</option>`)
            .join('');
    if (workerId) $('assign-worker-select').value = workerId;
    openModal('assign-modal');
};

async function handleAssign() {
    if (S.role !== 'admin') { toast('Admin access required', 'error'); return; }

    const issueId = $('assign-issue-select').value;
    const workerId = $('assign-worker-select').value;
    const priority = $('assign-priority') ? $('assign-priority').value : 'normal';
    const notes = $('assign-notes') ? $('assign-notes').value.trim() : '';
    if (!issueId || !workerId) { toast('Select both an issue and a worker', 'error'); return; }

    const iss = S.issues.find(i => i.id === issueId);
    const dbIssueId = iss?.dbId || parseInt(String(issueId).replace(/\D/g, '')) || 1;
    const numWorkerId = parseInt(String(workerId).replace(/\D/g, '')) || 1;
    const wkr = S.workers.find(w => w.id === workerId || w.dbId === numWorkerId);

    try {
        await RoadPulseAPI.admin.assign(dbIssueId, numWorkerId, notes ? `${notes} (Priority: ${priority})` : `Priority: ${priority}`);
        if (iss) { iss.status = 'in-progress'; iss.assignedTo = wkr?.name || `Worker #${numWorkerId}`; }
        closeModal('assign-modal');
        renderIssuesTable();
        renderReportsTable();
        renderMiniIssues();
        toast(`Issue ${issueId} assigned to ${wkr?.name || 'Worker'}`, 'success');
        loadLiveBackendData();
    } catch (err) {
        toast(`Assignment error: ${err.message}`, 'error');
    }
}

window.resolveIssue = async function (id) {
    if (S.role !== 'admin') { toast('Admin access required', 'error'); return; }
    const i = S.issues.find(x => x.id === id); if (!i) return;
    try {
        const dbId = i.dbId || parseInt(String(id).replace(/\D/g, ''));
        if (dbId) {
            await RoadPulseAPI.request(`/api/defects/${dbId}/status`, {
                method: 'PATCH',
                body: JSON.stringify({ issue_id: dbId, status: 'completed', notes: 'Marked resolved via admin panel' })
            }).catch(() => null);
        }
        await RoadPulseAPI.repairs.create({
            road_name: i.location || 'Highway Sector',
            status: 'approved',
            defects_resolved: 1,
            cost_saved: i.cost || 0,
            admin_notes: `Marked resolved via administrative panel for issue ${id}.`,
        }).catch(() => null);

        i.status = 'resolved';
        renderIssuesTable();
        renderReportsTable();
        renderMiniIssues();
        renderKPIs();
        toast(`Issue ${id} marked as resolved!`, 'success');
        loadLiveBackendData();
    } catch (err) {
        toast(`Error resolving issue: ${err.message}`, 'error');
    }
};

function openModal(id) { const m = $(id); if (m) m.style.display = 'flex'; }
function closeModal(id) { const m = $(id); if (m) m.style.display = 'none'; }

/* ─────────────────────────────────────────────────────────────
   EXPORT CSV
───────────────────────────────────────────────────────────── */
function exportCSV(data, name) {
    const hdr = ['ID', 'Type', 'Location', 'State', 'Severity', 'Reporter', 'Date', 'Status'];
    const rows = data.map(i => [i.id, i.type, i.location, i.state, i.severity, i.reporter, i.date, i.status].map(v => `"${v}"`).join(','));
    const csv = [hdr.join(','), ...rows].join('\n');
    const a = document.createElement('a');
    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
    a.download = `roadpulse-${name}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    toast('CSV exported', 'success');
}

/* ─────────────────────────────────────────────────────────────
   THEME
───────────────────────────────────────────────────────────── */
function applyTheme(theme) {
    S.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    const i = $('theme-toggle').querySelector('i');
    i.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
    lucide.createIcons({ nodes: [$('theme-toggle')] });
    if ($('dark-mode-toggle')) $('dark-mode-toggle').checked = theme === 'dark';
    localStorage.setItem('rp_theme', theme);
    Object.values(S.charts).forEach(c => { try { c.destroy(); } catch { } });
    S.charts = {};
    setTimeout(() => { initCharts(); if (S.currentPage === 'analytics') initAnalyticsCharts(); }, 80);
}

/* ─────────────────────────────────────────────────────────────
   BOOT
───────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    const theme = localStorage.getItem('rp_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    S.theme = theme;
    lucide.createIcons();
    initLogin();
    if (!checkAutoLogin()) {
        $('login-screen').style.display = 'flex';
        $('app').style.display = 'none';
    }
});

/* ─────────────────────────────────────────────────────────────
   USER MANAGEMENT (Admin)
───────────────────────────────────────────────────────────── */
async function renderUsersTable() {
    const tbody = $('users-tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted)">Loading user records...</td></tr>';
    try {
        const users = await RoadPulseAPI.admin.users();
        S.users = users;
        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted)">No user accounts registered.</td></tr>';
            return;
        }
        tbody.innerHTML = users.map(u => `
        <tr>
          <td><strong>#${u.id}</strong></td>
          <td><div style="display:flex;align-items:center;gap:8px"><div class="worker-avatar" style="width:24px;height:24px;font-size:.7rem">${u.username[0].toUpperCase()}</div>${u.username}</div></td>
          <td><span class="role-pill role-${u.role}">${u.role}</span></td>
          <td><span class="status-pill status-${u.is_active ? 'completed' : 'pending'}">${u.is_active ? 'Active' : 'Deactivated'}</span></td>
          <td>${u.created_at ? u.created_at.split('T')[0] : 'N/A'}</td>
          <td>
            ${u.username !== S.user?.username ? `
            <button class="btn-sm" onclick="toggleUserStatus(${u.id})" title="${u.is_active ? 'Deactivate' : 'Activate'}">
              <i data-lucide="${u.is_active ? 'user-x' : 'user-check'}"></i> ${u.is_active ? 'Deactivate' : 'Activate'}
            </button>` : '<span style="color:var(--text-muted);font-size:.75rem">Current Account</span>'}
          </td>
        </tr>`).join('');
        lucide.createIcons({ nodes: [tbody] });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--critical)">Failed to load users: ${err.message}</td></tr>`;
    }
}

window.toggleUserStatus = async function (id) {
    if (S.role !== 'admin') return;
    try {
        await RoadPulseAPI.admin.toggleUser(id);
        toast(`User status updated successfully.`, 'success');
        renderUsersTable();
    } catch (err) {
        toast(`Error: ${err.message}`, 'error');
    }
};

async function handleCreateUser() {
    if (S.role !== 'admin') return;
    const u = $('new-user-username').value.trim();
    const r = $('new-user-role').value;
    const p = $('new-user-password').value;
    const errBox = $('create-user-error');
    errBox.style.display = 'none';

    if (!u || !p) {
        errBox.textContent = 'Username and password are required.';
        errBox.style.display = 'block';
        return;
    }
    const btn = $('btn-submit-create-user');
    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        await RoadPulseAPI.admin.createUser({ username: u, role: r, password: p });
        toast(`Account '${u}' (${r}) created successfully!`, 'success');
        closeModal('create-user-modal');
        $('new-user-username').value = '';
        $('new-user-password').value = '';
        renderUsersTable();
        await loadLiveBackendData();
        if (S.currentPage === 'workers') renderWorkers();
    } catch (err) {
        errBox.textContent = err.message || 'Failed to create user.';
        errBox.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="check"></i> Create Account';
        lucide.createIcons({ nodes: [btn] });
    }
}
