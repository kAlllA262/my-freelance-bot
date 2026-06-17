import time
import requests
import feedparser
import json
import os
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

FH_RSS_URL = "https://freelancehunt.com/projects.rss?skills%5B%5D=113&skills%5B%5D=192&skills%5B%5D=144&skills%5B%5D=101&skills%5B%5D=18&skills%5B%5D=91"
FH_INTERVAL = 60

KABANCHIK_URLS = [
    "https://kabanchik.ua/projects/category/ai-poslugi",
    "https://kabanchik.ua/projects/category/foto-i-video-posluhy",
    "https://kabanchik.ua/projects/category/roboty-v-interneti",
]
KABANCHIK_INTERVAL = 30

CONFIG_FILE = "config.json"
# ====================================================


class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Combo Multi-Category Bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):
        return


def run_web_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthCheckServer)
    server.serve_forever()


fh_sent_projects = set()
kabanchik_sent_tasks = set()


def get_default_config():
    return {
        "freelancehunt": {
            "categories": {
                "Аудио/видео монтаж": True,
                "AI создание видео": True,
                "Видео реклама": True,
                "Обработка видео": True,
                "Обработка фото": True,
                "Анимация": True
            },
            "min_budget": 0,
            "keywords": ["видео", "монтаж", "AI", "анимация", "реклама"]
        },
        "kabanchik": {
            "categories": {
                "AI услуги": True,
                "Фото и видео услуги": True,
                "Работы в интернете": True
            }
        }
    }


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки конфига: {e}")
    return None


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")
        return False


def ensure_config_exists():
    config = load_config()
    if not config:
        config = get_default_config()
        save_config(config)
    return config


def get_settings_text(config):
    text = "⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n"

    text += "📁 <b>FREELANCEHUNT КАТЕГОРИИ:</b>\n"
    for cat, enabled in config["freelancehunt"]["categories"].items():
        status = "✅" if enabled else "❌"
        text += f"{status} {cat}\n"

    text += f"\n💰 <b>МИНИМАЛЬНЫЙ БЮДЖЕТ:</b> ${config['freelancehunt']['min_budget']}\n"

    text += "\n🔍 <b>КЛЮЧЕВЫЕ СЛОВА:</b>\n"
    text += ", ".join(config["freelancehunt"]["keywords"]) + "\n"

    text += "\n📁 <b>KABANCHIK КАТЕГОРИИ:</b>\n"
    for cat, enabled in config["kabanchik"]["categories"].items():
        status = "✅" if enabled else "❌"
        text += f"{status} {cat}\n"

    return text


def create_settings_keyboard(config):
    keyboard = {"inline_keyboard": []}

    keyboard["inline_keyboard"].append([
        {"text": "⚙️ Главное меню", "callback_data": "open_settings"}
    ])

    keyboard["inline_keyboard"].append([
        {"text": "💰 Бюджет", "callback_data": "open_budget"},
        {"text": "🔍 Ключевые слова", "callback_data": "open_keywords"}
    ])

    keyboard["inline_keyboard"].append([
        {"text": "📁 Категории Freelancehunt", "callback_data": "show_fh_categories"}
    ])

    keyboard["inline_keyboard"].append([
        {"text": "📁 Категории Kabanchik", "callback_data": "show_kb_categories"}
    ])

    keyboard["inline_keyboard"].append([
        {"text": "🔄 Сброс", "callback_data": "reset_config"},
        {"text": "❌ Закрыть", "callback_data": "close_settings"}
    ])

    return keyboard


def create_budget_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "$0", "callback_data": "budget_0"},
                {"text": "$50", "callback_data": "budget_50"},
                {"text": "$100", "callback_data": "budget_100"}
            ],
            [
                {"text": "$200", "callback_data": "budget_200"},
                {"text": "$500", "callback_data": "budget_500"}
            ],
            [
                {"text": "⬅️ Назад", "callback_data": "back_to_settings"}
            ]
        ]
    }


def create_keywords_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "Видео", "callback_data": "kw_video"},
                {"text": "Монтаж", "callback_data": "kw_edit"}
            ],
            [
                {"text": "AI", "callback_data": "kw_ai"},
                {"text": "Анимация", "callback_data": "kw_anim"}
            ],
            [
                {"text": "Реклама", "callback_data": "kw_ads"},
                {"text": "Фото", "callback_data": "kw_photo"}
            ],
            [
                {"text": "⬅️ Назад", "callback_data": "back_to_settings"}
            ]
        ]
    }


def clean_html_text(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(url, json=payload)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None


def send_telegram_message_with_two_buttons(text, b1_text, b1_url, b2_text, b2_url):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    b1_url = b1_url.strip()
    b2_url = b2_url.strip()

    reply_markup = {
        "inline_keyboard": [[
            {"text": b1_text, "url": b1_url},
            {"text": b2_text, "url": b2_url}
        ]]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Ошибка Telegram API: {response.text}")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")


def handle_updates():
    offset = 0
    config = ensure_config_exists()

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url)
            updates = response.json().get("result", [])

            for update in updates:
                offset = max(offset, update["update_id"] + 1)

                if "message" in update:
                    message = update["message"]
                    text = message.get("text", "").lower()

                    if text == "/settings":
                        config = ensure_config_exists()
                        settings_text = get_settings_text(config)
                        keyboard = create_settings_keyboard(config)
                        send_telegram_message(settings_text, keyboard)

                    elif text == "/help":
                        help_text = """
📚 <b>ДОСТУПНЫЕ КОМАНДЫ:</b>

/settings - Открыть настройки категорий
/help - Эта справка
/status - Статус бота

<b>В меню настроек:</b>
- Нажимай на категорию чтобы включить/выключить
- 💰 Бюджет - выбрать минимальный бюджет
- 🔍 Ключевые слова - включать/выключать слова
- 🔄 Сброс - вернуть дефолтные настройки
- ❌ Закрыть - закрыть меню
"""
                        send_telegram_message(help_text)

                    elif text == "/status":
                        config = ensure_config_exists()
                        status_text = "✅ <b>БОТ РАБОТАЕТ</b>\n\n"
                        status_text += f"💰 Бюджет: ${config['freelancehunt']['min_budget']}\n"
                        status_text += f"🔍 Ключевые слова: {', '.join(config['freelancehunt']['keywords'])}\n"
                        send_telegram_message(status_text)

                elif "callback_query" in update:
                    callback = update["callback_query"]
                    callback_id = callback["id"]
                    data = callback["data"]

                    config = ensure_config_exists()

                    if data == "open_settings":
                        settings_text = get_settings_text(config)
                        keyboard = create_settings_keyboard(config)
                        send_telegram_message(settings_text, keyboard)

                    elif data == "open_budget":
                        send_telegram_message("💰 <b>Выберите минимальный бюджет:</b>", create_budget_keyboard())

                    elif data == "open_keywords":
                        send_telegram_message("🔍 <b>Выберите ключевое слово:</b>", create_keywords_keyboard())

                    elif data == "back_to_settings":
                        settings_text = get_settings_text(config)
                        keyboard = create_settings_keyboard(config)
                        send_telegram_message(settings_text, keyboard)

                    elif data == "show_fh_categories":
                        text = "📁 <b>Freelancehunt категории:</b>\n\n"
                        for cat, enabled in config["freelancehunt"]["categories"].items():
                            status = "✅" if enabled else "❌"
                            text += f"{status} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard(config))

                    elif data == "show_kb_categories":
                        text = "📁 <b>Kabanchik категории:</b>\n\n"
                        for cat, enabled in config["kabanchik"]["categories"].items():
                            status = "✅" if enabled else "❌"
                            text += f"{status} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard(config))

                    elif data.startswith("budget_"):
                        budget = int(data.replace("budget_", ""))
                        config["freelancehunt"]["min_budget"] = budget
                        save_config(config)
                        send_telegram_message(f"✅ Минимальный бюджет установлен: ${budget}", create_settings_keyboard(config))

                    elif data.startswith("kw_"):
                        keyword_map = {
                            "kw_video": "видео",
                            "kw_edit": "монтаж",
                            "kw_ai": "AI",
                            "kw_anim": "анимация",
                            "kw_ads": "реклама",
                            "kw_photo": "фото"
                        }
                        keyword = keyword_map.get(data)
                        if keyword:
                            keywords = config["freelancehunt"]["keywords"]
                            if keyword in keywords:
                                keywords.remove(keyword)
                                msg = f"❌ Ключевое слово удалено: {keyword}"
                            else:
                                keywords.append(keyword)
                                msg = f"✅ Ключевое слово добавлено: {keyword}"
                            config["freelancehunt"]["keywords"] = keywords
                            save_config(config)
                            send_telegram_message(msg, create_settings_keyboard(config))

                    elif data.startswith("toggle_fh_"):
                        cat_name = data.replace("toggle_fh_", "")
                        if cat_name in config["freelancehunt"]["categories"]:
                            config["freelancehunt"]["categories"][cat_name] = not config["freelancehunt"]["categories"][cat_name]
                            save_config(config)
                            send_telegram_message(f"✅ Freelancehunt: {cat_name} изменено", create_settings_keyboard(config))

                    elif data.startswith("toggle_kb_"):
                        cat_name = data.replace("toggle_kb_", "")
                        if cat_name in config["kabanchik"]["categories"]:
                            config["kabanchik"]["categories"][cat_name] = not config["kabanchik"]["categories"][cat_name]
                            save_config(config)
                            send_telegram_message(f"✅ Kabanchik: {cat_name} изменено", create_settings_keyboard(config))

                    elif data == "reset_config":
                        config = get_default_config()
                        save_config(config)
                        send_telegram_message("🔄 Настройки сброшены", create_settings_keyboard(config))

                    elif data == "close_settings":
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                        requests.post(url, json={"callback_query_id": callback_id, "text": "Меню закрыто"})
                        continue

        except Exception as e:
            print(f"Ошибка в handle_updates: {e}")
            time.sleep(5)


def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN или CHAT_ID не заданы в переменных окружения")
        return

    config = ensure_config_exists()
    print("Бот запущен")
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()

    handle_updates()


if __name__ == "__main__":
    main()
