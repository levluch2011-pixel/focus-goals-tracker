import os
import sys
import json
import time
import sqlite3
import threading

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from pywebpush import webpush, WebPushException
from py_vapid import Vapid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAPID_FILE = os.path.join(BASE_DIR, "vapid_keys.json")
DB_FILE = os.path.join(BASE_DIR, "server_push.db")

# 1. Load or Generate VAPID Keys
if not os.path.exists(VAPID_FILE):
    vapid = Vapid()
    vapid.generate_keys()
    import base64
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    raw_pub = vapid.public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint
    )
    b64_pub = base64.urlsafe_b64encode(raw_pub).rstrip(b'=').decode('utf-8')
    pem_priv = vapid.private_pem().decode('utf-8')
    with open(VAPID_FILE, 'w', encoding='utf-8') as f:
        json.dump({'public_key': b64_pub, 'private_key': pem_priv}, f, indent=2)

with open(VAPID_FILE, 'r', encoding='utf-8') as f:
    VAPID_KEYS = json.load(f)

VAPID_PUBLIC_KEY = VAPID_KEYS['public_key']
VAPID_PRIVATE_KEY = VAPID_KEYS['private_key']
VAPID_CLAIMS = {"sub": "mailto:focusgoals@app.internal"}

# 2. Database Initialization
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT UNIQUE,
                p256dh TEXT,
                auth TEXT,
                goals_json TEXT DEFAULT '[]',
                notified_keys TEXT DEFAULT '[]',
                timezone_offset INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

# 3. Flask App Initialization
app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

@app.after_request
def add_headers(response):
    response.headers['Service-Worker-Allowed'] = '/'
    return response

# Static routes
@app.route('/')
def serve_index():
    return send_file(os.path.join(BASE_DIR, 'index.html'))

@app.route('/sw.js')
def serve_sw():
    response = send_file(os.path.join(BASE_DIR, 'sw.js'), mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/manifest.json')
def serve_manifest():
    return send_file(os.path.join(BASE_DIR, 'manifest.json'), mimetype='application/manifest+json')

@app.route('/<path:filename>')
def serve_static(filename):
    file_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "Not Found", 404

# API Endpoints
@app.route('/api/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    return jsonify({'publicKey': VAPID_PUBLIC_KEY})

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json(silent=True) or {}
    sub = data.get('subscription') or {}
    endpoint = sub.get('endpoint')
    keys = sub.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')
    goals = json.dumps(data.get('goals') or [], ensure_ascii=False)
    tz_offset = data.get('timezoneOffset', 0)

    if not endpoint or not p256dh or not auth:
        return jsonify({'error': 'Invalid subscription parameters'}), 400

    with get_db() as conn:
        conn.execute("""
            INSERT INTO subscriptions (endpoint, p256dh, auth, goals_json, timezone_offset, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(endpoint) DO UPDATE SET
                p256dh=excluded.p256dh,
                auth=excluded.auth,
                goals_json=excluded.goals_json,
                timezone_offset=excluded.timezone_offset,
                updated_at=CURRENT_TIMESTAMP
        """, (endpoint, p256dh, auth, goals, tz_offset))
        conn.commit()

    print(f"[Subscribe] New device registered for Web Push: {endpoint[:45]}...")
    return jsonify({'status': 'ok', 'message': 'Device successfully subscribed for background push'})

@app.route('/api/sync-reminders', methods=['POST'])
def sync_reminders():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    goals = json.dumps(data.get('goals') or [], ensure_ascii=False)
    tz_offset = data.get('timezoneOffset', 0)

    if not endpoint:
        return jsonify({'error': 'Missing endpoint'}), 400

    with get_db() as conn:
        conn.execute("""
            UPDATE subscriptions 
            SET goals_json = ?, timezone_offset = ?, updated_at = CURRENT_TIMESTAMP
            WHERE endpoint = ?
        """, (goals, tz_offset, endpoint))
        conn.commit()

    return jsonify({'status': 'ok', 'synced': True})

def send_web_push(sub_info, payload):
    try:
        webpush(
            subscription_info=sub_info,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS.copy(),
            ttl=86400
        )
        print(f"[Push Delivered] -> {payload.get('title')}")
        return True
    except WebPushException as ex:
        print(f"[Push Error] {ex}")
        if ex.response is not None and ex.response.status_code in (404, 410):
            # Endpoint is expired or unregistered
            with get_db() as conn:
                conn.execute("DELETE FROM subscriptions WHERE endpoint = ?", (sub_info['endpoint'],))
                conn.commit()
            print(f"[Cleaned] Removed expired endpoint: {sub_info['endpoint'][:45]}")
        return False
    except Exception as e:
        print(f"[Unexpected Push Error] {e}")
        return False

@app.route('/api/test-push', methods=['POST'])
def test_push():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    title = data.get('title', '🔔 Тест фонового push-уведомления!')
    body = data.get('body', 'Уведомление доставлено через Apple APNs! Работает даже при закрытом приложении.')
    delay = int(data.get('delaySeconds', 0))

    if not endpoint:
        return jsonify({'error': 'Missing endpoint'}), 400

    with get_db() as conn:
        row = conn.execute("SELECT * FROM subscriptions WHERE endpoint = ?", (endpoint,)).fetchone()
        if not row:
            return jsonify({'error': 'Subscription not found'}), 404

        sub_info = {
            'endpoint': row['endpoint'],
            'keys': {
                'p256dh': row['p256dh'],
                'auth': row['auth']
            }
        }

    payload = {
        'title': title,
        'body': body,
        'tag': f'test_{int(time.time())}',
        'icon': 'icon-192.png',
        'badge': 'icon-192.png',
        'url': './'
    }

    if delay > 0:
        def delayed_send():
            time.sleep(delay)
            send_web_push(sub_info, payload)
        threading.Thread(target=delayed_send, daemon=True).start()
        return jsonify({'status': 'scheduled', 'delay': delay, 'message': f'Push will arrive in {delay} seconds. Lock your phone now!'})
    else:
        success = send_web_push(sub_info, payload)
        return jsonify({'status': 'sent' if success else 'failed'})

@app.route('/api/ping', methods=['GET'])
@app.route('/healthz', methods=['GET'])
def ping():
    return jsonify({'status': 'ok', 'time': datetime.now(timezone.utc).isoformat()})

# 4. Background Scheduler (Checks deadlines for closed apps 24/7)
def background_scheduler_worker():
    print("[Scheduler] Background Push Notification Worker started.")
    goal_cascade = [
        ('30d', 30 * 86400, '🗓️ До дедлайна 1 месяц!'),
        ('14d', 14 * 86400, '📅 До дедлайна 2 недели!'),
        ('7d',  7  * 86400, '📅 До дедлайна 1 неделя!'),
        ('3d',  3  * 86400, '⚠️ До дедлайна 3 дня!'),
        ('2d',  2  * 86400, '⚠️ До дедлайна 2 дня!'),
        ('1d',  1  * 86400, '🔴 До дедлайна 1 день!'),
        ('8h',  8  * 3600,  '🔴 До дедлайна 8 часов!'),
        ('5h',  5  * 3600,  '🔴 До дедлайна 5 часов!'),
        ('3h',  3  * 3600,  '🔴 До дедлайна 3 часа!'),
        ('1h',  1  * 3600,  '🚨 До дедлайна 1 час!'),
        ('30m', 30 * 60,    '🚨 До дедлайна 30 минут!'),
        ('15m', 15 * 60,    '🚨 До дедлайна 15 минут!'),
    ]

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            with get_db() as conn:
                rows = conn.execute("SELECT * FROM subscriptions").fetchall()

            for row in rows:
                sub_info = {
                    'endpoint': row['endpoint'],
                    'keys': {'p256dh': row['p256dh'], 'auth': row['auth']}
                }
                goals = json.loads(row['goals_json'] or '[]')
                notified_keys = set(json.loads(row['notified_keys'] or '[]'))
                tz_offset_mins = row['timezone_offset'] or 0
                device_now = now_utc - timedelta(minutes=tz_offset_mins)
                today_str = device_now.strftime('%Y-%m-%d')
                current_total_mins = device_now.hour * 60 + device_now.minute
                keys_updated = False

                for goal in goals:
                    if goal.get('completed') or goal.get('failed'):
                        continue

                    g_id = goal.get('id', '')
                    g_type = goal.get('type', 'goal')
                    title = goal.get('title', '')
                    deadline_str = goal.get('deadline')

                    # 1. Standard Goal Cascade
                    if g_type == 'goal' and deadline_str:
                        try:
                            # Parse ISO deadline
                            dl_clean = deadline_str.replace('Z', '+00:00')
                            dl_dt = datetime.fromisoformat(dl_clean)
                            if dl_dt.tzinfo is None:
                                dl_dt = dl_dt.replace(tzinfo=timezone.utc)
                            diff_sec = (dl_dt - now_utc).total_seconds()

                            # First reminder window filter
                            first_rem = goal.get('firstReminder', '30d')
                            first_rem_map = {
                                '30d': 30*86400, '14d': 14*86400, '7d': 7*86400, '3d': 3*86400,
                                '2d': 2*86400, '1d': 86400, '8h': 8*3600, '5h': 5*3600,
                                '3h': 3*3600, '1h': 3600, '30m': 1800, '15m': 900
                            }
                            max_window = first_rem_map.get(first_rem, 30*86400)

                            for key, threshold_sec, label in goalCascade:
                                if threshold_sec > max_window:
                                    continue
                                notif_key = f"goal_{g_id}_{key}"
                                if diff_sec <= threshold_sec and diff_sec > 0 and notif_key not in notified_keys:
                                    notified_keys.add(notif_key)
                                    keys_updated = True
                                    send_web_push(sub_info, {
                                        'title': label,
                                        'body': f"Цель «{title}»: {label} Не откладывай! 🎯",
                                        'tag': notif_key,
                                        'url': './'
                                    })
                                    break
                        except Exception as e:
                            pass

                    # 2. Routine Daily / Mandatory Reminders
                    elif g_type == 'routine':
                        sched_time = goal.get('scheduledTime', '18:00')
                        rem_mins = int(goal.get('reminderMinutes', 60))
                        completions = goal.get('completions') or {}
                        done_today = completions.get(today_str, 0)
                        target_today = int(goal.get('timesPerDay', 1))

                        if done_today < target_today:
                            try:
                                s_hour, s_min = map(int, sched_time.split(':'))
                                sched_mins = s_hour * 60 + s_min

                                # Normal reminder
                                norm_at = sched_mins - rem_mins
                                norm_key = f"routine_norm_{g_id}_{today_str}_{norm_at}"
                                if current_total_mins >= norm_at and current_total_mins < norm_at + 2 and norm_key not in notified_keys:
                                    notified_keys.add(norm_key)
                                    keys_updated = True
                                    send_web_push(sub_info, {
                                        'title': f"📋 Напоминание: {title}",
                                        'body': f"Запланировано на {sched_time}. Выполнено {done_today}/{target_today} раз.",
                                        'tag': norm_key,
                                        'url': './'
                                    })

                                # Exact time reminder
                                exact_key = f"routine_exact_{g_id}_{today_str}_{sched_mins}"
                                if current_total_mins >= sched_mins and current_total_mins < sched_mins + 2 and exact_key not in notified_keys:
                                    notified_keys.add(exact_key)
                                    keys_updated = True
                                    send_web_push(sub_info, {
                                        'title': f"⏰ Пора! {title}",
                                        'body': f"Наступило запланированное время {sched_time}! Не забудьте отметить выполнение.",
                                        'tag': exact_key,
                                        'url': './'
                                    })
                            except Exception as e:
                                pass

                    # 3. Challenge Evening Check-in
                    elif g_type == 'challenge':
                        ch_key = f"ch_evening_{g_id}_{today_str}"
                        if current_total_mins >= 21 * 60 and current_total_mins < 21 * 60 + 2 and ch_key not in notified_keys:
                            notified_keys.add(ch_key)
                            keys_updated = True
                            send_web_push(sub_info, {
                                'title': "🌙 Испытание держится!",
                                'body': f"«{title}»: Ещё один день без срыва! Завтра продолжаем стрик! 🔥",
                                'tag': ch_key,
                                'url': './'
                            })

                if keys_updated:
                    with get_db() as conn:
                        conn.execute("UPDATE subscriptions SET notified_keys = ? WHERE endpoint = ?", 
                                     (json.dumps(list(notified_keys)), row['endpoint']))
                        conn.commit()

        except Exception as e:
            print(f"[Scheduler Error] {e}")

        time.sleep(25)

scheduler_thread = threading.Thread(target=background_scheduler_worker, daemon=True)
scheduler_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[FocusGoals Server] Running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
