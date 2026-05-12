// Load config on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    loadVoiceLibrary();
    fetch('/api/version').then(r => r.json()).then(v => {
        const el = document.getElementById('app-version');
        if (el) el.textContent = `v${v.version}`;
    }).catch(() => {});
});

let currentConfig = {};
let voiceDb = { active_voice_id: '', voices: [] };

async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        const data = await resp.json();
        currentConfig = data;

        // Fill form fields
        document.getElementById('anthropicKey').value = data.anthropic_api_key || '';
        document.getElementById('elevenlabsKey').value = data.elevenlabs_api_key || '';
        document.getElementById('userName').value = data.user_name || '';
        document.getElementById('userAddress').value = data.user_address || '';
        document.getElementById('city').value = data.city || '';
        document.getElementById('timezone').value = data.timezone || 'Europe/Berlin';
        document.getElementById('language').value = data.language || 'de';
        document.getElementById('lat').value = data.lat || '';
        document.getElementById('lon').value = data.lon || '';
        document.getElementById('kachelmannKey').value = data.kachelmann_api_key || '';
        document.getElementById('workspacePath').value = data.workspace_path || '';
        document.getElementById('obsidianPath').value = data.obsidian_inbox_path || '';
        document.getElementById('obsidianArchivePath').value = data.obsidian_archive_path || '';
        document.getElementById('haUrl').value = data.ha_url || '';
        document.getElementById('haToken').value = data.ha_token || '';
        document.getElementById('browserUrl').value = data.browser_url || '';
        document.getElementById('spotifyTrack').value = data.spotify_track || '';

        // Toggle HA
        if (data.ha_enabled) {
            document.getElementById('haToggle').classList.add('on');
            document.getElementById('haFields').style.opacity = '1';
            document.getElementById('haFields').style.pointerEvents = 'auto';
        }

        // Toggle wake greeting
        if (data.wake_greeting_enabled !== false) {
            document.getElementById('wakeGreetingToggle').classList.add('on');
        }

        // Load available apps and populate dropdowns
        await loadAvailableApps();

        // Load selected programs
        loadPrograms(data.programs || []);

    } catch (e) {
        console.error('Config load failed:', e);
    }
}

// ── Voice Library ─────────────────────────────────────────────────────────

async function loadVoiceLibrary() {
    try {
        const resp = await fetch('/api/voices');
        voiceDb = await resp.json();
        renderActiveVoice();
    } catch(e) {
        const d = document.getElementById('activeVoiceDisplay');
        if (d) d.textContent = 'Fehler beim Laden';
    }
}

function renderActiveVoice() {
    const display = document.getElementById('activeVoiceDisplay');
    if (!display) return;
    const active = voiceDb.voices?.find(v => v.voice_id === voiceDb.active_voice_id);
    display.textContent = active ? `● ${active.name}` : (voiceDb.active_voice_id || '—');
}

function renderVoiceList() {
    const list = document.getElementById('voiceList');
    if (!list) return;
    if (!voiceDb.voices?.length) {
        list.innerHTML = '<div style="color:#555;font-size:0.85rem;text-align:center;padding:16px;">Noch keine Stimmen gespeichert.</div>';
        return;
    }
    list.innerHTML = voiceDb.voices.map((v, i) => {
        const isActive = v.voice_id === voiceDb.active_voice_id;
        return `<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:6px;background:${isActive ? 'rgba(76,191,126,0.08)' : 'rgba(42,158,226,0.04)'};border:1px solid ${isActive ? 'rgba(76,191,126,0.3)' : 'rgba(42,158,226,0.1)'};">
            <div style="flex:1;min-width:0;">
                <div style="font-size:0.85rem;font-weight:500;${isActive ? 'color:#4cbf7e' : ''}">${isActive ? '● ' : '○ '}${v.name}</div>
                <div style="font-size:0.7rem;color:#555;font-family:monospace;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${v.voice_id}</div>
            </div>
            <button class="field-row-action eye-btn" onclick="playVoicePreview('${v.voice_id}')" title="Testen">▶</button>
            ${isActive
                ? `<button class="field-row-action" style="border-color:#4cbf7e;color:#4cbf7e;cursor:default;opacity:0.6;" disabled>Aktiv</button>`
                : `<button class="field-row-action" onclick="activateVoice('${v.voice_id}')">Aktivieren</button>`}
            <button class="field-row-action eye-btn" onclick="removeVoice(${i})" title="Löschen" style="color:#e05252;">✗</button>
        </div>`;
    }).join('');
}

function openVoiceModal() {
    renderVoiceList();
    document.getElementById('voiceModal').classList.add('show');
}

function closeVoiceModal() {
    document.getElementById('voiceModal').classList.remove('show');
    document.getElementById('newVoiceName').value = '';
    document.getElementById('newVoiceId').value   = '';
}

async function activateVoice(voiceId) {
    try {
        const resp = await fetch('/api/voices/activate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({voice_id: voiceId})
        });
        const data = await resp.json();
        if (data.success) {
            voiceDb.active_voice_id = voiceId;
            renderActiveVoice();
            renderVoiceList();
            showToast('Stimme aktiviert', 'success');
        } else {
            showToast('Fehler: ' + (data.error || ''), 'error');
        }
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
    }
}

async function addVoice() {
    const name    = document.getElementById('newVoiceName').value.trim();
    const voiceId = document.getElementById('newVoiceId').value.trim();
    if (!name || !voiceId) { showToast('Name und Voice ID erforderlich', 'error'); return; }
    if (voiceDb.voices.some(v => v.voice_id === voiceId)) { showToast('Voice ID bereits vorhanden', 'error'); return; }
    voiceDb.voices.push({name, voice_id: voiceId});
    await saveVoiceDb();
    document.getElementById('newVoiceName').value = '';
    document.getElementById('newVoiceId').value   = '';
    renderVoiceList();
    showToast(`"${name}" hinzugefügt`, 'success');
}

async function removeVoice(index) {
    if (voiceDb.voices[index]?.voice_id === voiceDb.active_voice_id) {
        showToast('Aktive Stimme kann nicht gelöscht werden', 'error');
        return;
    }
    voiceDb.voices.splice(index, 1);
    await saveVoiceDb();
    renderVoiceList();
    showToast('Stimme entfernt', 'success');
}

async function saveVoiceDb() {
    await fetch('/api/voices/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(voiceDb)
    });
}

async function playVoicePreview(voiceId) {
    try {
        const resp = await fetch('/api/preview_voice', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({voice_id: voiceId})
        });
        const data = await resp.json();
        if (data.audio) {
            new Audio('data:audio/mpeg;base64,' + data.audio).play();
        } else {
            showToast('Vorschau fehlgeschlagen: ' + (data.error || 'Kein Audio'), 'error');
        }
    } catch(e) {
        showToast('Vorschau fehlgeschlagen', 'error');
    }
}

async function previewActiveVoice() {
    if (!voiceDb.active_voice_id) { showToast('Keine aktive Stimme', 'error'); return; }
    await playVoicePreview(voiceDb.active_voice_id);
}

async function testNewVoice() {
    const voiceId = document.getElementById('newVoiceId').value.trim();
    if (!voiceId) { showToast('Voice ID eingeben', 'error'); return; }
    const btn = document.getElementById('testNewVoiceBtn');
    btn.textContent = '…'; btn.disabled = true;
    await playVoicePreview(voiceId);
    btn.textContent = '▶ Testen'; btn.disabled = false;
}

async function loadVoices(apiKey) {
    const key = apiKey || document.getElementById('elevenlabsKey')?.value.trim() || '';
    try {
        const url = key ? `/api/elevenlabs_voices?key=${encodeURIComponent(key)}` : '/api/elevenlabs_voices';
        return await (await fetch(url)).json();
    } catch(e) { return {voices: [], error: e.message}; }
}

async function testKey(type) {
    const btn = document.getElementById(type + 'Btn');
    const input = document.getElementById(type + 'Key');
    const key = input.value.trim();

    if (!key) {
        showToast('Kein API Key eingegeben', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = '…';

    try {
        const resp = await fetch('/api/test_key', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({type, key})
        });

        const data = await resp.json();
        if (data.success) {
            btn.classList.add('ok');
            btn.textContent = '✓ OK';
            showToast(type + ' API Key funktioniert', 'success');
            setTimeout(() => {
                btn.classList.remove('ok');
                btn.textContent = 'Testen';
            }, 3000);
        } else {
            btn.classList.add('err');
            btn.textContent = '✗ Fehler';
            showToast('API Key ungültig: ' + (data.error || 'Unbekannter Fehler'), 'error');
            setTimeout(() => {
                btn.classList.remove('err');
                btn.textContent = 'Testen';
            }, 3000);
        }
    } catch (e) {
        btn.classList.add('err');
        btn.textContent = '✗ Fehler';
        showToast('Test fehlgeschlagen: ' + e.message, 'error');
        setTimeout(() => {
            btn.classList.remove('err');
            btn.textContent = 'Testen';
        }, 3000);
    } finally {
        btn.disabled = false;
    }
}

function togglePanel(bodyId, chevronId) {
    const body = document.getElementById(bodyId);
    const chevron = document.getElementById(chevronId);
    const open = body.style.display === 'none';
    body.style.display = open ? 'block' : 'none';
    chevron.textContent = open ? '▼' : '▶';
}

function toggleObsidian() {
    togglePanel('obsidianFields', 'obsidianChevron');
}

function toggleHA() {
    const toggle = document.getElementById('haToggle');
    const fields = document.getElementById('haFields');
    toggle.classList.toggle('on');

    if (toggle.classList.contains('on')) {
        fields.style.opacity = '1';
        fields.style.pointerEvents = 'auto';
    } else {
        fields.style.opacity = '0.3';
        fields.style.pointerEvents = 'none';
    }
}

function toggleWakeGreeting() {
    const toggle = document.getElementById('wakeGreetingToggle');
    toggle.classList.toggle('on');
}

async function loadAvailableApps() {
    try {
        const resp = await fetch('/api/apps');
        const data = await resp.json();
        const apps = data.apps || [];

        // Populate all 6 dropdowns
        for (let i = 0; i < 6; i++) {
            const select = document.getElementById('program-' + i);
            if (select) {
                select.innerHTML = '<option value="">— App auswählen —</option>';
                apps.forEach(app => {
                    const opt = document.createElement('option');
                    opt.value = app;
                    opt.textContent = app;
                    select.appendChild(opt);
                });
            }
        }
    } catch (e) {
        console.error('Failed to load apps:', e);
    }
}

function loadPrograms(programs) {
    // Load saved programs into dropdowns (handle both null and undefined)
    for (let i = 0; i < 6; i++) {
        const select = document.getElementById('program-' + i);
        if (select) {
            const app = programs && programs[i];
            select.value = app || '';
        }
    }
}

async function saveConfig() {
    const btn = document.querySelector('.btn-primary');
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = '…';
    // Collect all 6 program slots (including empty ones, storing null for empty)
    const programs = [];
    for (let i = 0; i < 6; i++) {
        const select = document.getElementById('program-' + i);
        if (select) {
            programs.push(select.value || null);
        } else {
            programs.push(null);
        }
    }

    // Use selected voice or fallback to current/default if dropdown is empty
    const voiceId = voiceDb.active_voice_id
        || currentConfig.elevenlabs_voice_id
        || 'rDmv3mOhK6TnhYWckFaD';

    const config = {
        anthropic_api_key: document.getElementById('anthropicKey').value,
        elevenlabs_api_key: document.getElementById('elevenlabsKey').value,
        elevenlabs_voice_id: voiceId,
        user_name: document.getElementById('userName').value,
        user_address: document.getElementById('userAddress').value,
        city: document.getElementById('city').value,
        timezone: document.getElementById('timezone').value,
        language: document.getElementById('language').value,
        lat: parseFloat(document.getElementById('lat').value),
        lon: parseFloat(document.getElementById('lon').value),
        kachelmann_api_key: document.getElementById('kachelmannKey').value,
        workspace_path: document.getElementById('workspacePath').value,
        obsidian_inbox_path: document.getElementById('obsidianPath').value,
        obsidian_archive_path: document.getElementById('obsidianArchivePath').value,
        ha_url: document.getElementById('haUrl').value,
        ha_token: document.getElementById('haToken').value,
        ha_enabled: document.getElementById('haToggle').classList.contains('on'),
        browser_url: document.getElementById('browserUrl').value,
        spotify_track: document.getElementById('spotifyTrack').value,
        wake_greeting_enabled: document.getElementById('wakeGreetingToggle').classList.contains('on'),
        programs: programs
    };

    try {
        const resp = await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });

        const data = await resp.json();
        if (data.status === 'saved' && (!data.errors || data.errors.length === 0)) {
            btn.textContent = '✓ Gespeichert';
            btn.style.background = '#4cbf7e';
            showToast('Einstellungen gespeichert', 'success');
        } else {
            const errorMsg = data.errors && data.errors.length > 0 ? data.errors[0] : 'Fehler beim Speichern';
            btn.textContent = '✗ Fehler';
            btn.style.background = '#e05252';
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        btn.textContent = '✗ Fehler';
        btn.style.background = '#e05252';
        showToast('Speichern fehlgeschlagen: ' + e.message, 'error');
    } finally {
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = original;
            btn.style.background = '';
        }, 2500);
    }
}

function loadDefaults() {
    if (confirm('Wirklich auf Standardwerte zurücksetzen?')) {
        fetch('/api/reset_config', {method: 'POST'}).then(() => {
            loadConfig();
            showToast('Standardwerte geladen', 'success');
        });
    }
}

function restart() {
    document.getElementById('restartModal').classList.add('show');
}

function closeModal() {
    document.getElementById('restartModal').classList.remove('show');
}

async function confirmRestart() {
    closeModal();
    showToast('Server wird neu gestartet…', 'success');
    await fetch('/api/restart', {method: 'POST'}).catch(() => {});
    setTimeout(() => location.reload(), 2000);
}

function toggleVisibility(fieldId, btn) {
    const input = document.getElementById(fieldId);
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    btn.textContent = isHidden ? '🙈' : '👁';
    btn.title = isHidden ? 'Key verstecken' : 'Key anzeigen';
}

function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast show ' + type;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// ── Maintenance ───────────────────────────────────────────────────────────

async function openMaintenanceModal() {
    document.getElementById('maintenanceModal').classList.add('show');
    await mLoadStatus();
}

function closeMaintenanceModal() {
    document.getElementById('maintenanceModal').classList.remove('show');
    mRestoreButtons();
}

async function mLoadStatus() {
    try {
        const d = await (await fetch('/api/maintenance/status')).json();
        document.getElementById('mStatusNews').textContent = d.news_articles ?? '—';
        document.getElementById('mStatusNewsSub').textContent = d.news_last_fetch
            ? 'Letzter Fetch: ' + d.news_last_fetch.slice(0, 16).replace('T', ' ')
            : 'Noch kein Fetch';
        document.getElementById('mStatusBrief').textContent = d.brief_last_morning ?? 'Kein Brief';
        document.getElementById('mStatusBriefSub').textContent = `Schwellenwert: ${d.brief_threshold_minutes} min`;
        document.getElementById('mThresholdInput').value = d.brief_threshold_minutes ?? 30;
    } catch(e) {
        showToast('Status konnte nicht geladen werden', 'error');
    }
    mRestoreButtons();
}

function mRestoreButtons() {
    document.getElementById('mBtnNews').innerHTML =
        `<button class="btn btn-secondary" style="font-size:0.8rem;padding:7px 12px;" onclick="mAskConfirm('news')">🗑 Leeren</button>`;
    document.getElementById('mBtnBrief').innerHTML =
        `<button class="btn btn-secondary" style="font-size:0.8rem;padding:7px 12px;" onclick="mAskConfirm('brief')">🗑 Leeren</button>`;
    document.getElementById('mBtnAll').innerHTML =
        `<button class="btn btn-secondary" style="font-size:0.8rem;padding:7px 12px;border-color:rgba(224,82,82,0.4);color:#e05252;" onclick="mAskConfirm('all')">🗑 Alles</button>`;
}

function mAskConfirm(type) {
    const ids = {news: 'mBtnNews', brief: 'mBtnBrief', all: 'mBtnAll'};
    const el = document.getElementById(ids[type]);
    el.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
            <label style="display:flex;align-items:center;gap:8px;font-size:0.78rem;color:#aaa;cursor:pointer;">
                <input type="checkbox" id="mCheck_${type}" onchange="mCheckToggle('${type}')" style="accent-color:#e05252;width:14px;height:14px;flex-shrink:0;">
                Ja, unwiederbringlich löschen
            </label>
            <div style="display:flex;gap:6px;">
                <button class="btn-icon btn-del" id="mConfirmBtn_${type}" onclick="mDoReset('${type}')" disabled style="opacity:0.35;cursor:not-allowed;">Löschen</button>
                <button class="btn-icon btn-edit" onclick="mRestoreButtons()">Abbrechen</button>
            </div>
        </div>
    `;
}

function mCheckToggle(type) {
    const checked = document.getElementById(`mCheck_${type}`).checked;
    const btn = document.getElementById(`mConfirmBtn_${type}`);
    btn.disabled = !checked;
    btn.style.opacity = checked ? '1' : '0.35';
    btn.style.cursor = checked ? 'pointer' : 'not-allowed';
}

async function mDoReset(type) {
    const endpoint = {news: 'reset_news', brief: 'reset_brief', all: 'reset_all'}[type];
    try {
        const resp = await fetch(`/api/maintenance/${endpoint}`, {method: 'POST'});
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
        const label = {news: 'News-Archiv', brief: 'Daily Brief', all: 'Alles'}[type];
        showToast(`✅ ${label} geleert`, 'success');
        await mLoadStatus();
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
        mRestoreButtons();
    }
}

async function mSaveThreshold() {
    const minutes = parseInt(document.getElementById('mThresholdInput').value);
    if (isNaN(minutes) || minutes < 1 || minutes > 480) {
        showToast('Wert muss zwischen 1 und 480 Minuten liegen', 'error');
        return;
    }
    const btn = document.getElementById('mThresholdBtn');
    const orig = btn.textContent;
    btn.disabled = true; btn.textContent = '…';
    try {
        const resp = await fetch('/api/maintenance/set_threshold', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({minutes})
        });
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
        showToast(`✅ Schwellenwert: ${minutes} Minuten`, 'success');
        document.getElementById('mStatusBriefSub').textContent = `Schwellenwert: ${minutes} min`;
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
    } finally {
        setTimeout(() => { btn.disabled = false; btn.textContent = orig; }, 2000);
    }
}

// ── RSS Feeds Management ──────────────────────────────────────────────────

let _feedsData = [];
let _editingFeedId = null;

const _catColor = { apple: '#5bb8f5', tech: '#b478ff', science: '#4cbf7e' };
const _catBg    = { apple: 'rgba(42,158,226,0.15)', tech: 'rgba(180,120,255,0.12)', science: 'rgba(76,191,126,0.12)' };

function _escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function openFeedsModal() {
    document.getElementById('feedsModal').classList.add('show');
    await _loadFeeds();
}

function closeFeedsModal() {
    document.getElementById('feedsModal').classList.remove('show');
    hideFeedForm();
}

async function _loadFeeds() {
    try {
        const resp = await fetch('/api/rss_feeds');
        const data = await resp.json();
        _feedsData = data.feeds || [];
        _renderFeedsTable();
    } catch(e) {
        document.getElementById('feedsTableBody').innerHTML =
            '<tr><td colspan="5" style="color:#e05252;text-align:center;padding:16px;">Fehler beim Laden</td></tr>';
    }
}

function _renderFeedsTable() {
    const tbody = document.getElementById('feedsTableBody');
    if (!_feedsData.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="color:#555;text-align:center;padding:20px;">Keine Feeds konfiguriert. Klicke "+ Neuer Feed".</td></tr>';
        return;
    }
    tbody.innerHTML = _feedsData.map(f => {
        const cat     = f.category || '';
        const enabled = f.enabled !== false;
        const urlShort = (f.url || '').replace(/^https?:\/\//, '').slice(0, 40) + ((f.url||'').length > 46 ? '…' : '');
        return `<tr>
            <td class="col-name">${_escHtml(f.name || '')}</td>
            <td class="col-url" title="${_escHtml(f.url || '')}">${_escHtml(urlShort)}</td>
            <td><span class="feed-cat-badge" style="background:${_catBg[cat]||'rgba(255,255,255,0.06)'};color:${_catColor[cat]||'#888'}">${_escHtml(cat)||'—'}</span></td>
            <td><div class="toggle ${enabled?'on':''}" onclick="toggleFeedEnabled('${_escHtml(f.id)}')" title="${enabled?'Deaktivieren':'Aktivieren'}"></div></td>
            <td style="text-align:right;white-space:nowrap;">
                <button class="btn-icon btn-edit" onclick="showFeedForm('${_escHtml(f.id)}')">✎ Edit</button>
                <button class="btn-icon btn-del"  onclick="deleteFeed('${_escHtml(f.id)}')">✕</button>
            </td>
        </tr>`;
    }).join('');
}

function showFeedForm(feedId) {
    _editingFeedId = feedId;
    const box = document.getElementById('feedFormBox');
    document.getElementById('feedFormTitle').textContent = feedId ? 'Feed bearbeiten' : 'Neuer Feed';
    box.style.display = 'block';
    if (feedId) {
        const f = _feedsData.find(x => x.id === feedId);
        if (!f) return;
        document.getElementById('feedFormName').value     = f.name     || '';
        document.getElementById('feedFormUrl').value      = f.url      || '';
        document.getElementById('feedFormCategory').value = f.category || '';
    } else {
        document.getElementById('feedFormName').value     = '';
        document.getElementById('feedFormUrl').value      = '';
        document.getElementById('feedFormCategory').value = '';
    }
    document.getElementById('feedFormName').focus();
}

function hideFeedForm() {
    _editingFeedId = null;
    document.getElementById('feedFormBox').style.display = 'none';
}

async function saveFeedForm() {
    const name     = document.getElementById('feedFormName').value.trim();
    const url      = document.getElementById('feedFormUrl').value.trim();
    const category = document.getElementById('feedFormCategory').value.trim();
    if (!name) { showToast('Name erforderlich', 'error'); return; }
    if (!url)  { showToast('URL erforderlich', 'error'); return; }
    if (!url.startsWith('http')) { showToast('URL muss mit http/https beginnen', 'error'); return; }

    try {
        if (_editingFeedId) {
            const resp = await fetch(`/api/rss_feeds/${_editingFeedId}`, {
                method: 'PUT',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({name, url, category})
            });
            const data = await resp.json();
            if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
            const idx = _feedsData.findIndex(f => f.id === _editingFeedId);
            if (idx !== -1) Object.assign(_feedsData[idx], {name, url, category});
            showToast('Feed aktualisiert', 'success');
        } else {
            const resp = await fetch('/api/rss_feeds/add', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({name, url, category})
            });
            const data = await resp.json();
            if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
            _feedsData.push(data.feed);
            showToast(`"${name}" hinzugefügt`, 'success');
        }
        hideFeedForm();
        _renderFeedsTable();
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
    }
}

async function toggleFeedEnabled(feedId) {
    try {
        const resp = await fetch(`/api/rss_feeds/${feedId}/toggle`, {method: 'PUT'});
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
        const f = _feedsData.find(x => x.id === feedId);
        if (f) f.enabled = data.enabled;
        _renderFeedsTable();
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
    }
}

async function deleteFeed(feedId) {
    const f = _feedsData.find(x => x.id === feedId);
    if (!confirm(`Feed "${f?.name || feedId}" wirklich löschen?`)) return;
    try {
        const resp = await fetch(`/api/rss_feeds/${feedId}`, {method: 'DELETE'});
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
        _feedsData = _feedsData.filter(x => x.id !== feedId);
        _renderFeedsTable();
        showToast('Feed gelöscht', 'success');
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
    }
}

async function bulkSaveFeeds() {
    const btn = document.getElementById('feedsSaveBtn');
    const orig = btn.textContent;
    btn.disabled = true; btn.textContent = '…';
    try {
        const resp = await fetch('/api/rss_feeds', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({feeds: _feedsData})
        });
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Fehler', 'error'); return; }
        showToast(`✅ ${data.count} Feeds gespeichert`, 'success');
    } catch(e) {
        showToast('Fehler: ' + e.message, 'error');
    } finally {
        setTimeout(() => { btn.disabled = false; btn.textContent = orig; }, 2200);
    }
}
