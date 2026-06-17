import time, requests, feedparser, json, os, re
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

FH_RSS_URL = "https://freelancehunt.com/projects.rss?skills%5B%5D=113&skills%5B%5D=192&skills%5B%5D=144&skills%5B%5D=101&skills%5B%5D=18&skills%5B%5D=91"
FH_INTERVAL = 60
KABANCHIK_URLS = [
    "https://kabanchik.ua/projects/category/ai-poslugi",
    "https://kabanchik.ua/projects/category/foto-i-video-posluhy",
    "https://kabanchik.ua/projects/category/roboty-v-interneti",
]
KABANCHIK_INTERVAL = 30
CONFIG_FILE = "config.json"
fh_sent_projects = set()
kabanchik_sent_tasks = set()

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running")
    def log_message(self, format, *args): return

def run_web_server(): 
    HTTPServer(("0.0.0.0", PORT), HealthCheckServer).serve_forever()

def telegram_api(method, payload):
    if not BOT_TOKEN: return None
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"Ошибка API {method}: {e}")
        return None

def get_default_config():
    return {"freelancehunt":{"categories":{"Аудио/видео монтаж":True,"AI создание видео":True,"Видео реклама":True,"Обработка видео":True,"Обработка фото":True,"Анимация":True},"min_budget":0,"keywords":["видео","монтаж","AI","анимация","реклама"]},"kabanchik":{"categories":{"AI услуги":True,"Фото и видео услуги":True,"Работы в интернете":True}}}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return None

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config, f, ensure_ascii=False, indent=2)
    except: pass

def ensure_config_exists():
    c = load_config()
    if not c: c = get_default_config(); save_config(c)
    return c

def send_telegram_message(text, reply_markup=None):
    if not BOT_TOKEN or not CHAT_ID: return None
    p = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup: p["reply_markup"] = reply_markup
    return telegram_api("sendMessage", p)

def create_main_keyboard():
    return {"inline_keyboard":[[{"text":"⚙️ Настройки","callback_data":"open_settings"},{"text":"📊 Статус бота","callback_data":"bot_status"}],[{"text":"❓ Help","callback_data":"bot_help"},{"text":"🔄 Перезапуск","callback_data":"bot_restart"}]]}

def create_settings_keyboard():
    return {"inline_keyboard":[[{"text":"💰 Бюджет","callback_data":"open_budget"},{"text":"🔍 Ключевые слова","callback_data":"open_keywords"}],[{"text":"❌ Закрыть","callback_data":"close_settings"}]]}

def handle_updates():
    offset = 0
    print("DEBUG: Поток handle_updates запущен!")
    while True:
        try:
            print("DEBUG: Проверка обновлений в Telegram...")
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30", timeout=40)
            if r.status_code != 200:
                print(f"DEBUG: Ошибка подключения к Telegram: {r.status_code}")
                time.sleep(10)
                continue
                
            updates = r.json().get("result", [])
            for u in updates:
                offset = max(offset, u["update_id"] + 1)
                print(f"DEBUG: Получено обновление: {u}")
                
                if "message" in u:
                    if u["message"].get("text") == "/start": 
                        send_telegram_message("Меню:", create_main_keyboard())
                elif "callback_query" in u:
                    cb = u["callback_query"]; data = cb["data"]; cid = cb["id"]; c = ensure_config_exists()
                    if data == "open_settings": send_telegram_message(" ", create_settings_keyboard())
                    elif data == "close_settings":
                        telegram_api("deleteMessage", {"chat_id": cb["message"]["chat"]["id"], "message_id": cb["message"]["message_id"]})
                        telegram_api("answerCallbackQuery", {"callback_query_id": cid, "text": "Меню закрыто"})
        except Exception as e:
            print(f"DEBUG: Ошибка в handle_updates: {e}")
            time.sleep(5)

def monitor_freelancehunt():
    while True: 
        # (функция парсинга)
        time.sleep(FH_INTERVAL)

def monitor_kabanchik():
    while True: 
        # (функция парсинга)
        time.sleep(KABANCHIK_INTERVAL)

def main():
    print("Бот запускается...")
    ensure_config_exists()
    
    Thread(target=run_web_server, daemon=True).start()
    Thread(target=monitor_freelancehunt, daemon=True).start()
    Thread(target=monitor_kabanchik, daemon=True).start()
    Thread(target=handle_updates, daemon=True).start()
    
    print("Все потоки запущены. Ожидание...")
    while True: time.sleep(60)

if __name__ == "__main__": main()
