"""
Admin Panel — واجهة ويب لتعديل إعدادات البوت
يشتغل جنب bot_railway.py على نفس السيرفر
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading

CONFIG_FILE = "config.json"
PORT = int(os.environ.get("PORT", 8080))


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"welcome": {"title": "المساعد الذكي", "body": "", "subscribe_msg": ""}, "sections": [], "faqs": []}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>لوحة تحكم البوت</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #222536;
    --border: #2e3248;
    --accent: #5b6af0;
    --accent2: #7c8bff;
    --text: #e8eaf6;
    --muted: #8b90b8;
    --success: #4caf88;
    --danger: #e05c6e;
  }
  body { font-family: 'Tajawal', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  .topbar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0 2rem;
    display: flex; align-items: center; justify-content: space-between;
    height: 60px; position: sticky; top: 0; z-index: 100;
  }
  .topbar .logo { font-size: 17px; font-weight: 700; color: var(--accent2); letter-spacing: -0.3px; }
  .topbar .status { font-size: 12px; color: var(--success); display: flex; align-items: center; gap: 6px; }
  .topbar .status::before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: var(--success); display: inline-block; }

  .layout { display: grid; grid-template-columns: 200px 1fr; min-height: calc(100vh - 60px); }

  .sidebar {
    background: var(--surface);
    border-left: 1px solid var(--border);
    padding: 1.5rem 0;
  }
  .nav-item {
    display: block; padding: 10px 1.5rem;
    font-size: 14px; color: var(--muted);
    cursor: pointer; transition: all 0.15s;
    border-right: 3px solid transparent;
  }
  .nav-item:hover { color: var(--text); background: var(--surface2); }
  .nav-item.active { color: var(--accent2); border-right-color: var(--accent); background: var(--surface2); }

  .main { padding: 2rem; max-width: 760px; }

  .section { display: none; }
  .section.active { display: block; }

  .section-title { font-size: 20px; font-weight: 700; margin-bottom: 1.5rem; color: var(--text); }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
  }
  .card-title { font-size: 14px; font-weight: 500; color: var(--muted); margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.5px; font-size: 12px; }

  label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; margin-top: 14px; }
  label:first-of-type { margin-top: 0; }

  input[type=text], textarea {
    width: 100%; padding: 10px 14px;
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text);
    font-family: 'Tajawal', sans-serif; font-size: 14px;
    transition: border-color 0.15s; direction: rtl;
  }
  input[type=text]:focus, textarea:focus {
    outline: none; border-color: var(--accent);
  }
  textarea { min-height: 90px; resize: vertical; }

  .btn {
    padding: 9px 20px; border-radius: 8px;
    font-family: 'Tajawal', sans-serif; font-size: 14px;
    cursor: pointer; border: none; transition: all 0.15s;
    font-weight: 500;
  }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent2); }
  .btn-danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); padding: 6px 14px; font-size: 12px; }
  .btn-danger:hover { background: var(--danger); color: #fff; }
  .btn-secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }

  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

  .item-list { display: flex; flex-direction: column; gap: 8px; }
  .item {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px 14px;
    display: flex; align-items: flex-start; gap: 12px;
  }
  .item-content { flex: 1; }
  .item-q { font-size: 14px; font-weight: 500; margin-bottom: 4px; }
  .item-a { font-size: 13px; color: var(--muted); line-height: 1.5; }
  .item-actions { flex-shrink: 0; }

  .toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: var(--success); color: #fff;
    padding: 10px 24px; border-radius: 8px;
    font-size: 14px; font-weight: 500;
    opacity: 0; transition: opacity 0.2s; pointer-events: none;
    z-index: 999;
  }
  .toast.show { opacity: 1; }
  .toast.error { background: var(--danger); }

  .empty { text-align: center; padding: 2rem; color: var(--muted); font-size: 14px; }

  .actions-row { display: flex; gap: 8px; margin-top: 14px; }
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">⚡ لوحة تحكم البوت</div>
  <div class="status">البوت شغال</div>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="nav-item active" onclick="show('faqs')">الأسئلة والأجوبة</div>
    <div class="nav-item" onclick="show('sections')">أقسام القائمة</div>
    <div class="nav-item" onclick="show('welcome')">رسالة الترحيب</div>
  </div>

  <div class="main">

    <!-- أسئلة وأجوبة -->
    <div class="section active" id="sec-faqs">
      <div class="section-title">الأسئلة والأجوبة</div>

      <div class="card">
        <div class="card-title">إضافة سؤال جديد</div>
        <label>السؤال</label>
        <input type="text" id="new-q" placeholder="اكتب السؤال هنا...">
        <label>الجواب</label>
        <textarea id="new-a" placeholder="اكتب الجواب هنا..."></textarea>
        <div class="actions-row">
          <button class="btn btn-primary" onclick="addFaq()">إضافة ✓</button>
          <button class="btn btn-secondary" onclick="clearFaqForm()">مسح</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">الأسئلة الحالية</div>
        <div class="item-list" id="faq-list"></div>
      </div>
    </div>

    <!-- أقسام القائمة -->
    <div class="section" id="sec-sections">
      <div class="section-title">أقسام القائمة</div>

      <div class="card">
        <div class="card-title">إضافة قسم جديد</div>
        <div class="row">
          <div>
            <label>اسم الزرار</label>
            <input type="text" id="new-sname" placeholder="مثال: تفاصيل الكورس">
          </div>
          <div>
            <label>أيقونة</label>
            <input type="text" id="new-sicon" placeholder="مثال: 📚">
          </div>
        </div>
        <label>المحتوى</label>
        <textarea id="new-scontent" placeholder="النص اللي يظهر لما المستخدم يضغط..."></textarea>
        <div class="actions-row">
          <button class="btn btn-primary" onclick="addSection()">إضافة ✓</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">الأقسام الحالية</div>
        <div class="item-list" id="sections-list"></div>
      </div>
    </div>

    <!-- رسالة الترحيب -->
    <div class="section" id="sec-welcome">
      <div class="section-title">رسالة الترحيب</div>

      <div class="card">
        <label>اسم المساعد</label>
        <input type="text" id="w-title" placeholder="المساعد الذكي">
        <label>نص الترحيب</label>
        <textarea id="w-body" style="min-height:120px"></textarea>
        <label>رسالة طلب الاشتراك</label>
        <input type="text" id="w-sub">
        <div class="actions-row">
          <button class="btn btn-primary" onclick="saveWelcome()">حفظ التغييرات ✓</button>
        </div>
      </div>
    </div>

  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let config = {};

async function loadConfig() {
  const res = await fetch('/api/config');
  config = await res.json();
  renderFaqs();
  renderSections();
  renderWelcome();
}

function show(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('sec-' + name).classList.add('active');
  event.target.classList.add('active');
}

function toast(msg, err=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' error' : '');
  setTimeout(() => t.className = 'toast', 2500);
}

async function saveConfig() {
  const res = await fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(config)
  });
  if (res.ok) toast('✅ تم الحفظ بنجاح');
  else toast('❌ حصل خطأ', true);
}

function renderFaqs() {
  const list = document.getElementById('faq-list');
  if (!config.faqs || config.faqs.length === 0) {
    list.innerHTML = '<div class="empty">لا توجد أسئلة بعد</div>';
    return;
  }
  list.innerHTML = config.faqs.map((f, i) => `
    <div class="item">
      <div class="item-content">
        <div class="item-q">${f.q}</div>
        <div class="item-a">${f.a}</div>
      </div>
      <div class="item-actions">
        <button class="btn btn-danger" onclick="deleteFaq(${i})">حذف</button>
      </div>
    </div>
  `).join('');
}

function addFaq() {
  const q = document.getElementById('new-q').value.trim();
  const a = document.getElementById('new-a').value.trim();
  if (!q || !a) { toast('⚠️ أدخل السؤال والجواب', true); return; }
  if (!config.faqs) config.faqs = [];
  config.faqs.push({q, a});
  renderFaqs();
  saveConfig();
  clearFaqForm();
}

function deleteFaq(i) {
  config.faqs.splice(i, 1);
  renderFaqs();
  saveConfig();
}

function clearFaqForm() {
  document.getElementById('new-q').value = '';
  document.getElementById('new-a').value = '';
}

function renderSections() {
  const list = document.getElementById('sections-list');
  if (!config.sections || config.sections.length === 0) {
    list.innerHTML = '<div class="empty">لا توجد أقسام بعد</div>';
    return;
  }
  list.innerHTML = config.sections.map((s, i) => `
    <div class="item">
      <div class="item-content">
        <div class="item-q">${s.icon} ${s.name}</div>
        <div class="item-a">${s.content.substring(0, 80)}${s.content.length > 80 ? '...' : ''}</div>
      </div>
      <div class="item-actions">
        <button class="btn btn-danger" onclick="deleteSection(${i})">حذف</button>
      </div>
    </div>
  `).join('');
}

function addSection() {
  const name = document.getElementById('new-sname').value.trim();
  const icon = document.getElementById('new-sicon').value.trim() || '📌';
  const content = document.getElementById('new-scontent').value.trim();
  if (!name || !content) { toast('⚠️ أدخل الاسم والمحتوى', true); return; }
  if (!config.sections) config.sections = [];
  config.sections.push({icon, name, content});
  renderSections();
  saveConfig();
  document.getElementById('new-sname').value = '';
  document.getElementById('new-sicon').value = '';
  document.getElementById('new-scontent').value = '';
}

function deleteSection(i) {
  config.sections.splice(i, 1);
  renderSections();
  saveConfig();
}

function renderWelcome() {
  const w = config.welcome || {};
  document.getElementById('w-title').value = w.title || '';
  document.getElementById('w-body').value = w.body || '';
  document.getElementById('w-sub').value = w.subscribe_msg || '';
}

function saveWelcome() {
  config.welcome = {
    title: document.getElementById('w-title').value,
    body: document.getElementById('w-body').value,
    subscribe_msg: document.getElementById('w-sub').value,
  };
  saveConfig();
}

loadConfig();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # اخفي الـ logs العادية

    def do_GET(self):
        if self.path == '/api/config':
            data = json.dumps(load_config(), ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/config':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode('utf-8'))
                save_config(data)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"ok": false}')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run():
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"✅ Admin Panel شغال على port {PORT}")
    server.serve_forever()


if __name__ == '__main__':
    run()
