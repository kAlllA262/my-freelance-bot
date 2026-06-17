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

def run_web_server(): HTTPServer(("0.0.0.0", PORT), HealthCheckServer).serve_forever()

def telegram_api(method, payload):
    if not BOT_TOKEN: return None
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=20)
        return r.json() if r.status_code == 200 else None
    except: return None

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

def send_telegram_message_with_button(text, button_text, button_url):
    telegram_api("sendMessage", {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "reply_markup": {"inline_keyboard": [[{"text": button_text, "url": button_url.strip()}]]}})

def create_main_keyboard():
    return {"inline_keyboard":[[{"text":"⚙️ Настройки","callback_data":"open_settings"},{"text":"📊 Статус бота","callback_data":"bot_status"}],[{"text":"❓ Help","callback_data":"bot_help"},{"text":"🔄 Перезапуск","callback_data":"bot_restart"}]]}

def create_settings_keyboard():
    return {"inline_keyboard":[[{"text":"💰 Бюджет","callback_data":"open_budget"},{"text":"🔍 Ключевые слова","callback_data":"open_keywords"}],[{"text":"📁 Freelancehunt","callback_data":"show_fh_categories"}],[{"text":"📁 Kabanchik","callback_data":"show_kb_categories"}],[{"text":"❌ Закрыть","callback_data":"close_settings"}]]}

def create_budget_keyboard():
    return {"inline_keyboard":[[{"text":"$0","callback_data":"budget_0"},{"text":"$50","callback_data":"budget_50"},{"text":"$100","callback_data":"budget_100"}],[{"text":"⬅️ Назад","callback_data":"back_to_settings"}]]}

def create_keywords_keyboard():
    return {"inline_keyboard":[[{"text":"Видео","callback_data":"kw_video"},{"text":"Монтаж","callback_data":"kw_edit"}],[{"text":"AI","callback_data":"kw_ai"},{"text":"Анимация","callback_data":"kw_anim"}],[{"text":"⬅️ Назад","callback_data":"back_to_settings"}]]}

def get_settings_text(c):
    t="⚙️ <b>НАСТРОЙКИ:</b>\n\n💰 Бюджет: ${}\n🔍 Слова: {}".format(c['freelancehunt']['min_budget'], ", ".join(c["freelancehunt"]["keywords"]))
    return t

def setup_bot_menu(): telegram_api("setChatMenuButton", {"menu_button":{"type":"commands"}})

def handle_updates():
    offset = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30", timeout=40)
            updates = r.json().get("result", [])
            for u in updates:
                offset = max(offset, u["update_id"] + 1)
                if "message" in u:
                    if u["message"].get("text") == "/start": send_telegram_message("Меню:", create_main_keyboard())
                elif "callback_query" in u:
                    cb = u["callback_query"]; data = cb["data"]; cid = cb["id"]; c = ensure_config_exists()
                    
                    # При нажатии кнопок отправляем " " (пробел) вместо текста
                    if data == "open_settings": send_telegram_message(" ", create_settings_keyboard())
                    elif data == "open_budget": send_telegram_message(" ", create_budget_keyboard())
                    elif data == "open_keywords": send_telegram_message(" ", create_keywords_keyboard())
                    elif data == "back_to_settings": send_telegram_message(" ", create_settings_keyboard())
                    
                    elif data == "bot_status": send_telegram_message(f"✅ <b>БОТ РАБОТАЕТ</b>\n\n💰 Бюджет: ${c['freelancehunt']['min_budget']}", create_main_keyboard())
                    elif data == "bot_help": send_telegram_message("📚 <b>Справка:</b>\nНастройки, Статус, Help, Перезапуск", create_main_keyboard())
                    elif data == "bot_restart": os._exit(0)
                    
                    elif data.startswith("budget_"): 
                        c["freelancehunt"]["min_budget"] = int(data.split("_")[1]); save_config(c); send_telegram_message("✅", create_settings_keyboard())
                    elif data.startswith("kw_"):
                        k = {"kw_video":"видео", "kw_edit":"монтаж", "kw_ai":"AI", "kw_anim":"анимация"}[data]
                        kws = c["freelancehunt"]["keywords"]
                        if k in kws: kws.remove(k)
                        else: kws.append(k)
                        c["freelancehunt"]["keywords"] = kws; save_config(c); send_telegram_message(" ", create_keywords_keyboard())
                    
                    elif data == "close_settings":
                        telegram_api("deleteMessage", {"chat_id": cb["message"]["chat"]["id"], "message_id": cb["message"]["message_id"]})
        except: time.sleep(5)

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("Ошибка: BOT_TOKEN или CHAT_ID не заданы!")
        return

    ensure_config_exists()
    setup_bot_menu()
    print("Инициализация потоков...")
    
    # Запускаем фоновые задачи
    try:
        Thread(target=run_web_server, daemon=True).start()
        Thread(target=monitor_freelancehunt, daemon=True).start()
        Thread(target=monitor_kabanchik, daemon=True).start()
        Thread(target=handle_updates, daemon=True).start()
        print("Бот успешно запущен")
    except Exception as e:
        print(f"Ошибка при старте потоков: {e}")

    # Главный цикл
    while True:
        time.sleep(60)


if __name__ == "__main__": main()
