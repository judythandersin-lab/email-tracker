from flask import Flask, request, send_file, jsonify
from datetime import datetime, timedelta
from urllib.parse import unquote
import os
import smtplib
from email.message import EmailMessage
from threading import Lock

app = Flask(__name__)
LOG_FILE = "opens.log"
SENDERS_FILE = "senders.txt"
OPEN_CACHE = {}
CACHE_TIMEOUT = timedelta(minutes=5)
lock = Lock()

# --- Load sender credentials ---
def load_senders():
    senders = {}
    if not os.path.exists(SENDERS_FILE):
        return senders
    with open(SENDERS_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) == 3:
                email, name, password = parts
                senders[email] = {'name': name, 'pass': password}
    return senders

# --- Send alert email to sender ---
def send_open_notification(from_email, sender_name, sender_pass, opened_by, subject, ip, ua):
    msg = EmailMessage()
    msg['Subject'] = f"📬 Email Opened by {opened_by} | {subject}"
    msg['From'] = f"{sender_name} <{from_email}>"
    msg['To'] = from_email
    msg.set_content(f"""
    Open Tracking Notification:

    Recipient: {opened_by}
    Subject: {subject}
    IP Address: {ip}
    User-Agent: {ua}
    Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Sent by: {sender_name} <{from_email}>
    """)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(from_email, sender_pass)
            smtp.send_message(msg)
        print(f"📨 Alert sent to {from_email}")
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")

# --- Track open ---
@app.route('/track/<sender>/<email_id>/<subject>.png')
def track_open(sender, email_id, subject):
    sender = unquote(sender)
    email_id = unquote(email_id)
    subject = unquote(subject)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent', '')
    now = datetime.now()

    # Duplicate prevention
    key = (sender, email_id, subject, ip)
    with lock:
        if key in OPEN_CACHE and now - OPEN_CACHE[key] < CACHE_TIMEOUT:
            return send_file('pixel.png', mimetype='image/png')
        OPEN_CACHE[key] = now

    log_entry = f"[{now}] Opened by {email_id} | Subject: {subject} | IP: {ip} | UA: {ua} | Sender: {sender}\n"
    print(log_entry.strip())

    with open(LOG_FILE, "a") as log:
        log.write(log_entry)

    senders = load_senders()
    if sender in senders:
        send_open_notification(sender, senders[sender]['name'], senders[sender]['pass'], email_id, subject, ip, ua)
    else:
        print(f"⚠️ Unknown sender: {sender}")

    return send_file('pixel.png', mimetype='image/png')

# --- View logs dashboard ---
@app.route('/logs')
def view_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()[-100:]  # last 100
    entries = [line.strip() for line in lines]
    return jsonify(entries)

# --- Generate tracking pixel if missing ---
if __name__ == '__main__':
    if not os.path.exists('pixel.png'):
        from PIL import Image
        img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))
        img.save('pixel.png')
    app.run(host="0.0.0.0", port=5000)
