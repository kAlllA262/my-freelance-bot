import time
import requests
import feedparser
import json
import os
import re
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
        {"text": "💰 Бюджет", "callback_data": "open_budget"},
        {"text": "🔍 Ключевые слова", "callback_data": "open_keywords"}
    ])

    keyboard["inline_keyboard"].append([
        {"text": "📁 Freelancehunt", "callback_data": "show_fh_categories"}
    ])

    keyboard["inline_keyboard"].append([
        {"text": "📁 Kabanchik", "callback_data": "show_kb_categories"}
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
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN или CHAT_ID не заданы")
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            print(f"Ошибка Telegram API: {response.text}")
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None


def send_telegram_message_with_button(text, button_text, button_url):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN или CHAT_ID не заданы")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    reply_markup = {
        "inline_keyboard": [[
            {"text": button_text, "url": button_url.strip()}
        ]]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            print(f"Ошибка Telegram API: {response.text}")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")


def send_telegram_message_with_two_buttons(text, b1_text, b1_url, b2_text, b2_url):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN или CHAT_ID не заданы")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    reply_markup = {
        "inline_keyboard": [[
            {"text": b1_text, "url": b1_url.strip()},
            {"text": b2_text, "url": b2_url.strip()}
        ]]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            print(f"Ошибка Telegram API: {response.text}")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")


def extract_budget(text):
    if not text:
        return 0
    match = re.search(r'(\d[\d\s]*)', text.replace(",", ""))
    if match:
        try:
            return int(match.group(1).replace(" ", ""))
        except:
            return 0
    return 0


def matches_keywords(text, keywords):
    if not text:
        return False
    low = text.lower()
    for kw in keywords:
        if kw.lower() in low:
            return True
    return False


def parse_freelancehunt():
    config = ensure_config_exists()
    enabled_keywords = config["freelancehunt"]["keywords"]
    min_budget = config["freelancehunt"]["min_budget"]

    try:
        feed = feedparser.parse(FH_RSS_URL)
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")
            project_id = link or title

            if project_id in fh_sent_projects:
                continue

            text_for_filter = f"{title} {summary}"
            budget = extract_budget(text_for_filter)

            if min_budget and budget < min_budget:
                continue

            if enabled_keywords and not matches_keywords(text_for_filter, enabled_keywords):
                continue

            fh_sent_projects.add(project_id)

            msg = (
                f"🟢 <b>Freelancehunt</b>\n"
                f"📌 <b>{clean_html_text(title)}</b>\n\n"
                f"{clean_html_text(summary[:700])}"
            )
            send_telegram_message_with_button(msg, "🔗 Открыть проект", link)

    except Exception as e:
        print(f"Ошибка парсинга Freelancehunt: {e}")


def parse_kabanchik():
    config = ensure_config_exists()

    try:
        for url in KABANCHIK_URLS:
            response = requests.get(url, timeout=20, headers={
                "User-Agent": "Mozilla/5.0"
            })
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            links = soup.find_all("a", href=True)
            for a in links:
                href = a["href"]
                title = a.get_text(" ", strip=True)

                if not title or len(title) < 5:
                    continue

                if "project" not in href and "task" not in href:
                    continue

                full_link = href if href.startswith("http") else f"https://kabanchik.ua{href}"
                task_id = full_link

                if task_id in kabanchik_sent_tasks:
                    continue

                text_for_filter = title.lower()
                if config["freelancehunt"]["keywords"]:
                    if not matches_keywords(text_for_filter, config["freelancehunt"]["keywords"]):
                        continue

                kabanchik_sent_tasks.add(task_id)

                msg = (
                    f"🟠 <b>Kabanchik</b>\n"
                    f"📌 <b>{clean_html_text(title)}</b>"
                )
                send_telegram_message_with_button(msg, "🔗 Открыть задачу", full_link)

    except Exception as e:
        print(f"Ошибка парсинга Kabanchik: {e}")


def handle_updates():
    offset = 0
    config = ensure_config_exists()

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=40)
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

/settings - Открыть настройки
/help - Эта справка
/status - Статус бота

<b>В меню:</b>
- Бюджет
- Ключевые слова
- Категории
- Сброс
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


def monitor_freelancehunt():
    while True:
        parse_freelancehunt()
        time.sleep(FH_INTERVAL)


def monitor_kabanchik():
    while True:
        parse_kabanchik()
        time.sleep(KABANCHIK_INTERVAL)


def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN или CHAT_ID не заданы в переменных окружения")
        return

    ensure_config_exists()
    print("Бот запущен")

    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()

    fh_thread = Thread(target=monitor_freelancehunt, daemon=True)
    kb_thread = Thread(target=monitor_kabanchik, daemon=True)
    updates_thread = Thread(target=handle_updates, daemon=True)

    fh_thread.start()
    kb_thread.start()
    updates_thread.start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
