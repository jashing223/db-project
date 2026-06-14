/* ═══════════════════════════════════════════════════════
   共用設定 — 現代寵物醫院管理系統
   將 USE_MOCK 改為 false 並設定 API_BASE 即可接真實後端
═══════════════════════════════════════════════════════ */
const API_BASE    = 'http://localhost:8000';
const USE_MOCK    = false;
const STORAGE_KEY = 'pet_hospital_mock_v1';
const SESSION_KEY = 'pet_hospital_session';

/* ── 對照表 ── */
const ROLE_NAME     = { 1: '櫃檯行政', 2: '護理人員', 3: '獸醫師', 4: '經理' };
const CATEGORY_LABEL = { 1: '藥品', 2: '檢驗', 3: '治療', 4: '住宿' };
function roleName(n)     { return ROLE_NAME[n]      || String(n); }
function categoryLabel(n){ return CATEGORY_LABEL[n]  || String(n); }

/* ── Utilities ── */
function todayStr() { return new Date().toISOString().slice(0, 10); }
function todayAt(t) { return `${todayStr()}T${t}:00`; }
function slotFromDatetime(dt) { return dt ? dt.slice(11, 16) : ''; }
function dateFromDatetime(dt) { return dt ? dt.slice(0, 10) : ''; }
function calcAge(birthDate) {
  if (!birthDate) return '未知';
  const diff = Date.now() - new Date(birthDate).getTime();
  const y = Math.floor(diff / (365.25 * 24 * 3600 * 1000));
  const m = Math.floor((diff % (365.25 * 24 * 3600 * 1000)) / (30.44 * 24 * 3600 * 1000));
  return y > 0 ? `${y}歲` : `${m}個月`;
}
function calcAgeYears(birthDate) {
  if (!birthDate) return 0;
  return Math.floor((Date.now() - new Date(birthDate).getTime()) / (365.25 * 24 * 3600 * 1000));
}

/* ── 預設資料 ── */
function getDefaultData() {
  return {
    owners: [
      { Owner_ID: 1, Full_Name: '陳小明', Phone_Number: '0912-345-678', Email_Address: null, Physical_Address: null, Is_Anonymized: false },
      { Owner_ID: 2, Full_Name: '林美玲', Phone_Number: '0987-654-321', Email_Address: null, Physical_Address: null, Is_Anonymized: false },
      { Owner_ID: 3, Full_Name: '張大偉', Phone_Number: '0933-111-222', Email_Address: null, Physical_Address: null, Is_Anonymized: false },
    ],
    pets: [
      { Pet_ID: 1, Owner_ID: 1, Pet_Name: '小白', Species_Type: '貓', Breed_Name: '混種', Birth_Date: '2024-03-10', Current_Weight: 3.2 },
      { Pet_ID: 2, Owner_ID: 1, Pet_Name: '旺財', Species_Type: '犬', Breed_Name: '柴犬',  Birth_Date: '2022-07-22', Current_Weight: 8.5 },
      { Pet_ID: 3, Owner_ID: 2, Pet_Name: '毛球', Species_Type: '兔', Breed_Name: null,    Birth_Date: '2023-11-01', Current_Weight: 1.8 },
      { Pet_ID: 4, Owner_ID: 3, Pet_Name: '咕嚕', Species_Type: '貓', Breed_Name: '波斯', Birth_Date: '2021-05-15', Current_Weight: 4.1 },
    ],
    // Staff 同時扮演 Staff + Doctors；Role_Level=3 者有 Specialty
    staff: [
      { Staff_ID: 1, Staff_Name: '王大明', Role_Level: 3, Specialty: '一般內科' },
    ],
    appointments: [
      { Appointment_ID: 1, Pet_ID: 1, Doc_Staff_ID: 1, Scheduled_Time: todayAt('09:00'), Appt_Status: 0 },
      { Appointment_ID: 2, Pet_ID: 3, Doc_Staff_ID: 2, Scheduled_Time: todayAt('10:00'), Appt_Status: 0 },
      { Appointment_ID: 3, Pet_ID: 4, Doc_Staff_ID: 1, Scheduled_Time: todayAt('11:00'), Appt_Status: 0 },
    ],
    catalog: [
      { Item_ID: 1, Item_Name: '阿莫西林 250mg',  Item_Category: 1, Current_Price: 20,   Stock_Quantity: 500,  Is_Discontinued: false },
      { Item_ID: 2, Item_Name: '血液常規檢查',    Item_Category: 2, Current_Price: 650,  Stock_Quantity: null, Is_Discontinued: false },
      { Item_ID: 3, Item_Name: '點滴（500ml）',   Item_Category: 3, Current_Price: 350,  Stock_Quantity: 80,   Is_Discontinued: false },
      { Item_ID: 4, Item_Name: 'X 光檢查',        Item_Category: 2, Current_Price: 900,  Stock_Quantity: null, Is_Discontinued: false },
      { Item_ID: 5, Item_Name: '疫苗（三合一）',  Item_Category: 1, Current_Price: 800,  Stock_Quantity: 30,   Is_Discontinued: false },
      { Item_ID: 6, Item_Name: '外科縫合處置',    Item_Category: 3, Current_Price: 1200, Stock_Quantity: null, Is_Discontinued: false },
      { Item_ID: 7, Item_Name: '一般病房住宿',    Item_Category: 4, Current_Price: 800,  Stock_Quantity: null, Is_Discontinued: false },
      { Item_ID: 8, Item_Name: '加護病房住宿',    Item_Category: 4, Current_Price: 1800, Stock_Quantity: null, Is_Discontinued: false },
    ],
    records:  [],
    invoices: [],
    _nextId:  200,
  };
}

/* ── localStorage 初始化 ── */
function loadMock() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return getDefaultData();
    const data = JSON.parse(raw);
    // 跨日時重建預設預約（保留使用者自建的 ID >= 200）
    const today = todayStr();
    const hasToday = data.appointments?.some(a => dateFromDatetime(a.Scheduled_Time) === today);
    if (!hasToday) {
      const def = getDefaultData();
      data.appointments = [
        ...def.appointments,
        ...(data.appointments?.filter(a => a.Appointment_ID >= 200) || []),
      ];
    }
    // 若 localStorage 沒有 staff（舊版資料），補上預設
    if (!data.staff) data.staff = getDefaultData().staff;
    return data;
  } catch(e) {
    return getDefaultData();
  }
}

function saveMock() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...MOCK, _nextId })); } catch(e) {}
}

function resetMock() {
  localStorage.removeItem(STORAGE_KEY);
  location.reload();
}

/* ── MOCK 初始化 ── */
const _loaded = loadMock();
const MOCK = {
  owners:       _loaded.owners,
  pets:         _loaded.pets,
  staff:        _loaded.staff,
  appointments: _loaded.appointments,
  catalog:      _loaded.catalog,
  records:      _loaded.records,
  invoices:     _loaded.invoices,
};
let _nextId = _loaded._nextId || 200;

/* ── Session ── */
function getCurrentUser() {
  try {
    const s = localStorage.getItem(SESSION_KEY);
    if (!s) return null;
    const u = JSON.parse(s);
    if (USE_MOCK) {
      // mock 模式：確認 staff 還存在
      if (MOCK.staff.find(m => m.Staff_ID === u.Staff_ID)) return u;
    } else {
      // 真實模式：有 token 就算登入
      if (u._token) return u;
    }
  } catch(e) {}
  return null;
}

function getToken() {
  try {
    const s = localStorage.getItem(SESSION_KEY);
    if (s) return JSON.parse(s)._token || null;
  } catch(e) {}
  return null;
}

function saveSession(user, token = null) {
  localStorage.setItem(SESSION_KEY, JSON.stringify({ ...user, _token: token }));
}

function login(staffId) {
  // mock 模式專用（同步）
  const u = MOCK.staff.find(s => s.Staff_ID === Number(staffId));
  if (!u) return;
  saveSession(u);
  location.href = 'appointment.html';
}

function logout() {
  localStorage.removeItem(SESSION_KEY);
  location.href = 'login.html';
}

/* ── 固定 busy slots ── */
const BUSY_SLOTS = { 1: ['10:00','14:00'], 2: ['09:00','11:00'], 3: ['13:00'] };
const ALL_SLOTS  = ['09:00','10:00','11:00','13:00','14:00','15:00','16:00'];

/* ── API wrapper ── */
async function api(method, path, body) {
  if (USE_MOCK) {
    return new Promise((res, rej) =>
      setTimeout(() => {
        try { res(mockRoute(method, path, body)); }
        catch(e) { rej(e); }
      }, 60)
    );
  }
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const r = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (r.status === 401) { logout(); return; }   // token 過期或無效 → 強制登出
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail || r.statusText);
  }
  return r.json();
}

/* ── Mock router ── */
function mockRoute(method, path, body) {
  const url = new URL('http://x' + path);

  // ── 飼主 ──
  if (path === '/owners') {
    return MOCK.owners
      .filter(o => !o.Is_Anonymized)
      .map(o => ({ ...o, pets: MOCK.pets.filter(p => p.Owner_ID === o.Owner_ID) }));
  }
  if (method === 'POST' && path === '/owners') {
    const o = { Owner_ID: _nextId++, Is_Anonymized: false, ...body };
    MOCK.owners.push(o); saveMock(); return o;
  }
  if (method === 'PATCH' && path.match(/^\/owners\/\d+$/) && !path.includes('/anonymize')) {
    const o = MOCK.owners.find(o => o.Owner_ID === parseInt(path.split('/')[2]));
    if (!o) throw new Error('飼主不存在');
    Object.assign(o, body); saveMock(); return o;
  }
  if (method === 'PATCH' && path.includes('/anonymize')) {
    const o = MOCK.owners.find(o => o.Owner_ID === parseInt(path.split('/')[2]));
    if (!o) throw new Error('飼主不存在');
    Object.assign(o, { Full_Name: 'Deleted User', Phone_Number: `deleted-${o.Owner_ID}-${Date.now()}`, Email_Address: null, Physical_Address: null, Is_Anonymized: true });
    saveMock(); return o;
  }

  // ── 寵物 ──
  if (path.startsWith('/pets?')) {
    const oid = parseInt(url.searchParams.get('owner_id'));
    return MOCK.pets.filter(p => p.Owner_ID === oid).map(p => ({ ...p, Age: calcAgeYears(p.Birth_Date) }));
  }
  if (method === 'POST' && path === '/pets') {
    const p = { Pet_ID: _nextId++, ...body }; MOCK.pets.push(p); saveMock(); return p;
  }
  if (method === 'PATCH' && path.match(/^\/pets\/\d+$/)) {
    const p = MOCK.pets.find(p => p.Pet_ID === parseInt(path.split('/')[2]));
    if (!p) throw new Error('寵物不存在');
    Object.assign(p, body); saveMock(); return p;
  }

  // ── 醫師（從 staff 過濾 Role_Level=3）──
  if (path === '/doctors') return MOCK.staff.filter(s => s.Role_Level === 3);

  // ── 排班 ──
  if (path.startsWith('/schedule')) {
    const did  = parseInt(url.searchParams.get('doctor_id'));
    const date = url.searchParams.get('date');
    const busy = BUSY_SLOTS[did] || [];
    const booked = MOCK.appointments
      .filter(a => a.Doc_Staff_ID === did && dateFromDatetime(a.Scheduled_Time) === date && a.Appt_Status !== 2)
      .map(a => slotFromDatetime(a.Scheduled_Time));
    return ALL_SLOTS.map(t => ({ time: t, available: !busy.includes(t) && !booked.includes(t) }));
  }

  // ── 預約 ──
  if (method === 'POST' && path === '/appointments') {
    const a = { Appointment_ID: _nextId++, Appt_Status: 0, ...body };
    MOCK.appointments.push(a); saveMock(); return a;
  }
  if (path === '/appointments/today') {
    const d = todayStr();
    return MOCK.appointments
      .filter(a => dateFromDatetime(a.Scheduled_Time) === d && a.Appt_Status === 0)
      .map(a => ({
        ...a,
        pet:    MOCK.pets.find(p => p.Pet_ID === a.Pet_ID),
        owner:  (() => { const p = MOCK.pets.find(p => p.Pet_ID === a.Pet_ID); return p ? MOCK.owners.find(o => o.Owner_ID === p.Owner_ID) : null; })(),
        doctor: MOCK.staff.find(s => s.Staff_ID === a.Doc_Staff_ID),
      }));
  }
  if (path.startsWith('/appointments?')) {
    const did  = parseInt(url.searchParams.get('doctor_id'));
    const date = url.searchParams.get('date');
    return MOCK.appointments
      .filter(a => a.Doc_Staff_ID === did && dateFromDatetime(a.Scheduled_Time) === date)
      .map(a => ({
        ...a,
        pet:    MOCK.pets.find(p => p.Pet_ID === a.Pet_ID),
        owner:  (() => { const p = MOCK.pets.find(p => p.Pet_ID === a.Pet_ID); return p ? MOCK.owners.find(o => o.Owner_ID === p.Owner_ID) : null; })(),
        doctor: MOCK.staff.find(s => s.Staff_ID === a.Doc_Staff_ID),
      }));
  }
  if (method === 'PATCH' && path.includes('/cancel')) {
    const appt = MOCK.appointments.find(a => a.Appointment_ID === parseInt(path.split('/')[2]));
    if (!appt) throw new Error('預約不存在');
    appt.Appt_Status = 2; saveMock(); return appt;
  }

  // ── 目錄 ──
  if (path === '/catalog') return MOCK.catalog.filter(c => !c.Is_Discontinued);
  if (path === '/catalog/all') return MOCK.catalog;
  if (method === 'PATCH' && path.match(/^\/catalog\/\d+$/)) {
    const item = MOCK.catalog.find(c => c.Item_ID === parseInt(path.split('/')[2]));
    if (!item) throw new Error('項目不存在');
    Object.assign(item, body); saveMock(); return item;
  }

  // ── 病歷 ──
  if (method === 'POST' && path === '/records') {
    const rec = { Record_ID: _nextId++, Record_Locked: false, details: [], ...body };
    MOCK.records.push(rec);
    MOCK.invoices.push({ Invoice_ID: _nextId++, Record_ID: rec.Record_ID, Total_Billed: 0.00, Payment_Status: 0, Payment_Method: null });
    saveMock(); return rec;
  }
  if (method === 'POST' && path.includes('/details') && !path.includes('/details/')) {
    const rid  = parseInt(path.split('/')[2]);
    const rec  = MOCK.records.find(r => r.Record_ID === rid);
    if (rec.Record_Locked) throw new Error('病歷已鎖定，無法新增項目');
    const item   = MOCK.catalog.find(i => i.Item_ID === body.Item_ID);
    const detail = { Detail_ID: _nextId++, Record_ID: rid, ...body, Historical_Price: item.Current_Price };
    rec.details.push(detail);
    const inv = MOCK.invoices.find(i => i.Record_ID === rid);
    if (inv) inv.Total_Billed = +(inv.Total_Billed + detail.Historical_Price * detail.Numeric_Value).toFixed(2);
    saveMock(); return detail;
  }
  if (method === 'DELETE' && path.includes('/details/')) {
    const parts = path.split('/');
    const rec   = MOCK.records.find(r => r.Record_ID === parseInt(parts[2]));
    if (rec.Record_Locked) throw new Error('病歷已鎖定，無法刪除項目');
    const idx = rec.details.findIndex(d => d.Detail_ID === parseInt(parts[4]));
    if (idx >= 0) {
      const d = rec.details[idx];
      const inv = MOCK.invoices.find(i => i.Record_ID === rec.Record_ID);
      if (inv) inv.Total_Billed = +(inv.Total_Billed - d.Historical_Price * d.Numeric_Value).toFixed(2);
      rec.details.splice(idx, 1);
    }
    saveMock(); return { ok: true };
  }
  if (method === 'PATCH' && path.includes('/draft')) {
    const rec = MOCK.records.find(r => r.Record_ID === parseInt(path.split('/')[2]));
    Object.assign(rec, body); saveMock(); return rec;
  }
  if (method === 'PATCH' && path.includes('/lock')) {
    const rec = MOCK.records.find(r => r.Record_ID === parseInt(path.split('/')[2]));
    Object.assign(rec, body, { Record_Locked: true });
    rec.details.forEach(d => {
      const item = MOCK.catalog.find(c => c.Item_ID === d.Item_ID);
      if (item?.Item_Category === 1) item.Stock_Quantity = Math.max(0, item.Stock_Quantity - d.Numeric_Value);
    });
    const appt = MOCK.appointments.find(a => a.Appointment_ID === rec.Appointment_ID);
    if (appt) appt.Appt_Status = 2;
    saveMock(); return rec;
  }

  // ── 帳單 ──
  if (path === '/invoices/pending') {
    return MOCK.invoices
      .filter(i => i.Payment_Status === 0)
      .map(i => {
        const rec  = MOCK.records.find(r => r.Record_ID === i.Record_ID);
        if (!rec?.Record_Locked) return null;
        const appt = MOCK.appointments.find(a => a.Appointment_ID === rec.Appointment_ID);
        const pet  = appt ? MOCK.pets.find(p => p.Pet_ID === appt.Pet_ID) : null;
        const owner = pet ? MOCK.owners.find(o => o.Owner_ID === pet.Owner_ID) : null;
        const enrichedDetails = (rec.details || []).map(d => {
          const cat = MOCK.catalog.find(c => c.Item_ID === d.Item_ID);
          return { ...d, Item_Name: cat?.Item_Name || '' };
        });
        return { ...i, record: { ...rec, details: enrichedDetails }, appt, pet, owner };
      })
      .filter(Boolean);
  }
  if (method === 'PATCH' && path.includes('/pay')) {
    const inv = MOCK.invoices.find(i => i.Invoice_ID === parseInt(path.split('/')[2]));
    if (!inv || inv.Payment_Status !== 0) throw new Error('帳單已結帳或不存在');
    Object.assign(inv, { Payment_Status: 1, ...body }); saveMock(); return inv;
  }

  throw new Error('Mock: 未實作 ' + method + ' ' + path);
}

/* ── Nav 定義（每個頁面可看到哪些連結由 roles 控制） ── */
const NAV_ITEMS = [
  { href: 'appointment.html', icon: '📅', label: '掛號預約',   roles: [1, 4] },
  { href: 'medical.html',     icon: '📋', label: '病歷 / 處方', roles: [2, 3, 4] },
  { href: 'invoice.html',     icon: '🧾', label: '帳單結算',   roles: [1, 4] },
  { href: 'owner.html',       icon: '👤', label: '飼主管理',   roles: [1, 4] },
  { href: 'inventory.html',   icon: '📦', label: '庫存查詢',   roles: [4] },
  { href: 'schedule.html',    icon: '🗓️', label: '預約查詢',   roles: [1, 4] },
];

/* ── 角色首頁（無權限時跳轉目標） ── */
const ROLE_HOME = { 1: 'appointment.html', 2: 'medical.html', 3: 'medical.html', 4: 'inventory.html' };

/* ── Sidebar 自動渲染 ＋ Auth Guard ＋ Role Guard（所有頁面共用） ── */
document.addEventListener('DOMContentLoaded', () => {
  // login.html 不需要 guard
  if (location.pathname.endsWith('login.html')) return;

  // 未登入 → 回登入頁
  const u = getCurrentUser();
  if (!u) { location.href = 'login.html'; return; }

  // Role guard：讀 <body data-roles="1,4"> 決定誰能進這個頁面
  const allowed = document.body.dataset.roles;
  if (allowed) {
    const levels = allowed.split(',').map(Number);
    if (!levels.includes(u.Role_Level)) {
      location.href = ROLE_HOME[u.Role_Level] || 'appointment.html';
      return;
    }
  }

  // 動態渲染 nav（只顯示該角色有權限的連結）
  const nav = document.querySelector('#sidebar nav');
  if (nav) {
    const current = location.pathname.split('/').pop();
    nav.innerHTML = NAV_ITEMS
      .filter(item => item.roles.includes(u.Role_Level))
      .map(item => `
        <a${item.href === current ? ' class="active"' : ''} href="${item.href}">
          <span class="icon">${item.icon}</span> ${item.label}
        </a>`)
      .join('');
  }

  // 渲染 sidebar 使用者資訊
  const el = document.getElementById('user-info');
  if (!el) return;
  el.innerHTML = `
    <div class="user-role">${ROLE_NAME[u.Role_Level] || '未知'} · Role ${u.Role_Level}</div>
    <div class="user-name">${u.Staff_Name}</div>
    <button onclick="logout()"
      style="margin-top:8px;width:100%;font-size:11px;background:transparent;color:#6b7280;border:1px solid #374151;border-radius:4px;padding:4px 0;cursor:pointer;transition:all .15s"
      onmouseover="this.style.color='#e5e7eb'" onmouseout="this.style.color='#6b7280'">
      登出
    </button>
  `;
});

/* ── Toast ── */
let _toastTimer;
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = 'show ' + type;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => (el.className = ''), 2800);
}
