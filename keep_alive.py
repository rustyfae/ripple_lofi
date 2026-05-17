"""
keep_alive.py — Optional tiny web server for uptime monitoring services.
Only needed if your host requires an HTTP ping to keep running (e.g. Render free tier).
NOT needed for local, Raspberry Pi, or paid hosting.

Usage: import keep_alive; keep_alive.keep_alive() at the top of bot.py (optional).
"""

from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "🎵 Lofi bot is alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("[keep_alive] Web server running on port 8080")
