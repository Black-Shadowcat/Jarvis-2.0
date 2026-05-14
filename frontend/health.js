// ═══════════════════════════════════════════════════════════════
// J.A.R.V.I.S. Health Monitor — Real-Time Supervisor Dashboard
// ═══════════════════════════════════════════════════════════════

// ── Mock Data (will be replaced with live API calls) ──
const mockData = {
    status: 'operational',
    healthScore: 100,
    uptime: '12D 04:32:17',
    startTime: new Date(Date.now() - 12 * 24 * 60 * 60 * 1000),
    lastCheck: new Date(Date.now() - 30 * 1000),
    nextCheck: new Date(Date.now() + 30 * 1000),
    services: [
        { name: 'SERVER', status: 'healthy', pid: 3916 },
        { name: 'WEBSOCKET', status: 'healthy', pid: 0 },
        { name: 'SPEECH INPUT', status: 'healthy', pid: 4244 },
        { name: 'WAKE MONITOR', status: 'healthy', pid: 814 },
        { name: 'CHROME FRONTEND', status: 'healthy', pid: 0 },
        { name: 'HOME ASSISTANT', status: 'healthy', pid: 0 },
    ],
    metrics: {
        cpu: 12,
        memory: 284,
        disk: 18,
        networkIn: 1.2,
        networkOut: 2.4,
    },
    recoveries: 0,
    logs: [
        { time: '13:37:04', level: 'OK', message: 'All systems healthy' },
        { time: '13:37:04', level: 'OK', message: 'Server HTTP response: 200' },
        { time: '13:37:04', level: 'OK', message: 'WebSocket handshake OK' },
        { time: '13:37:04', level: 'OK', message: 'speech_input.py running' },
        { time: '13:37:04', level: 'OK', message: 'wake-monitor.py running' },
        { time: '13:37:04', level: 'OK', message: 'Chrome process running' },
        { time: '13:37:03', level: 'OK', message: 'Home Assistant reachable' },
        { time: '13:31:47', level: 'OK', message: 'All systems healthy' },
    ],
};

// ── Initialize ──
document.addEventListener('DOMContentLoaded', () => {
    console.log('[health] DOM Content Loaded');
    init();
    setInterval(updateData, 10000); // Update every 10 seconds
    setInterval(updateDaytime, 1000); // Update daytime every second
    updateDaytime();
});

async function init() {
    console.log('[health] Initializing...');
    try {
        updateSystemWatch();
        updateHealthScore();
        updateMetrics();
        updateLogs();
        drawArchitecture();
        updateFooter();
        console.log('[health] Init complete');
    } catch (e) {
        console.error('[health] Init error:', e);
    }
}

// ── Fetch real data from API (will be implemented) ──
async function fetchSupervisorStatus() {
    try {
        const response = await fetch('/api/supervisor/status');
        if (!response.ok) return mockData;
        return await response.json();
    } catch (e) {
        console.log('Using mock data (API not available)');
        return mockData;
    }
}

async function fetchSupervisorLog() {
    try {
        const response = await fetch('/api/supervisor/log?tail=50');
        if (!response.ok) return mockData.logs;
        return await response.json();
    } catch (e) {
        return mockData.logs;
    }
}

// ── Update System Watch ──
function updateSystemWatch() {
    const container = document.getElementById('system-watch-items');
    container.innerHTML = '';

    mockData.services.forEach(service => {
        const item = document.createElement('div');
        item.className = 'watch-item';

        const dotClass = service.status === 'healthy' ? 'watch-dot' :
                        service.status === 'degraded' ? 'watch-dot warning' :
                        'watch-dot error';

        item.innerHTML = `
            <span class="${dotClass}"></span>
            <span class="watch-label">${service.name}</span>
            <span class="watch-status">${service.status.toUpperCase()}</span>
        `;
        container.appendChild(item);
    });
}

// ── Update Health Score Gauge ──
function updateHealthScore() {
    const score = mockData.healthScore;
    const ring = document.getElementById('gauge-ring');
    const scoreEl = document.getElementById('health-score');

    // Calculate stroke-dashoffset (377 is full circle circumference)
    const offset = 377 - (score / 100) * 377;
    ring.style.strokeDashoffset = offset;
    scoreEl.textContent = score + '%';

    // Update main status
    let status = 'OPERATIONAL';
    let bannerClass = 'operational';
    if (score < 50) {
        status = 'CRITICAL';
        bannerClass = 'critical';
    } else if (score < 80) {
        status = 'DEGRADED';
        bannerClass = 'degraded';
    }

    document.getElementById('main-status').textContent = status;
    document.getElementById('status-banner').className = 'status-banner ' + bannerClass;
    document.getElementById('supervisor-status').textContent = 'ACTIVE';

    // Update info (daytime is updated separately in updateDaytime())
    // Version wird dynamisch geladen
    fetch('/api/version').then(r => r.json()).then(v => {
        document.getElementById('info-version').textContent = `v${v.version}`;
    }).catch(() => {
        document.getElementById('info-version').textContent = 'v?.?.?';
    });
    document.getElementById('info-last-check').textContent = formatTime(mockData.lastCheck);
    document.getElementById('info-next-check').textContent = formatTime(mockData.nextCheck);
}

// ── Update Metrics ──
function updateMetrics() {
    const container = document.getElementById('metrics-container');
    container.innerHTML = '';

    const metrics = [
        { label: 'CPU USAGE', value: mockData.metrics.cpu, unit: '%' },
        { label: 'MEMORY', value: mockData.metrics.memory, unit: 'MB' },
        { label: 'DISK', value: mockData.metrics.disk, unit: '%' },
        { label: 'NETWORK (IN)', value: mockData.metrics.networkIn, unit: 'kB/s' },
        { label: 'NETWORK (OUT)', value: mockData.metrics.networkOut, unit: 'kB/s' },
    ];

    metrics.forEach(metric => {
        const box = document.createElement('div');
        box.style.cssText = `
            border: 1px solid rgba(0,255,136,0.1);
            border-radius: 2px;
            padding: 8px;
            background: rgba(0,255,136,0.02);
        `;
        box.innerHTML = `
            <div style="font-size: 10px; color: #888; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;">${metric.label}</div>
            <div style="font-size: 16px; color: #00ff88; font-weight: bold;">${metric.value}<span style="font-size: 12px;">${metric.unit}</span></div>
        `;
        container.appendChild(box);
    });
}

// ── Update Logs ──
function updateLogs() {
    const container = document.getElementById('log-container');
    container.innerHTML = '';

    mockData.logs.forEach(log => {
        const entry = document.createElement('div');
        const levelClass = log.level === 'ERROR' ? 'error' : log.level === 'WARN' ? 'warning' : '';
        entry.className = 'log-entry ' + levelClass;
        entry.innerHTML = `
            <span class="log-timestamp">${log.time}</span>
            <span class="log-status">${log.level}</span>
            <span class="log-message">${log.message}</span>
        `;
        container.appendChild(entry);
    });

    document.getElementById('recovery-count').textContent = mockData.recoveries;
    document.getElementById('last-recovery').textContent = mockData.recoveries > 0 ? '5m ago' : 'NONE';
}

// ── Draw Architecture Diagram ──
function drawArchitecture() {
    const svg = document.getElementById('architecture-svg');
    if (!svg) {
        console.error('[health] architecture-svg not found');
        return;
    }

    // Clear existing content (except grid and defs)
    const oldConnections = svg.querySelector('#connections');
    const oldNodes = svg.querySelector('#nodes');
    if (oldConnections) oldConnections.remove();
    if (oldNodes) oldNodes.remove();

    // Create groups
    const connectionsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    connectionsGroup.setAttribute('id', 'connections');
    svg.appendChild(connectionsGroup);

    const nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    nodesGroup.setAttribute('id', 'nodes');
    svg.appendChild(nodesGroup);

    const services = [
        { name: 'SERVER', x: 300, y: 80, color: '#00ff88' },
        { name: 'SPEECH\nINPUT', x: 100, y: 200, color: '#00ff88' },
        { name: 'WEBSOCKET', x: 500, y: 200, color: '#00ff88' },
        { name: 'WAKE\nMONITOR', x: 100, y: 320, color: '#00ff88' },
        { name: 'CHROME\nFRONTEND', x: 500, y: 320, color: '#00ff88' },
        { name: 'HOME\nASSISTANT', x: 500, y: 140, color: '#00ff88' },
    ];

    const supervisor = { name: 'SUPERVISOR', x: 300, y: 200, color: '#00ff88' };

    // Draw connections (lines from supervisor to services)
    services.forEach(service => {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', supervisor.x);
        line.setAttribute('y1', supervisor.y);
        line.setAttribute('x2', service.x);
        line.setAttribute('y2', service.y);
        line.setAttribute('stroke', 'rgba(0,255,136,0.3)');
        line.setAttribute('stroke-width', '1.5');
        line.setAttribute('stroke-dasharray', '4,4');
        connectionsGroup.appendChild(line);
    });

    // Draw supervisor (center)
    drawNode(nodesGroup, supervisor);

    // Draw service nodes
    services.forEach(service => {
        drawNode(nodesGroup, service);
    });

    console.log('[health] Architecture drawn');
}

function drawNode(group, node) {
    // Box
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', node.x - 50);
    rect.setAttribute('y', node.y - 20);
    rect.setAttribute('width', '100');
    rect.setAttribute('height', '40');
    rect.setAttribute('fill', 'rgba(10,14,39,0.8)');
    rect.setAttribute('stroke', node.color);
    rect.setAttribute('stroke-width', '1.5');
    rect.setAttribute('rx', '4');
    group.appendChild(rect);

    // Status dot
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', node.x + 45);
    circle.setAttribute('cy', node.y - 20);
    circle.setAttribute('r', '3');
    circle.setAttribute('fill', node.color);
    circle.setAttribute('filter', 'url(#glow)');
    group.appendChild(circle);

    // Text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', node.x);
    text.setAttribute('y', node.y + 3);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', node.color);
    text.setAttribute('font-size', '11');
    text.setAttribute('font-family', 'monospace');
    text.setAttribute('font-weight', 'bold');
    text.setAttribute('letter-spacing', '0.5');
    text.textContent = node.name;
    group.appendChild(text);
}

// ── Update Data (Polling) ──
async function updateData() {
    const data = await fetchSupervisorStatus();
    mockData.healthScore = data.healthScore || 100;
    mockData.uptime = data.uptime || mockData.uptime;
    mockData.services = data.services || mockData.services;
    mockData.metrics = data.metrics || mockData.metrics;

    updateSystemWatch();
    updateHealthScore();
    updateMetrics();
    updateLogs();
}

// ── Update Footer ──
function updateFooter() {
    const start = mockData.startTime;
    const dateStr = start.toISOString().split('T')[0];
    document.getElementById('footer-time').textContent = 'MONITORING SINCE: ' + dateStr;
}

// ── Helper: Format Time ──
function formatTime(date) {
    const h = String(date.getHours()).padStart(2, '0');
    const m = String(date.getMinutes()).padStart(2, '0');
    const s = String(date.getSeconds()).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

function updateDaytime() {
    const now = new Date();
    document.getElementById('main-uptime').textContent = formatTime(now);
}

// ── System Commands ──
function forceHealthCheck() {
    alert('Force Health Check — Supervisor will re-check all services immediately');
    // TODO: POST /api/supervisor/force-check
}

function restartServer() {
    const confirmed = confirm('Restart server.py? This may briefly interrupt chat.');
    if (confirmed) {
        alert('Restarting server via launchctl kickstart…');
        // TODO: POST /api/supervisor/restart?service=server
    }
}

function restartAllServices() {
    const confirmed = confirm('Restart ALL Jarvis services? System will be offline ~10 seconds.');
    if (confirmed) {
        alert('Restarting all services…');
        // TODO: POST /api/supervisor/restart?all=true
    }
}

function viewLogFile() {
    alert('Opening supervisor.log…');
    window.open('/api/supervisor/log?view=full', '_blank');
}

// ── Add Glow Filter to SVG if not present ──
window.addEventListener('load', () => {
    const svg = document.getElementById('architecture-svg');
    if (!svg) return;

    if (!svg.querySelector('defs')) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        svg.insertBefore(defs, svg.firstChild);
    }

    const defs = svg.querySelector('defs');
    if (!defs.querySelector('#glow')) {
        const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
        filter.setAttribute('id', 'glow');
        const feGaussian = document.createElementNS('http://www.w3.org/2000/svg', 'feGaussianBlur');
        feGaussian.setAttribute('stdDeviation', '2');
        feGaussian.setAttribute('result', 'coloredBlur');
        const feMerge = document.createElementNS('http://www.w3.org/2000/svg', 'feMerge');
        const feMergeNode1 = document.createElementNS('http://www.w3.org/2000/svg', 'feMergeNode');
        feMergeNode1.setAttribute('in', 'coloredBlur');
        const feMergeNode2 = document.createElementNS('http://www.w3.org/2000/svg', 'feMergeNode');
        feMergeNode2.setAttribute('in', 'SourceGraphic');
        feMerge.appendChild(feMergeNode1);
        feMerge.appendChild(feMergeNode2);
        filter.appendChild(feGaussian);
        filter.appendChild(feMerge);
        defs.appendChild(filter);
    }
});
