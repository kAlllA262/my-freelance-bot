import time
import requests
import feedparser
import json
import os
import re
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Простой переводчик без внешних библиотек
def translate_to_russian(text):
    return text
    
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

    def log_message(self, format, *args):
        return


def run_web_server():
    HTTPServer(("0.0.0.0", PORT), HealthCheckServer).serve_forever()


def telegram_api(method, payload):
    if not BOT_TOKEN:
        print("DEBUG: BOT_TOKEN not set")
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload,
            timeout=20
        )
        if r.status_code != 200:
            print(f"DEBUG: Telegram API error {method}: {r.status_code} {r.text}")
            return None
        return r.json()
    except Exception as e:
        print(f"DEBUG: Telegram API exception {method}: {e}")
        return None


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
        print(f"DEBUG: load_config error: {e}")
    return None


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"DEBUG: save_config error: {e}")
        return False


def ensure_config_exists():
    c = load_config()
    if not c:
        c = get_default_config()
        save_config(c)
    return c


def clean_html_text(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_telegram_message(text, reply_markup=None):
    if not BOT_TOKEN or not CHAT_ID:
        print("DEBUG: BOT_TOKEN or CHAT_ID missing")
        return None

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    return telegram_api("sendMessage", payload)


def send_telegram_message_with_button(text, button_text, button_url):
    if not BOT_TOKEN or not CHAT_ID:
        print("DEBUG: BOT_TOKEN or CHAT_ID missing")
        return None

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": button_text, "url": button_url.strip()}]
            ]
        }
    }
    return telegram_api("sendMessage", payload)


def create_main_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⚙️ Настройки", "callback_data": "open_settings"},
                {"text": "📊 Статус бота", "callback_data": "bot_status"}
            ],
            [
                {"text": "❓ Help", "callback_data": "bot_help"},
                {"text": "🔄 Перезапуск", "callback_data": "bot_restart"}
            ]
        ]
    }


def create_settings_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Бюджет", "callback_data": "open_budget"},
                {"text": "🔍 Ключевые слова", "callback_data": "open_keywords"}
            ],
            [
                {"text": "📁 Freelancehunt", "callback_data": "show_fh_categories"}
            ],
            [
                {"text": "📁 Kabanchik", "callback_data": "show_kb_categories"}
            ],
            [
                {"text": "🔄 Сброс", "callback_data": "reset_config"},
                {"text": "❌ Закрыть", "callback_data": "close_settings"}
            ]
        ]
    }


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


def get_settings_text(config):
    text = "⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n📁 <b>FREELANCEHUNT КАТЕГОРИИ:</b>\n"
    for cat, enabled in config["freelancehunt"]["categories"].items():
        text += f"{'✅' if enabled else '❌'} {cat}\n"

    text += f"\n💰 <b>МИНИМАЛЬНЫЙ БЮДЖЕТ:</b> ${config['freelancehunt']['min_budget']}\n\n🔍 <b>КЛЮЧЕВЫЕ СЛОВА:</b>\n"
    text += ", ".join(config["freelancehunt"]["keywords"])
    text += "\n\n📁 <b>KABANCHIK КАТЕГОРИИ:</b>\n"

    for cat, enabled in config["kabanchik"]["categories"].items():
        text += f"{'✅' if enabled else '❌'} {cat}\n"

    return text


def extract_budget_and_currency(text):
    if not text:
        return None, ""
    patterns = [
        r'(\d[\d\s]*)\s*(₴|грн|uah|usd|\$|€|eur)',
        r'(₴|грн|uah|usd|\$|€|eur)\s*(\d[\d\s]*)'
    ]
    low = text.lower()
    for p in patterns:
        m = re.search(p, low, re.IGNORECASE)
        if m:
            if m.group(1).replace(" ", "").isdigit():
                amount = int(m.group(1).replace(" ", ""))
                currency = m.group(2)
            else:
                amount = int(m.group(2).replace(" ", ""))
                currency = m.group(1)
            return amount, currency.upper()
    m = re.search(r'(\d[\d\s]*)', text)
    if m:
        try:
            return int(m.group(1).replace(" ", "")), ""
        except:
            return None, ""
    return None, ""

def is_russian_or_ukrainian(text):
    if not text:
        return True
    low = text.lower()
    ru_ua_chars = "абвгдеёжзиіїєґклмнопрстуфхцчшщьыэюя"
    return any(ch in low for ch in ru_ua_chars)


def maybe_translate(text):
    if not text:
        return text, False
    if is_russian_or_ukrainian(text):
        return text, False
    translated = translate_to_russian(text)
    return translated, True


def matches_keywords(text, keywords):
    if not text:
        return False
    low = text.lower()
    return any(kw.lower() in low for kw in keywords)


def detect_fh_category(text):
    text_low = text.lower()
    category_map = {
        "Аудио/видео монтаж": ["монтаж", "видеомонтаж", "нарезка", "склейка", "редактирование видео"],
        "AI создание видео": ["ai", "нейросеть", "генерация видео", "создать видео ии", "sora", "midjourney"],
        "Видео реклама": ["реклама", "рекламный ролик", "promo", "promotional", "reels", "ads"],
        "Обработка видео": ["обработка видео", "цветокор", "post production", "color correction"],
        "Обработка фото": ["фото", "ретушь", "обработка фото", "photoshop"],
        "Анимация": ["анимация", "motion", "2d", "3d", "after effects", "moho"]
    }

    for category, words in category_map.items():
        if any(word in text_low for word in words):
            return category

    return "Без категории"


def format_freelancehunt_message(title, summary, category, budget=None, currency=""):
    budget_text = "Не указана"
    if budget is not None:
        budget_text = f"{budget} {currency}".strip()

    title, title_translated = maybe_translate(title)
    summary, summary_translated = maybe_translate(summary)

    title_line = clean_html_text(title)
    if title_translated:
        title_line += " <i>(переведен)</i>"

    summary_line = clean_html_text(summary[:900])
    if summary_translated:
        summary_line += "\n\n<i>(переведен)</i>"

    return (
        f"🟡 <b>Freelancehunt</b>\n\n"
        f"{title_line}\n\n"
        f"🏷 Категория\n{clean_html_text(category)}\n\n"
        f"💰 {clean_html_text(budget_text)}\n\n"
        f"📝 Описание\n{summary_line}"
    )


def format_kabanchik_message(title, category, description="Описание на сайте Kabanchik", budget=None, currency=""):
    budget_text = "Не указана"
    if budget is not None:
        budget_text = f"{budget} {currency}".strip()

    title, title_translated = maybe_translate(title)
    description, description_translated = maybe_translate(description)

    title_line = clean_html_text(title)
    if title_translated:
        title_line += " <i>(переведен)</i>"

    description_line = clean_html_text(description)
    if description_translated:
        description_line += "\n\n<i>(переведен)</i>"

    return (
        f"🟢 <b>Kabanchik</b>\n\n"
        f"{title_line}\n\n"
        f"🏷 Категория\n{clean_html_text(category)}\n\n"
        f"💰 {clean_html_text(budget_text)}\n\n"
        f"📝 Описание\n{description_line}"
    )


def setup_bot_menu():
    telegram_api("setChatMenuButton", {
        "menu_button": {
            "type": "commands"
        }
    })


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
            budget, currency = extract_budget_and_currency(text_for_filter)

            if min_budget and budget is not None and budget < min_budget:
                continue

            if enabled_keywords and not matches_keywords(text_for_filter, enabled_keywords):
                continue

            category = detect_fh_category(text_for_filter)
            fh_sent_projects.add(project_id)

            send_telegram_message_with_button(
                format_freelancehunt_message(title, summary, category, budget, currency),
                "🔗 Открыть проект",
                link
            )
    except Exception as e:
        print(f"DEBUG: parse_freelancehunt error: {e}")


def parse_kabanchik():
    config = ensure_config_exists()

    try:
        for url in KABANCHIK_URLS:
            response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = a.get_text(" ", strip=True)

                if not title or len(title) < 5:
                    continue

                if "project" not in href and "task" not in href:
                    continue

                full_link = href if href.startswith("http") else f"https://kabanchik.ua{href}"

                if full_link in kabanchik_sent_tasks:
                    continue

                text_for_filter = title.lower()
                if config["freelancehunt"]["keywords"] and not matches_keywords(text_for_filter, config["freelancehunt"]["keywords"]):
                    continue

                if "ai-poslugi" in url:
                    category = "AI услуги"
                elif "foto-i-video-posluhy" in url:
                    category = "Фото и видео услуги"
                elif "roboty-v-interneti" in url:
                    category = "Работы в интернете"
                else:
                    category = "Без категории"

                kabanchik_sent_tasks.add(full_link)

                send_telegram_message_with_button(
                    format_kabanchik_message(title, category, "Описание на сайте Kabanchik", None, ""),
                    "🔗 Открыть задачу",
                    full_link
                )
    except Exception as e:
        print(f"DEBUG: parse_kabanchik error: {e}")


def handle_updates():
    offset = 0
    print("DEBUG: Поток handle_updates запущен!")
    while True:
        try:
            print("DEBUG: Проверка обновлений в Telegram...")
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30",
                timeout=40
            )

            if r.status_code != 200:
                print(f"DEBUG: Ошибка Telegram API getUpdates: {r.status_code} {r.text}")
                time.sleep(5)
                continue

            updates = r.json().get("result", [])

            for u in updates:
                offset = max(offset, u["update_id"] + 1)
                print(f"DEBUG: Получено обновление: {u}")

                if "message" in u:
                    message = u["message"]
                    text = message.get("text", "").strip()

                    if text == "/start":
                        send_telegram_message("Меню:", create_main_keyboard())

                    elif text == "/settings":
                        config = ensure_config_exists()
                        send_telegram_message(get_settings_text(config), create_settings_keyboard())

                    elif text == "/help":
                        send_telegram_message(
                            "📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n"
                            "⚙️ Настройки\n"
                            "📊 Статус бота\n"
                            "❓ Help\n"
                            "🔄 Перезапуск",
                            create_main_keyboard()
                        )

                    elif text == "/status":
                        config = ensure_config_exists()
                        send_telegram_message(
                            f"✅ <b>БОТ РАБОТАЕТ</b>\n\n"
                            f"💰 Бюджет: ${config['freelancehunt']['min_budget']}\n"
                            f"🔍 Ключевые слова: {', '.join(config['freelancehunt']['keywords'])}",
                            create_main_keyboard()
                        )

                elif "callback_query" in u:
                    cb = u["callback_query"]
                    data = cb["data"]
                    cid = cb["id"]
                    config = ensure_config_exists()

                    if data == "open_settings":
                        send_telegram_message(get_settings_text(config), create_settings_keyboard())

                    elif data == "open_budget":
                        send_telegram_message("💰 <b>Выберите минимальный бюджет:</b>", create_budget_keyboard())

                    elif data == "open_keywords":
                        send_telegram_message("🔍 <b>Выберите ключевое слово:</b>", create_keywords_keyboard())

                    elif data == "back_to_settings":
                        send_telegram_message(get_settings_text(config), create_settings_keyboard())

                    elif data == "show_fh_categories":
                        text = "📁 <b>Freelancehunt категории:</b>\n\n"
                        for cat, enabled in config["freelancehunt"]["categories"].items():
                            text += f"{'✅' if enabled else '❌'} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard())

                    elif data == "show_kb_categories":
                        text = "📁 <b>Kabanchik категории:</b>\n\n"
                        for cat, enabled in config["kabanchik"]["categories"].items():
                            text += f"{'✅' if enabled else '❌'} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard())

                    elif data.startswith("budget_"):
                        budget = int(data.replace("budget_", ""))
                        config["freelancehunt"]["min_budget"] = budget
                        save_config(config)
                        send_telegram_message(
                            f"✅ Минимальный бюджет установлен: ${budget}",
                            create_settings_keyboard()
                        )

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
                            send_telegram_message(msg, create_settings_keyboard())

                    elif data == "reset_config":
                        config = get_default_config()
                        save_config(config)
                        send_telegram_message("🔄 Настройки сброшены", create_settings_keyboard())

                    elif data == "bot_status":
                        send_telegram_message(
                            f"✅ <b>БОТ РАБОТАЕТ</b>\n\n"
                            f"💰 Бюджет: ${config['freelancehunt']['min_budget']}\n"
                            f"🔍 Ключевые слова: {', '.join(config['freelancehunt']['keywords'])}",
                            create_main_keyboard()
                        )

                    elif data == "bot_help":
                        send_telegram_message(
                            "📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n"
                            "⚙️ Настройки\n"
                            "📊 Статус бота\n"
                            "❓ Help\n"
                            "🔄 Перезапуск",
                            create_main_keyboard()
                        )

                    elif data == "bot_restart":
                        send_telegram_message("🔄 Перезапуск...", create_main_keyboard())
                        os._exit(0)

                    elif data == "close_settings":
                        chat_id = cb["message"]["chat"]["id"]
                        message_id = cb["message"]["message_id"]
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "Меню закрыто"
                        })

        except Exception as e:
            print(f"DEBUG: Ошибка в handle_updates: {e}")
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
    print("Бот запускается...")
    if not BOT_TOKEN or not CHAT_ID:
        print("DEBUG: BOT_TOKEN или CHAT_ID не заданы")
        return

    ensure_config_exists()
    setup_bot_menu()

    Thread(target=run_web_server, daemon=True).start()
    Thread(target=monitor_freelancehunt, daemon=True).start()
    Thread(target=monitor_kabanchik, daemon=True).start()
    Thread(target=handle_updates, daemon=True).start()

    print("Все потоки запущены. Ожидание...")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
