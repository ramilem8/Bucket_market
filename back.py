"""
TaskBloom — Flask Backend
pip install flask
Çalışdırmaq üçün: python app.py
Sonra brauzderdə: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json, base64, os
from datetime import datetime

app = Flask(__name__)

# ─── Sadə yaddaş (real layihədə verilənlər bazası işlət) ───
DB_FILE = "taskbloom_data.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"balance": 0, "tasks": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Mağaza məhsulları ───
SHOP_ITEMS = [
    {"id": "gul_qizilgul",  "name": "Qızılgül",       "emoji": "🌹", "price": 30,  "type": "gul"},
    {"id": "gul_orxideya",  "name": "Orxideya",        "emoji": "🌸", "price": 40,  "type": "gul"},
    {"id": "gul_cobanyast", "name": "Çobanyastığı",    "emoji": "💐", "price": 25,  "type": "gul"},
    {"id": "gul_lale",      "name": "Lalə",             "emoji": "🌷", "price": 28,  "type": "gul"},
    {"id": "hed_qarku",     "name": "Qar kürəsi",       "emoji": "🔮", "price": 80,  "type": "hediyye"},
    {"id": "hed_ayiciq",    "name": "Oyuncaq ayı",      "emoji": "🧸", "price": 60,  "type": "hediyye"},
    {"id": "hed_pishik",    "name": "Oyuncaq pişik",    "emoji": "🐱", "price": 55,  "type": "hediyye"},
    {"id": "hed_it",        "name": "Oyuncaq it",       "emoji": "🐶", "price": 55,  "type": "hediyye"},
    {"id": "hed_hotwheels", "name": "Hot Wheels",       "emoji": "🏎️", "price": 50,  "type": "hediyye"},
    {"id": "hed_saat",      "name": "Qol saatı",        "emoji": "⌚", "price": 150, "type": "hediyye"},
]

# ─── API: Tapşırıqlar ───

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    db = load_db()
    return jsonify({"tasks": db["tasks"], "balance": db["balance"]})

@app.route("/api/tasks", methods=["POST"])
def add_task():
    db = load_db()
    data = request.get_json()
    text = data.get("text", "").strip()
    reward = int(data.get("reward", 10))
    if not text:
        return jsonify({"error": "Tapşırıq mətni boş ola bilməz"}), 400
    task = {
        "id": datetime.now().timestamp(),
        "text": text,
        "reward": reward,
        "done": False
    }
    db["tasks"].append(task)
    save_db(db)
    return jsonify(task), 201

@app.route("/api/tasks/<float:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    db = load_db()
    for task in db["tasks"]:
        if task["id"] == task_id and not task["done"]:
            task["done"] = True
            db["balance"] += task["reward"]
            save_db(db)
            return jsonify({"balance": db["balance"], "earned": task["reward"]})
    return jsonify({"error": "Tapşırıq tapılmadı"}), 404

@app.route("/api/tasks/<float:task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = load_db()
    before = len(db["tasks"])
    removed = next((t for t in db["tasks"] if t["id"] == task_id), None)
    db["tasks"] = [t for t in db["tasks"] if t["id"] != task_id]
    if removed and removed["done"]:
        db["balance"] = max(0, db["balance"] - removed["reward"])
    if len(db["tasks"]) < before:
        save_db(db)
        return jsonify({"ok": True, "balance": db["balance"]})
    return jsonify({"error": "Tapılmadı"}), 404

# ─── API: Mağaza ───

@app.route("/api/shop", methods=["GET"])
def get_shop():
    return jsonify(SHOP_ITEMS)

# ─── API: Sifariş (checkout) ───

@app.route("/api/checkout", methods=["POST"])
def checkout():
    db = load_db()
    data = request.get_json()
    item_ids = data.get("item_ids", [])
    recipient = data.get("recipient", "").strip()

    if not item_ids:
        return jsonify({"error": "Heç bir məhsul seçilməyib"}), 400
    if not recipient:
        return jsonify({"error": "Alıcının adı yazılmalıdır"}), 400

    selected = [s for s in SHOP_ITEMS if s["id"] in item_ids]
    total = sum(s["price"] for s in selected)

    if db["balance"] < total:
        return jsonify({"error": f"Balans kifayət deyil. Lazım: {total} q, Mövcud: {db['balance']} q"}), 400

    db["balance"] -= total
    save_db(db)

    has_flowers = any(s["type"] == "gul" for s in selected)
    has_gifts = any(s["type"] == "hediyye" for s in selected)
    if has_flowers and has_gifts:
        packaging = "Güllər buketdə, hədiyyələr qutuda"
    elif has_flowers:
        packaging = "Güllər gözəl buketdə"
    else:
        packaging = "Hədiyyələr bəzəkli qutuda"

    payload = {
        "to": recipient,
        "items": [{"emoji": s["emoji"], "name": s["name"], "type": s["type"]} for s in selected],
        "total": total,
        "packaging": packaging,
        "date": datetime.now().strftime("%d.%m.%Y")
    }
    encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()
    link = f"http://localhost:5000/hediyye/{encoded}"

    return jsonify({
        "ok": True,
        "link": link,
        "balance": db["balance"],
        "packaging": packaging,
        "total": total
    })

# ─── Hədiyyə görünüşü ───

GIFT_HTML = """
<!DOCTYPE html>
<html lang="az">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎀 Sənin üçün hədiyyə!</title>
<style>
  body { margin:0; font-family:'Segoe UI',system-ui,sans-serif;
         background: linear-gradient(135deg,#fce4ec,#fff8e1);
         min-height:100vh; display:flex; align-items:center; justify-content:center; }
  .card { background:white; border-radius:20px; padding:2.5rem 2rem;
          max-width:400px; width:90%; text-align:center;
          box-shadow:0 8px 40px rgba(231,84,128,0.15); }
  h1 { color:#e75480; font-size:1.5rem; margin:0.5rem 0 0.3rem; }
  .date { color:#9ca3af; font-size:0.85rem; margin-bottom:1.5rem; }
  .box { background:#fce4ec; border-radius:12px; padding:1.2rem;
         margin-bottom:1.2rem; text-align:left; }
  .box p { margin:4px 0; font-size:0.92rem; }
  .box strong { color:#9d174d; }
  .item { padding:3px 0; font-size:0.95rem; }
  .footer { color:#e75480; font-weight:700; font-size:1.05rem; }
  .sub { color:#9ca3af; font-size:0.8rem; margin-top:0.4rem; }
</style>
</head>
<body>
<div class="card">
  <div style="font-size:3rem">🎀</div>
  <h1>{{ data.to }} üçün hədiyyə!</h1>
  <p class="date">Hazırlanma tarixi: {{ data.date }}</p>
  <div class="box">
    <p><strong>📦 Qablaşdırma:</strong></p>
    <p>{{ data.packaging }}</p>
    <br>
    <p><strong>🎁 İçindəkilər:</strong></p>
    {% for item in data.items %}
    <p class="item">{{ item.emoji }} {{ item.name }}</p>
    {% endfor %}
    <br>
    <p><strong>💰 Cəm:</strong> {{ data.total }} qəpik</p>
  </div>
  <p class="footer">Sevgiylə, TaskBloom 🌸</p>
  <p class="sub">Bu hədiyyəni xüsusi bir insan göndərdi 💝</p>
</div>
</body>
</html>
"""

@app.route("/hediyye/<encoded>")
def gift_view(encoded):
    try:
        payload = json.loads(base64.b64decode(encoded.encode()).decode())
        return render_template_string(GIFT_HTML, data=payload)
    except Exception:
        return "<h2>Keçərsiz link 😢</h2>", 400

# ─── Ana səhifə (HTML faylı qaytarır) ───

@app.route("/")
def index():
    html_path = os.path.join(os.path.dirname(__file__), "todo_hediyye.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h2>todo_hediyye.html faylı tapılmadı. HTML faylını bu Python faylının yanına qoy.</h2>"

if __name__ == "__main__":
    print("🌸 TaskBloom işə başladı: http://localhost:5000")
    app.run(debug=True)