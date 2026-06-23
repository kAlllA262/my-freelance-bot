import time
import requests
import json
import os
import re
import sys
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

KABANCHIK_EMAIL = os.environ.get("KABANCHIK_EMAIL")
KABANCHIK_PASSWORD = os.environ.get("KABANCHIK_PASSWORD")

# ВАШИ ССЫЛКИ
KABANCHIK_URLS = [
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/ai-poslugi",
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/dyzain",
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/foto-i-video-posluhy"
]

kabanchik_session = None
kabanchik_sent = set()
stats = {"orders": 0}

def telegram_api(method, payload):
    if not BOT_TOKEN:
        return None
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=20)
        return r.json()
    except:
        return None

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    telegram_api("sendMessage", payload)

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web_server():
    HTTPServer(("0.0.0.0", PORT), HealthCheckServer).serve_forever()

def login_to_kabanchik():
    global kabanchik_session
    try:
        if not KABANCHIK_EMAIL or not KABANCHIK_PASSWORD:
            print("❌ Нет данных для входа")
            return False
        
        print("🔐 Вход на Kabanchik...")
        kabanchik_session = requests.Session()
        kabanchik_session.headers.update({"User-Agent": "Mozilla/5.0"})
        
        # Получаем CSRF токен
        response = kabanchik_session.get("https://kabanchik.ua/ua/login", timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "_token"})
        csrf = token.get("value") if token else ""
        
        # Вход
        data = {"email": KABANCHIK_EMAIL, "password": KABANCHIK_PASSWORD, "_token": csrf, "remember": "1"}
        response = kabanchik_session.post("https://kabanchik.ua/ua/login", data=data, timeout=30, allow_redirects=True)
        
        if "вход" in response.text.lower() or "login" in response.url.lower():
            print("❌ Вход не удался")
            return False
        
        print("✅ Вход выполнен")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def parse_kabanchik():
    global kabanchik_session, kabanchik_sent
    print("🔍 Парсинг Kabanchik...")
    
    if not kabanchik_session:
        if not login_to_kabanchik():
            return
    
    for url in KABANCHIK_URLS:
        try:
            print(f"📂 URL: {url}")
            response = kabanchik_session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"❌ Ошибка: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("div", class_="project-item") or soup.find_all("div", class_="order-item")
            
            for item in items:
                title_elem = item.find("a", class_="title") or item.find("h3") or item.find("h2")
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else title_elem.find("a")
                link = "https://kabanchik.ua" + link_elem.get("href") if link_elem and link_elem.get("href") else ""
                
                if not link or link in kabanchik_sent:
                    continue
                
                kabanchik_sent.add(link)
                stats["orders"] += 1
                
                msg = f"🟢 <b>Kabanchik</b>\n\n📌 <b>{title}</b>\n\n🔗 {link}"
                send_telegram(msg)
                print(f"✅ {title[:50]}...")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def monitor():
    while True:
        parse_kabanchik()
        time.sleep(60)

def main():
    print("🚀 Бот запущен")
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Нет BOT_TOKEN или CHAT_ID")
        sys.exit(1)
    
    login_to_kabanchik()
    
    threads = [
        Thread(target=run_web_server, daemon=True),
        Thread(target=monitor, daemon=True)
    ]
    for t in threads:
        t.start()
    
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
