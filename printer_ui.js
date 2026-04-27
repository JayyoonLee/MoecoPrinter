const BASE = "http://localhost:8765";

// DOM
const refreshBtn    = document.getElementById('refreshBtn');
const sendBtn       = document.getElementById('sendBtn');
const addFieldBtn   = document.getElementById('addFieldBtn');
const fieldRows     = document.getElementById('fieldRows');
const clearLogBtn   = document.getElementById('clearLogBtn');
const statusDot     = document.getElementById('statusDot');
const statusText    = document.getElementById('statusText');
const engineState   = document.getElementById('engineState');
const fieldList     = document.getElementById('fieldList');
const logEl         = document.getElementById('logEl');
const msgInput      = document.getElementById('msgInput');
const msgDatalist   = document.getElementById('msgDatalist');
const sendCardLabel = document.getElementById('sendCardLabel');
const genInput        = document.getElementById('genInput');
const genBtn          = document.getElementById('genBtn');
const btnContainer    = document.getElementById('btnContainer');
const seqCount        = document.getElementById('seqCount');
const seqValue        = document.getElementById('seqValue');
const seqGenBtn       = document.getElementById('seqGenBtn');
const seqBtnContainer = document.getElementById('seqBtnContainer');

const MSG_STORAGE_KEY = 'moeco_msg_history';

// source_info에서 읽은 현재 메시지 필드 목록
let currentFields = [];

function loadMsgHistory() {
    try { return JSON.parse(localStorage.getItem(MSG_STORAGE_KEY)) || []; }
    catch { return []; }
}

function saveMsgToHistory(name) {
    if (!name) return;
    const list = loadMsgHistory().filter(m => m !== name);
    list.unshift(name);
    localStorage.setItem(MSG_STORAGE_KEY, JSON.stringify(list.slice(0, 20)));
    renderDatalist();
}

function renderDatalist() {
    msgDatalist.innerHTML = loadMsgHistory()
        .map(m => `<option value="${m}">`)
        .join('');
}

function log(msg, type = 'info') {
    const t = new Date().toLocaleTimeString();
    const el = document.createElement('div');
    el.className = `log-entry log-${type}`;
    el.innerHTML = `<span class="log-time">[${t}]</span>${msg}`;
    logEl.appendChild(el);
    logEl.scrollTop = logEl.scrollHeight;
}

function setStatus(connected) {
    statusDot.className  = `status-dot ${connected ? 'connected' : 'disconnected'}`;
    statusText.className = `status-text ${connected ? 'connected' : 'disconnected'}`;
    statusText.textContent = connected ? 'Connected' : 'Disconnected';
}

async function api(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(`${BASE}${path}`, opts);
    return resp.json();
}

async function getStatus() {
    try {
        const data = await api('GET', '/engine/real');
        setStatus(true);
        refreshBtn.disabled = false;
        sendBtn.disabled = false;
        addFieldBtn.disabled = false;
        msgInput.disabled = false;
        genBtn.disabled = false;
        seqGenBtn.disabled = false;
        engineState.textContent = `state: ${data.state}  |  message: ${data.data_name}  |  output: ${data.output}`;
        currentFields = data.source_info || [];
        fieldList.innerHTML = currentFields.map(f =>
            `<span class="field-tag">id:${f.id} · ${f.name}</span>`
        ).join('');
        refreshFieldLabels();
        // 현재 로드된 메시지를 입력창에 반영 + 이력 저장
        if (data.data_name) {
            msgInput.value = data.data_name;
            saveMsgToHistory(data.data_name);
            sendCardLabel.textContent = `Send — ${data.data_name}`;
        }
        log(`Status OK — state: ${data.state}, message: ${data.data_name}`, 'success');
    } catch (e) {
        setStatus(false);
        log(`Failed to reach printer: ${e.message}`, 'error');
    }
}


const sleep = ms => new Promise(r => setTimeout(r, ms));

function refreshFieldLabels() {
    // Send 카드 동적 필드 라벨 업데이트
    fieldRows.querySelectorAll('.field-label').forEach((label, i) => {
        label.textContent = currentFields[i]?.name || `Field ${i + 1}`;
    });
    // 제거 버튼: 행이 1개면 숨김
    const removeBtns = fieldRows.querySelectorAll('.btn-field-remove');
    removeBtns.forEach(btn => {
        btn.style.visibility = removeBtns.length > 1 ? 'visible' : 'hidden';
    });
    // Sequence Generator 두 번째 필드 라벨
    const seqLabel = document.getElementById('seqValueLabel');
    if (seqLabel && currentFields[1]?.name) seqLabel.textContent = currentFields[1].name;
}

function addFieldRow() {
    const index = fieldRows.querySelectorAll('.field-input').length;
    const label = currentFields[index]?.name || `Field ${index + 1}`;

    const row = document.createElement('div');
    row.className = 'input-row';
    row.innerHTML = `
        <span class="input-label field-label">${label}</span>
        <input type="text" class="field-input" placeholder="값 입력">
        <button class="btn-field-remove" type="button">−</button>
    `;
    row.querySelector('.btn-field-remove').addEventListener('click', () => {
        if (fieldRows.querySelectorAll('.input-row').length > 1) {
            row.remove();
            refreshFieldLabels();
        }
    });
    fieldRows.appendChild(row);
    refreshFieldLabels();
}

// values: content 값 배열 (필드명은 내부에서 currentFields 기준으로 결정)
async function printSequence(msgName, values) {
    const status = await api('GET', '/engine/real');

    if (status.data_name !== msgName || status.state === 'completed') {
        const stop = await api('DELETE', '/engine/printjob', { id: 0 });
        log(`stop: ${JSON.stringify(stop)}`, 'info');
        await sleep(500);

        const start = await api('POST', '/engine/printjob', {
            hash: 11112,
            attribute: { print_data_name: msgName }
        });
        log(`start ${msgName}: ${JSON.stringify(start)}`, 'info');
        await sleep(1000);

        // 새 메시지의 실제 필드 정보 갱신
        const updated = await api('GET', '/engine/real');
        currentFields = updated.source_info || [];
        refreshFieldLabels();
        log(`fields updated: ${currentFields.map(f => f.name).join(', ')}`, 'info');
    } else {
        log(`[${msgName}] already loaded — skip restart`, 'info');
    }

    const data = values.map((content, i) => ({
        type: 'text',
        name: currentFields[i]?.name || `field${i}`,
        content
    }));

    log(`sending: ${JSON.stringify(data)}`, 'info');
    const result = await api('POST', '/engine/dynamic', {
        print_mode: 'single',
        data
    });
    return result;
}

function createNumberBtn(value) {
    const btn = document.createElement('button');
    btn.className = 'btn-number';
    btn.textContent = value;
    btn.addEventListener('click', async () => {
        btn.remove();
        const msgName = msgInput.value.trim() || 'Msg2';
        log(`[${msgName}] Button send: ${value}`, 'info');
        try {
            const result = await printSequence(msgName, [value]);
            log(`[${msgName}] ${result.descript || JSON.stringify(result)}`, result.status === 'ok' ? 'success' : 'error');
        } catch (e) {
            log(`[${msgName}] Error: ${e.message}`, 'error');
        }
    });
    btnContainer.appendChild(btn);
}

genBtn.addEventListener('click', () => {
    const val = genInput.value.trim();
    if (!val) return;
    createNumberBtn(val);
    genInput.value = '';
    genInput.focus();
});

genInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') genBtn.click();
});

// 시퀀스 버튼 생성기
function createSeqBtn(index, val2) {
    const btn = document.createElement('button');
    btn.className = 'btn-number';
    btn.textContent = `${index}  ${val2}`;
    btn.addEventListener('click', async () => {
        btn.remove();
        const msgName = msgInput.value.trim() || 'Msg1';
        log(`[${msgName}] Seq send: [${index}, ${val2}]`, 'info');
        try {
            const result = await printSequence(msgName, [String(index), val2]);
            log(`[${msgName}] ${result.descript || JSON.stringify(result)}`, result.status === 'ok' ? 'success' : 'error');
        } catch (e) {
            log(`[${msgName}] Error: ${e.message}`, 'error');
        }
    });
    seqBtnContainer.appendChild(btn);
}

seqGenBtn.addEventListener('click', () => {
    const count = parseInt(seqCount.value);
    const val2  = seqValue.value.trim();
    if (!count || count < 1 || !val2) return;
    seqBtnContainer.innerHTML = '';
    for (let i = 1; i <= count; i++) {
        createSeqBtn(i, val2);
    }
});

msgInput.addEventListener('change', () => {
    const name = msgInput.value.trim();
    if (name) sendCardLabel.textContent = `Send — ${name}`;
});

addFieldBtn.addEventListener('click', () => addFieldRow());

// Send
sendBtn.addEventListener('click', async () => {
    const msgName = msgInput.value.trim() || 'Msg2';
    const values  = [...fieldRows.querySelectorAll('.field-input')].map(i => i.value);
    try {
        const result = await printSequence(msgName, values);
        saveMsgToHistory(msgName);
        log(`[${msgName}] ${result.descript || JSON.stringify(result)}`, result.status === 'ok' ? 'success' : 'error');
    } catch (e) {
        log(`[${msgName}] Error: ${e.message}`, 'error');
    }
});

refreshBtn.addEventListener('click', getStatus);
clearLogBtn.addEventListener('click', () => { logEl.innerHTML = ''; });

// 초기화
renderDatalist();
addFieldRow();
getStatus();
