import time
import requests
import feedparser
import json
import os
import re
import sys
import hashlib
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FH_API_TOKEN = os.environ.get("FH_API_TOKEN")

# Данные для авторизации на Kabanchik
KABANCHIK_EMAIL = os.environ.get("KABANCHIK_EMAIL")
KABANCHIK_PASSWORD = os.environ.get("KABANCHIK_PASSWORD")

# Шаблон отклика
template = {
    "price": 500,
    "deadline": 3,
    "style": "Профессиональный",
    "extra_text": "Могу предоставить портфолио по запросу."
}

waiting_for_template_input = False
template_input_type = None

# URL для парсинга Kabanchik
KABANCHIK_BASE_URL = "https://kabanchik.ua"
KABANCHIK_LOGIN_URL = "https://kabanchik.ua/ua/login"
KABANCHIK_CATEGORIES = {
    "ai_services": "ai-poslugi",
    "design": "dyzain",
    "photo_video": "foto-i-video-posluhy"
}
KABANCHIK_PROJECTS_URL = "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category"

FH_CATEGORIES = {
    "ai_video": "https://freelancehunt.com/projects.rss?skills%5B%5D=192",
    "animation": "https://freelancehunt.com/projects.rss?skills%5B%5D=91",
    "video_audio": "https://freelancehunt.com/projects.rss?skills%5B%5D=113",
    "video_ads": "https://freelancehunt.com/projects.rss?skills%5B%5D=144",
    "audio_processing": "https://freelancehunt.com/projects.rss?skills%5B%5D=102",
    "video_processing": "https://freelancehunt.com/projects.rss?skills%5B%5D=101",
    "photo_processing": "https://freelancehunt.com/projects.rss?skills%5B%5D=18",
    "voice_over": "https://freelancehunt.com/projects.rss?skills%5B%5D=143",
}

FH_CATEGORY_NAMES = {
    "ai_video": "AI создание видео",
    "animation": "Анимация",
    "video_audio": "Аудио/видео монтаж",
    "video_ads": "Видео реклама",
    "audio_processing": "Обработка аудио",
    "video_processing": "Обработка видео",
    "photo_processing": "Обработка фото",
    "voice_over": "Услуги диктора"
}

FH_INTERVAL = 60
KABANCHIK_INTERVAL = 60
WEBLANCER_INTERVAL = 60

WEBLANCER_URL = "https://www.weblancer.net/projects/"
WEBLANCER_KEYWORDS = [
    "монтаж видеороликов", "монтаж видео", "видеомонтаж"
]

CONFIG_FILE = "config.json"

fh_sent_projects = set()
kabanchik_sent_tasks = set()
weblancer_sent_projects = set()
pending_orders = {}
ai_responses_cache = {}

# Сессия для Kabanchik
kabanchik_session = None

stats = {
    "orders_found": 0,
    "orders_sent": 0,
    "ai_generated": 0,
    "start_time": time.time(),
    "freelancehunt": 0,
    "kabanchik": 0,
    "weblancer": 0
}

errors = {
    "freelancehunt": 0,
    "kabanchik": 0,
    "weblancer": 0,
    "gemini": 0,
    "telegram": 0,
    "last_errors": []
}

check_stats = {
    "freelancehunt": {
        "last_check": None,
        "last_count": 0,
        "total_checks": 0,
        "categories": {}
    },
    "kabanchik": {
        "last_check": None,
        "last_count": 0,
        "total_checks": 0,
        "categories": {}
    },
    "weblancer": {
        "last_check": None,
        "last_count": 0,
        "total_checks": 0,
        "keywords": {}
    }
}

def get_short_id(project_id):
    return hashlib.md5(project_id.encode()).hexdigest()[:8]

def update_check_stats(platform, category, count):
    kiev_time = time.localtime(time.time() + 10800)
    time_str = time.strftime('%d.%m.%Y %H:%M', kiev_time)
    
    if platform == "freelancehunt":
        check_stats["freelancehunt"]["last_check"] = time_str
        check_stats["freelancehunt"]["total_checks"] += 1
        check_stats["freelancehunt"]["last_count"] += count
        if category:
            check_stats["freelancehunt"]["categories"][category] = check_stats["freelancehunt"]["categories"].get(category, 0) + count
    elif platform == "kabanchik":
        check_stats["kabanchik"]["last_check"] = time_str
        check_stats["kabanchik"]["total_checks"] += 1
        check_stats["kabanchik"]["last_count"] += count
        if category:
            check_stats["kabanchik"]["categories"][category] = check_stats["kabanchik"]["categories"].get(category, 0) + count
    elif platform == "weblancer":
        check_stats["weblancer"]["last_check"] = time_str
        check_stats["weblancer"]["total_checks"] += 1
        check_stats["weblancer"]["last_count"] += count
        if category:
            check_stats["weblancer"]["keywords"][category] = check_stats["weblancer"]["keywords"].get(category, 0) + count

def log_error(error_type, message):
    kiev_time = time.localtime(time.time() + 10800)
    time_str = time.strftime('%H:%M', kiev_time)
    
    if error_type in errors:
        errors[error_type] += 1
    else:
        errors[error_type] = 1
    
    errors["last_errors"].append(f"{error_type.capitalize()}: {time_str} - {message}")
    if len(errors["last_errors"]) > 10:
        errors["last_errors"] = errors["last_errors"][-10:]

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return

def run_web_server():
    try:
        HTTPServer(("0.0.0.0", PORT), HealthCheckServer).serve_forever()
    except Exception as e:
        print(f"Web server error: {e}")

def telegram_api(method, payload):
    if not BOT_TOKEN:
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload,
            timeout=20
        )
        if r.status_code != 200:
            print(f"Telegram API error {method}: {r.status_code} {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"Telegram API exception {method}: {e}")
        return None

def get_default_config():
    return {
        "freelancehunt": {
            "categories": {
                "AI создание видео": True,
                "Анимация": True,
                "Аудио/видео монтаж": True,
                "Видео реклама": True,
                "Обработка аудио": True,
                "Обработка видео": True,
                "Обработка фото": True,
                "Услуги диктора": True
            },
            "min_budget": 0,
            "keywords": [
                "монтаж", "видеомонтаж", "монтаж видео", "нарезка", "склейка",
                "редактирование видео", "рекламный ролик", "видеореклама",
                "промо", "динамичный ролик", "реклама для соцсетей",
                "рекламное видео", "youtube видео", "ютуб",
                "youtube монтаж", "ai видео", "генерация видео",
                "нейросеть", "davinci resolve", "цветокоррекция",
                "color grading", "визуальные эффекты", "vfx",
                "motion", "анимация", "обработка видео", "ретушь"
            ]
        },
        "kabanchik": {
            "categories": {
                "AI услуги": True,
                "Дизайн": True,
                "Фото и видео услуги": True
            },
            "min_budget": 0
        }
    }

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"load_config error: {e}")
    return None

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"save_config error: {e}")
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
        print("BOT_TOKEN или CHAT_ID не заданы!")
        return None

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    result = telegram_api("sendMessage", payload)
    if result is None:
        log_error("telegram", "не удалось отправить сообщение")
    else:
        print(f"Сообщение отправлено! ID: {result.get('result', {}).get('message_id', 'unknown')}")
    return result

def generate_ai_bid(project_title, project_description, project_category):
    if not GEMINI_API_KEY:
        return f"""Здравствуйте! Меня заинтересовал ваш заказ «{project_title}».

Я специализируюсь в области {project_category} и имею успешный опыт.

Буду рад обсудить детали, стоимость и сроки. Жду вашего ответа!"""
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""
Ты — профессиональный фрилансер с опытом в {project_category}.
Напиши ПЕРСОНАЛЬНЫЙ отклик на этот конкретный заказ:

Заказ: {project_title}
Описание: {project_description[:500]}

Твой ответ должен:
1. Быть уникальным для ЭТОГО КОНКРЕТНОГО заказа
2. Показать понимание задачи
3. Предложить конкретные идеи решения
4. Быть уверенным и профессиональным
5. НЕ УПОМИНАТЬ цену и сроки

Стиль: {template['style']}
Дополнительный текст: {template['extra_text']}

Ответ: 3-5 предложений на русском языке.
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            ai_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if ai_text:
                return ai_text.strip()
        
        return f"""Здравствуйте! Меня заинтересовал ваш заказ «{project_title}».

Я специализируюсь в области {project_category} и имею успешный опыт.

Буду рад обсудить детали, стоимость и сроки. Жду вашего ответа!"""
            
    except Exception as e:
        log_error("gemini", str(e)[:30])
        return f"""Здравствуйте! Меня заинтересовал ваш заказ «{project_title}».

Я специализируюсь в области {project_category} и имею опыт в таких проектах.

Готов обсудить детали и предложить лучшее решение. Жду вашего ответа!"""

def send_telegram_message_with_buttons(text, button_url, project_id):
    if not BOT_TOKEN or not CHAT_ID:
        return None

    short_id = get_short_id(project_id)

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔗 Открыть", "url": button_url.strip()},
                {"text": "💼 Откликнуться", "callback_data": f"bid_{short_id}"}
            ]
        ]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    
    result = telegram_api("sendMessage", payload)
    if result is None:
        log_error("telegram", "не удалось отправить кнопку")
    else:
        message_id = result.get('result', {}).get('message_id', 'unknown')
        print(f"Отправлено! message_id: {message_id}")
        stats["orders_sent"] += 1
    return result

def send_bid(project_id, price, deadline, comment):
    if not FH_API_TOKEN:
        return {"status": "error", "message": "❌ API-ключ не настроен!"}
    
    try:
        match = re.search(r'/(\d+)/?', project_id)
        if not match:
            return {"status": "error", "message": f"❌ Не удалось определить ID проекта"}
        
        project_id_clean = match.group(1)
        
        print(f"Отправка отклика на проект {project_id_clean} (Freelancehunt)")
        
        url = "https://api.freelancehunt.com/v2/bids"
        
        headers = {
            "Authorization": f"Bearer {FH_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        data = {
            "project_id": int(project_id_clean),
            "price": price,
            "deadline": deadline,
            "comment": comment
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 201 or response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"Ошибка {response.status_code}: {response.text[:200]}"}
            
    except Exception as e:
        log_error("freelancehunt", f"Отправка отклика: {str(e)[:30]}")
        return {"status": "error", "message": str(e)}

def create_main_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⚙️ Настройки", "callback_data": "open_settings"},
                {"text": "🔄 Перезапуск", "callback_data": "bot_restart"}
            ],
            [
                {"text": "📊 Статус бота", "callback_data": "bot_status"},
                {"text": "❓ Help", "callback_data": "bot_help"}
            ]
        ]
    }

def create_help_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "⚙️ Настройки", "callback_data": "open_settings"},
                {"text": "📊 Статус бота", "callback_data": "bot_status"}
            ],
            [
                {"text": "🗑️ Очистить кэш", "callback_data": "clear_cache"},
                {"text": "🔄 Перезапуск", "callback_data": "bot_restart"}
            ],
            [
                {"text": "🏠 Главное меню", "callback_data": "show_main_menu"}
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
                {"text": "📁 Freelancehunt", "callback_data": "show_fh_categories"},
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
                {"text": "Монтаж", "callback_data": "kw_montage"},
                {"text": "AI видео", "callback_data": "kw_ai_video"}
            ],
            [
                {"text": "Реклама", "callback_data": "kw_ads"},
                {"text": "YouTube", "callback_data": "kw_youtube"}
            ],
            [
                {"text": "DaVinci", "callback_data": "kw_davinci"},
                {"text": "Цветокор", "callback_data": "kw_color"}
            ],
            [
                {"text": "⬅️ Назад", "callback_data": "back_to_settings"}
            ]
        ]
    }

def create_template_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Цена", "callback_data": "template_price"},
                {"text": "📅 Срок", "callback_data": "template_deadline"}
            ],
            [
                {"text": "🎯 Стиль", "callback_data": "template_style"},
                {"text": "📝 Доп. текст", "callback_data": "template_text"}
            ],
            [
                {"text": "📋 Показать шаблон", "callback_data": "template_show"},
                {"text": "⬅️ Назад", "callback_data": "show_main_menu"}
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
    for cat, enabled in config.get("kabanchik", {}).get("categories", {}).items():
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
    return text, False

def matches_keywords(text, keywords):
    if not text:
        return False
    low = text.lower()
    return any(kw.lower() in low for kw in keywords)

def detect_fh_category(text):
    text_low = text.lower()
    category_map = {
        "AI создание видео": ["ai", "нейросеть", "генерация видео", "sora", "midjourney"],
        "Анимация": ["анимация", "motion", "2d", "3d", "after effects"],
        "Аудио/видео монтаж": ["монтаж", "видеомонтаж", "нарезка", "склейка", "редактирование"],
        "Видео реклама": ["рекламный ролик", "видеореклама", "промо", "рекламное видео"],
        "Обработка аудио": ["аудио", "звук", "обработка звука", "озвучка"],
        "Обработка видео": ["обработка видео", "цветокор", "color grading", "davinci resolve"],
        "Обработка фото": ["обработка фото", "ретушь", "photoshop"],
        "Услуги диктора": ["диктор", "озвучка", "голос", "voice over"]
    }

    for category, words in category_map.items():
        if any(word in text_low for word in words):
            return category

    return "Без категории"

def format_quote(text):
    lines = text.split('\n')
    quoted_lines = [f"> {line}" for line in lines if line.strip()]
    return '\n'.join(quoted_lines) if quoted_lines else "> (описание отсутствует)"

def format_freelancehunt_message(title, summary, category, budget=None, currency=""):
    budget_text = "Не указана"
    if budget is not None:
        budget_text = f"{budget} {currency}".strip()

    title, title_translated = maybe_translate(title)
    summary, summary_translated = maybe_translate(summary)

    title_line = f"📌 <b>{clean_html_text(title)}</b>"
    if title_translated:
        title_line += " <i>(переведен)</i>"

    category_formatted = f"<code>{clean_html_text(category)}</code>"

    summary_quoted = format_quote(clean_html_text(summary[:900]))
    if summary_translated:
        summary_quoted += "\n\n<i>(переведен)</i>"

    summary_line = f"┌─────────────────────\n📝 <b>Описание:</b>\n{summary_quoted}"

    return (
        f"🟡 <b>Freelancehunt</b>\n\n"
        f"{title_line}\n\n"
        f"🏷 <b>Категория:</b> {category_formatted}\n"
        f"💰 <b>Бюджет:</b> {clean_html_text(budget_text)}\n\n"
        f"{summary_line}"
    )

def format_kabanchik_message(title, description, category, budget=None, currency=""):
    budget_text = "Не указана"
    if budget is not None:
        budget_text = f"{budget} {currency}".strip()

    title, title_translated = maybe_translate(title)
    description, description_translated = maybe_translate(description)

    title_line = f"📌 <b>{clean_html_text(title)}</b>"
    if title_translated:
        title_line += " <i>(переведен)</i>"

    category_formatted = f"<code>{clean_html_text(category)}</code>"

    description_quoted = format_quote(clean_html_text(description[:900]))
    if description_translated:
        description_quoted += "\n\n<i>(переведен)</i>"

    description_line = f"┌─────────────────────\n📝 <b>Описание:</b>\n{description_quoted}"

    return (
        f"🟢 <b>Kabanchik</b>\n\n"
        f"{title_line}\n\n"
        f"🏷 <b>Категория:</b> {category_formatted}\n"
        f"💰 <b>Бюджет:</b> {clean_html_text(budget_text)}\n\n"
        f"{description_line}"
    )

def format_weblancer_message(title, description, budget_text, link):
    title, title_translated = maybe_translate(title)
    description, description_translated = maybe_translate(description)

    title_line = f"📌 <b>{clean_html_text(title)}</b>"
    if title_translated:
        title_line += " <i>(переведен)</i>"

    description_quoted = format_quote(clean_html_text(description[:900]))
    if description_translated:
        description_quoted += "\n\n<i>(переведен)</i>"

    description_line = f"┌─────────────────────\n📝 <b>Описание:</b>\n{description_quoted}"

    return (
        f"🟣 <b>Weblancer</b>\n\n"
        f"{title_line}\n\n"
        f"🏷 <b>Категория:</b> <code>Видеомонтаж / AI-видео</code>\n"
        f"💰 <b>Бюджет:</b> {clean_html_text(budget_text)}\n\n"
        f"{description_line}"
    )

def get_uptime():
    diff = time.time() - stats["start_time"]
    hours = int(diff // 3600)
    minutes = int((diff % 3600) // 60)
    return f"{hours} ч {minutes} мин"

def get_status_message():
    total_errors = sum([errors["freelancehunt"], errors["kabanchik"], errors["weblancer"], errors["gemini"], errors["telegram"]])
    
    status = "✅ БОТ РАБОТАЕТ" if total_errors < 10 else "⚠️ БОТ РАБОТАЕТ С ОШИБКАМИ"
    
    error_lines = []
    if errors["freelancehunt"] > 0:
        error_lines.append(f"• Freelancehunt: {errors['freelancehunt']} ошибок")
    if errors["kabanchik"] > 0:
        error_lines.append(f"• Kabanchik: {errors['kabanchik']} ошибок")
    if errors["weblancer"] > 0:
        error_lines.append(f"• Weblancer: {errors['weblancer']} ошибок")
    if errors["gemini"] > 0:
        error_lines.append(f"• Gemini: {errors['gemini']} ошибок")
    if errors["telegram"] > 0:
        error_lines.append(f"• Telegram: {errors['telegram']} ошибок")
    
    if not error_lines:
        error_lines.append("• Ошибок нет ✅")
    
    last_errors = "\n".join([f"• {e}" for e in errors["last_errors"][-3:]]) if errors["last_errors"] else "• Нет"
    gemini_status = "✅ Доступен" if GEMINI_API_KEY else "❌ Не настроен"
    
    kiev_time = time.localtime(stats["start_time"] + 10800)
    
    checks_lines = []
    
    fh = check_stats["freelancehunt"]
    if fh["last_check"]:
        checks_lines.append(f"> <b>Freelancehunt:</b> {fh['last_check']}")
        checks_lines.append(f"> (проверок: {fh['total_checks']}, найдено: {fh['last_count']} заказов)")
        if fh["categories"]:
            active_cats = {k: v for k, v in fh["categories"].items() if v > 0}
            if active_cats:
                for cat, count in active_cats.items():
                    checks_lines.append(f">   - {cat}: {count} заказов")
        checks_lines.append("")
    else:
        checks_lines.append("> Freelancehunt: ожидание первой проверки...")
        checks_lines.append("")
    
    kb = check_stats["kabanchik"]
    if kb["last_check"]:
        checks_lines.append(f"> <b>Kabanchik:</b> {kb['last_check']}")
        checks_lines.append(f"> (проверок: {kb['total_checks']}, найдено: {kb['last_count']} заказов)")
        if kb["categories"]:
            active_cats = {k: v for k, v in kb["categories"].items() if v > 0}
            if active_cats:
                for cat, count in active_cats.items():
                    checks_lines.append(f">   - {cat}: {count} заказов")
        checks_lines.append("")
    else:
        checks_lines.append("> Kabanchik: ожидание первой проверки...")
        checks_lines.append("")
    
    wl = check_stats["weblancer"]
    if wl["last_check"]:
        checks_lines.append(f"> <b>Weblancer:</b> {wl['last_check']}")
        checks_lines.append(f"> (проверок: {wl['total_checks']}, найдено: {wl['last_count']} заказов)")
        if wl["keywords"]:
            active_kws = {k: v for k, v in wl["keywords"].items() if v > 0}
            if active_kws:
                for kw, count in active_kws.items():
                    checks_lines.append(f">   - Поиск '{kw}': {count} заказов")
        checks_lines.append("")
    else:
        checks_lines.append("> Weblancer: ожидание первой проверки...")
        checks_lines.append("")
    
    checks_text = "\n".join(checks_lines)
    
    return (
        f"📊 <b>СТАТУС БОТА</b>\n\n"
        f"{status}\n\n"
        f"📋 <b>Статистика:</b>\n"
        f"• Всего найдено: {stats['orders_found']}\n"
        f"• Freelancehunt: {stats['freelancehunt']}\n"
        f"• Kabanchik: {stats['kabanchik']}\n"
        f"• Weblancer: {stats['weblancer']}\n"
        f"• Отправлено в Telegram: {stats['orders_sent']}\n"
        f"• AI-ответов сгенерировано: {stats['ai_generated']}\n\n"
        f"🔄 <b>Последние проверки:</b>\n"
        f"{checks_text}\n"
        f"⚠️ <b>Ошибки:</b>\n" + "\n".join(error_lines) + f"\n"
        f"📌 <b>Последние ошибки:</b>\n{last_errors}\n\n"
        f"🤖 <b>Gemini API:</b> {gemini_status}\n"
        f"⏱ <b>Работает:</b> {get_uptime()}\n"
        f"🔄 <b>Запущен (Киев):</b> {time.strftime('%d.%m.%Y %H:%M', kiev_time)}"
    )

def setup_bot_menu():
    telegram_api("setMyCommands", {
        "commands": [
            {"command": "start", "description": "🏠 Главное меню"},
            {"command": "settings", "description": "⚙️ Настройки"},
            {"command": "status", "description": "📊 Статус бота"},
            {"command": "help", "description": "❓ Помощь"}
        ]
    })

def login_to_kabanchik():
    global kabanchik_session
    
    try:
        if not KABANCHIK_EMAIL or not KABANCHIK_PASSWORD:
            print("❌ Не заданы KABANCHIK_EMAIL или KABANCHIK_PASSWORD")
            return False
        
        print("🔐 Выполняю вход на Kabanchik...")
        
        kabanchik_session = requests.Session()
        kabanchik_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        response = kabanchik_session.get(KABANCHIK_LOGIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        
        csrf_token = None
        token_input = soup.find("input", {"name": "_token"})
        if token_input:
            csrf_token = token_input.get("value")
        
        login_data = {
            "email": KABANCHIK_EMAIL,
            "password": KABANCHIK_PASSWORD,
            "_token": csrf_token or "",
            "remember": "1"
        }
        
        response = kabanchik_session.post(
            KABANCHIK_LOGIN_URL,
            data=login_data,
            timeout=30,
            allow_redirects=True
        )
        
        if "вход" in response.text.lower() or "login" in response.url.lower():
            print("❌ Вход на Kabanchik не удался")
            return False
        
        print("✅ Успешный вход на Kabanchik!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка авторизации на Kabanchik: {e}")
        return False

def parse_kabanchik():
    global kabanchik_session, kabanchik_sent_tasks
    
    print("🔍 Начинаю парсинг Kabanchik...")
    config = ensure_config_exists()
    enabled_categories = config.get("kabanchik", {}).get("categories", {})
    min_budget = config.get("kabanchik", {}).get("min_budget", 0)
    
    try:
        if not kabanchik_session:
            if not login_to_kabanchik():
                print("❌ Не удалось авторизоваться на Kabanchik")
                return
        
        total = 0
        
        for category_key, category_slug in KABANCHIK_CATEGORIES.items():
            category_name = {
                "ai_services": "AI услуги",
                "design": "Дизайн",
                "photo_video": "Фото и видео услуги"
            }.get(category_key, category_key)
            
            if not enabled_categories.get(category_name, True):
                print(f"   ⏭️ Категория '{category_name}' отключена")
                continue
            
            try:
                category_url = f"{KABANCHIK_PROJECTS_URL}/{category_slug}"
                print(f"   📂 Категория: {category_name}")
                print(f"   URL: {category_url}")
                
                response = kabanchik_session.get(category_url, timeout=30)
                
                if response.status_code != 200:
                    print(f"   ❌ Ошибка: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                project_items = soup.find_all("div", class_="project-item")
                if not project_items:
                    project_items = soup.find_all("div", class_="task-item")
                if not project_items:
                    project_items = soup.find_all("div", class_="order-item")
                if not project_items:
                    project_items = soup.find_all("div", class_="item")
                
                count = 0
                
                for item in project_items:
                    try:
                        title_elem = item.find("a", class_="title") or item.find("h3") or item.find("h2")
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        
                        link_elem = title_elem if title_elem.name == "a" else title_elem.find("a")
                        if link_elem and link_elem.get("href"):
                            link = "https://kabanchik.ua" + link_elem.get("href")
                        else:
                            continue
                        
                        desc_elem = item.find("div", class_="description") or item.find("p")
                        description = desc_elem.get_text(strip=True) if desc_elem else "Описание на сайте"
                        
                        budget_elem = item.find("div", class_="budget") or item.find("span", class_="price")
                        budget_text = budget_elem.get_text(strip=True) if budget_elem else ""
                        
                        project_id = link or title
                        
                        if project_id in kabanchik_sent_tasks:
                            continue
                        
                        if min_budget:
                            budget, _ = extract_budget_and_currency(budget_text)
                            if budget and budget < min_budget:
                                continue
                        
                        kabanchik_sent_tasks.add(project_id)
                        stats["orders_found"] += 1
                        stats["kabanchik"] += 1
                        count += 1
                        total += 1
                        
                        message_text = format_kabanchik_message(
                            title, description, category_name, None, ""
                        )
                        
                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {"text": "🔗 Открыть на Kabanchik", "url": link}
                                ]
                            ]
                        }
                        
                        send_telegram_message(message_text, keyboard)
                        print(f"   ✅ {title[:50]}...")
                        
                    except Exception as e:
                        print(f"   ⚠️ Ошибка: {e}")
                        continue
                
                print(f"   📊 В категории '{category_name}' найдено: {count} заказов")
                update_check_stats("kabanchik", category_name, count)
                
            except Exception as e:
                print(f"   ❌ Ошибка категории {category_name}: {e}")
                continue
        
        check_stats["kabanchik"]["last_count"] = total
        print(f"📊 Kabanchik: всего найдено {total} заказов")
                
    except Exception as e:
        log_error("kabanchik", str(e)[:30])
        print(f"❌ Ошибка парсинга Kabanchik: {e}")
        kabanchik_session = None

def parse_freelancehunt():
    print("🔍 Начинаю парсинг Freelancehunt...")
    config = ensure_config_exists()
    enabled_keywords = config["freelancehunt"]["keywords"]
    min_budget = config["freelancehunt"]["min_budget"]
    
    total_in_category = 0

    for category_key, category_url in FH_CATEGORIES.items():
        try:
            category_name = FH_CATEGORY_NAMES.get(category_key, category_key)
            if not config["freelancehunt"]["categories"].get(category_name, True):
                print(f"   ⏭️ Категория '{category_name}' отключена")
                continue
                
            print(f"   📂 Категория: {category_name}")
            feed = feedparser.parse(category_url)
            
            if len(feed.entries) == 0:
                print(f"   ⚠️ RSS пустой! Проверь URL: {category_url}")
                continue
            
            count_in_category = 0
            
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

                count_in_category += 1
                total_in_category += 1
                
                category = detect_fh_category(text_for_filter)
                fh_sent_projects.add(project_id)
                
                stats["orders_found"] += 1
                stats["freelancehunt"] += 1

                pending_orders[project_id] = {
                    "title": title,
                    "description": summary,
                    "category": category,
                    "link": link
                }

                bid_text = generate_ai_bid(title, summary, category)
                ai_responses_cache[project_id] = bid_text
                stats["ai_generated"] += 1

                message_text = format_freelancehunt_message(
                    title, summary, category, budget, currency
                )

                send_telegram_message_with_buttons(
                    message_text,
                    link,
                    project_id
                )
            
            update_check_stats("freelancehunt", category_name, count_in_category)
            
        except Exception as e:
            log_error("freelancehunt", str(e)[:30])
            print(f"   ❌ Ошибка {category_name}: {e}")
    
    check_stats["freelancehunt"]["last_count"] = total_in_category

def parse_weblancer():
    print("🔍 Начинаю парсинг Weblancer...")
    config = ensure_config_exists()
    enabled_keywords = config["freelancehunt"]["keywords"]
    min_budget = config["freelancehunt"]["min_budget"]
    total_in_keyword = 0
    
    try:
        for keyword in WEBLANCER_KEYWORDS[:10]:
            try:
                search_url = f"{WEBLANCER_URL}?q={keyword.replace(' ', '+')}"
                response = requests.get(search_url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, "html.parser")
                count_in_keyword = 0
                
                projects = soup.find_all("div", class_="col-sm-12")
                
                if not projects:
                    projects = soup.find_all("div", class_="row")
                
                for project in projects:
                    try:
                        title_elem = project.find("div", class_="title")
                        if not title_elem:
                            link_elem = project.find("a", href=True)
                            if not link_elem:
                                continue
                            title = link_elem.get_text(strip=True)
                            link = "https://www.weblancer.net" + link_elem.get("href")
                        else:
                            title = title_elem.get_text(strip=True)
                            link_elem = title_elem.find("a")
                            if not link_elem:
                                continue
                            link = "https://www.weblancer.net" + link_elem.get("href")
                        
                        desc_elem = project.find("div", class_="description")
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        
                        budget_elem = project.find("div", class_="amount")
                        budget_text = budget_elem.get_text(strip=True) if budget_elem else "Не указан"
                        
                        project_id = link or title
                        
                        if project_id in weblancer_sent_projects:
                            continue
                        
                        text_for_filter = f"{title} {description}"
                        budget, currency = extract_budget_and_currency(budget_text)
                        
                        if min_budget and budget is not None and budget < min_budget:
                            continue
                            
                        if enabled_keywords and not matches_keywords(text_for_filter, enabled_keywords):
                            continue
                        
                        weblancer_sent_projects.add(project_id)
                        stats["orders_found"] += 1
                        stats["weblancer"] += 1
                        count_in_keyword += 1
                        total_in_keyword += 1
                        
                        message_text = format_weblancer_message(
                            title, description, budget_text, link
                        )
                        
                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {"text": "🔗 Открыть", "url": link}
                                ]
                            ]
                        }
                        send_telegram_message(message_text, keyboard)
                        
                    except Exception as e:
                        continue
                
                update_check_stats("weblancer", keyword, count_in_keyword)
                print(f"   📊 По ключевому слову '{keyword}' найдено: {count_in_keyword} заказов")
                        
            except Exception as e:
                print(f"   ⚠️ Ошибка поиска по ключевому слову {keyword}: {e}")
                continue
                
    except Exception as e:
        log_error("weblancer", str(e)[:30])
        print(f"   ❌ Ошибка Weblancer: {e}")
    
    check_stats["weblancer"]["last_count"] = total_in_keyword
    print(f"📊 Weblancer: всего найдено {total_in_keyword} заказов")

def handle_updates():
    global waiting_for_template_input, template_input_type
    
    offset = 0
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30",
                timeout=40
            )

            if r.status_code != 200:
                time.sleep(5)
                continue

            updates = r.json().get("result", [])

            for u in updates:
                offset = max(offset, u["update_id"] + 1)

                if "message" in u:
                    message = u["message"]
                    text = message.get("text", "").strip()

                    if waiting_for_template_input:
                        if template_input_type == "price":
                            try:
                                new_price = int(text)
                                if 0 < new_price < 100000:
                                    template["price"] = new_price
                                    send_telegram_message(f"✅ Цена установлена: {template['price']} UAH")
                                else:
                                    send_telegram_message("❌ Введите корректную цену (от 1 до 100000)")
                            except:
                                send_telegram_message("❌ Введите число")
                            waiting_for_template_input = False
                            template_input_type = None
                            continue
                        
                        elif template_input_type == "deadline":
                            try:
                                new_deadline = int(text)
                                if 0 < new_deadline < 365:
                                    template["deadline"] = new_deadline
                                    send_telegram_message(f"✅ Срок установлен: {template['deadline']} дня")
                                else:
                                    send_telegram_message("❌ Введите корректный срок (от 1 до 365)")
                            except:
                                send_telegram_message("❌ Введите число")
                            waiting_for_template_input = False
                            template_input_type = None
                            continue
                        
                        elif template_input_type == "text":
                            if len(text) > 3:
                                template["extra_text"] = text
                                send_telegram_message(f"✅ Дополнительный текст сохранён:\n{template['extra_text']}")
                            else:
                                send_telegram_message("❌ Текст должен быть длиннее 3 символов")
                            waiting_for_template_input = False
                            template_input_type = None
                            continue

                    if text == "/start":
                        send_telegram_message("🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n\nВыберите действие:", create_main_keyboard())
                    elif text == "/settings":
                        send_telegram_message("⚙️ <b>Настройки</b>", create_settings_keyboard())
                    elif text == "/template":
                        send_telegram_message(
                            "📝 <b>НАСТРОЙКА ШАБЛОНА ОТКЛИКА</b>\n\n"
                            f"💰 Цена: {template['price']} UAH\n"
                            f"📅 Срок: {template['deadline']} дня\n"
                            f"🎯 Стиль: {template['style']}\n"
                            f"📝 Доп. текст: {template['extra_text']}\n\n"
                            "Выберите, что изменить:",
                            create_template_keyboard()
                        )
                    elif text == "/help":
                        send_telegram_message(
                            "📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n"
                            "⚙️ Настройки\n"
                            "📊 Статус бота\n"
                            "🗑️ Очистить кэш\n"
                            "🔄 Перезапуск\n\n"
                            "❓ Помощь — это меню",
                            create_help_keyboard()
                        )
                    elif text == "/status":
                        send_telegram_message(get_status_message())

                elif "callback_query" in u:
                    cb = u["callback_query"]
                    data = cb["data"]
                    cid = cb["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    message_id = cb["message"]["message_id"]
                    config = ensure_config_exists()

                    if data.startswith("bid_"):
                        short_id = data.replace("bid_", "")
                        project_id = None
                        for pid in pending_orders.keys():
                            if get_short_id(pid) == short_id:
                                project_id = pid
                                break
                        
                        if project_id and project_id in pending_orders:
                            order = pending_orders[project_id]
                            
                            if "freelancehunt.com" not in order.get("link", ""):
                                send_telegram_message(
                                    "❌ Автоотклик доступен ТОЛЬКО для заказов с Freelancehunt.\n"
                                    "Для этого заказа откройте ссылку и откликнитесь вручную."
                                )
                                telegram_api("answerCallbackQuery", {
                                    "callback_query_id": cid,
                                    "text": "❌ Только Freelancehunt",
                                    "show_alert": True
                                })
                                continue
                            
                            bid_text = generate_ai_bid(
                                order["title"],
                                order["description"],
                                order["category"]
                            )
                            
                            ai_responses_cache[project_id] = bid_text
                            
                            send_telegram_message(
                                f"📤 <b>ПОДТВЕРЖДЕНИЕ ОТКЛИКА</b>\n\n"
                                f"📌 <b>Заказ:</b> {order['title']}\n\n"
                                f"💰 <b>Цена:</b> {template['price']} UAH\n"
                                f"📅 <b>Срок:</b> {template['deadline']} дня\n\n"
                                f"📝 <b>Ваш отклик:</b>\n{bid_text}\n\n"
                                f"Подтвердите отправку:",
                                {
                                    "inline_keyboard": [
                                        [
                                            {"text": "✅ Отправить", "callback_data": f"send_{short_id}"},
                                            {"text": "🔄 Перегенерировать", "callback_data": f"regenerate_{short_id}"},
                                            {"text": "❌ Отмена", "callback_data": f"cancel_{short_id}"}
                                        ]
                                    ]
                                }
                            )
                            
                            telegram_api("answerCallbackQuery", {
                                "callback_query_id": cid,
                                "text": "📝 Отклик сгенерирован!",
                                "show_alert": False
                            })
                        else:
                            telegram_api("answerCallbackQuery", {
                                "callback_query_id": cid,
                                "text": "❌ Заказ не найден",
                                "show_alert": True
                            })

                    elif data.startswith("send_"):
                        short_id = data.replace("send_", "")
                        project_id = None
                        for pid in pending_orders.keys():
                            if get_short_id(pid) == short_id:
                                project_id = pid
                                break
                        
                        if project_id and project_id in pending_orders:
                            order = pending_orders[project_id]
                            bid_text = ai_responses_cache.get(project_id, "")
                            
                            if not bid_text:
                                bid_text = generate_ai_bid(
                                    order["title"],
                                    order["description"],
                                    order["category"]
                                )
                            
                            result = send_bid(
                                project_id,
                                template['price'],
                                template['deadline'],
                                bid_text
                            )
                            
                            if result["status"] == "success":
                                send_telegram_message(
                                    f"✅ <b>ОТКЛИК ОТПРАВЛЕН!</b>\n\n"
                                    f"📌 <b>Заказ:</b> {order['title']}\n"
                                    f"💰 <b>Цена:</b> {template['price']} UAH\n"
                                    f"📅 <b>Срок:</b> {template['deadline']} дня\n\n"
                                    f"Ждите ответа заказчика! 🍀"
                                )
                            else:
                                send_telegram_message(
                                    f"❌ <b>Ошибка отправки!</b>\n\n"
                                    f"{result['message']}\n\n"
                                    f"Попробуйте позже или отправьте вручную."
                                )
                            
                            telegram_api("answerCallbackQuery", {
                                "callback_query_id": cid,
                                "text": "✅ Готово!" if result["status"] == "success" else "❌ Ошибка",
                                "show_alert": False
                            })
                        else:
                            telegram_api("answerCallbackQuery", {
                                "callback_query_id": cid,
                                "text": "❌ Заказ не найден",
                                "show_alert": True
                            })

                    elif data.startswith("regenerate_"):
                        short_id = data.replace("regenerate_", "")
                        project_id = None
                        for pid in pending_orders.keys():
                            if get_short_id(pid) == short_id:
                                project_id = pid
                                break
                        
                        if project_id and project_id in pending_orders:
                            order = pending_orders[project_id]
                            
                            bid_text = generate_ai_bid(
                                order["title"],
                                order["description"],
                                order["category"]
                            )
                            ai_responses_cache[project_id] = bid_text
                            
                            send_telegram_message(
                                f"📤 <b>ПОДТВЕРЖДЕНИЕ ОТКЛИКА</b>\n\n"
                                f"📌 <b>Заказ:</b> {order['title']}\n\n"
                                f"💰 <b>Цена:</b> {template['price']} UAH\n"
                                f"📅 <b>Срок:</b> {template['deadline']} дня\n\n"
                                f"🔄 <b>Новый отклик:</b>\n{bid_text}\n\n"
                                f"Подтвердите отправку:",
                                {
                                    "inline_keyboard": [
                                        [
                                            {"text": "✅ Отправить", "callback_data": f"send_{short_id}"},
                                            {"text": "🔄 Перегенерировать", "callback_data": f"regenerate_{short_id}"},
                                            {"text": "❌ Отмена", "callback_data": f"cancel_{short_id}"}
                                        ]
                                    ]
                                }
                            )
                            
                            telegram_api("answerCallbackQuery", {
                                "callback_query_id": cid,
                                "text": "🔄 Новый отклик готов!",
                                "show_alert": False
                            })
                        else:
                            telegram_api("answerCallbackQuery", {
                                "callback_query_id": cid,
                                "text": "❌ Заказ не найден",
                                "show_alert": True
                            })

                    elif data.startswith("cancel_"):
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "❌ Отменено",
                            "show_alert": False
                        })

                    elif data == "open_template":
                        send_telegram_message(
                            "📝 <b>НАСТРОЙКА ШАБЛОНА ОТКЛИКА</b>\n\n"
                            f"💰 Цена: {template['price']} UAH\n"
                            f"📅 Срок: {template['deadline']} дня\n"
                            f"🎯 Стиль: {template['style']}\n"
                            f"📝 Доп. текст: {template['extra_text']}\n\n"
                            "Выберите, что изменить:",
                            create_template_keyboard()
                        )

                    elif data == "template_price":
                        waiting_for_template_input = True
                        template_input_type = "price"
                        send_telegram_message(
                            f"💰 <b>Текущая цена:</b> {template['price']} UAH\n\n"
                            "Отправьте новую цену сообщением.\n"
                            "Например: <code>500</code>"
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "💰 Введите новую цену",
                            "show_alert": False
                        })

                    elif data == "template_deadline":
                        waiting_for_template_input = True
                        template_input_type = "deadline"
                        send_telegram_message(
                            f"📅 <b>Текущий срок:</b> {template['deadline']} дня\n\n"
                            "Отправьте новый срок сообщением.\n"
                            "Например: <code>5</code>"
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "📅 Введите новый срок",
                            "show_alert": False
                        })

                    elif data == "template_style":
                        send_telegram_message(
                            f"🎯 <b>Текущий стиль:</b> {template['style']}\n\n"
                            "Выберите стиль:",
                            {
                                "inline_keyboard": [
                                    [
                                        {"text": "Профессиональный", "callback_data": "style_professional"},
                                        {"text": "Дружелюбный", "callback_data": "style_friendly"}
                                    ],
                                    [
                                        {"text": "Краткий", "callback_data": "style_short"},
                                        {"text": "Развёрнутый", "callback_data": "style_detailed"}
                                    ],
                                    [
                                        {"text": "⬅️ Назад", "callback_data": "open_template"}
                                    ]
                                ]
                            }
                        )

                    elif data.startswith("style_"):
                        style_map = {
                            "style_professional": "Профессиональный",
                            "style_friendly": "Дружелюбный",
                            "style_short": "Краткий",
                            "style_detailed": "Развёрнутый"
                        }
                        template["style"] = style_map.get(data, "Профессиональный")
                        send_telegram_message(
                            f"✅ Стиль изменён на: <b>{template['style']}</b>",
                            create_template_keyboard()
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": f"✅ Стиль: {template['style']}",
                            "show_alert": False
                        })

                    elif data == "template_text":
                        waiting_for_template_input = True
                        template_input_type = "text"
                        send_telegram_message(
                            f"📝 <b>Текущий дополнительный текст:</b>\n{template['extra_text']}\n\n"
                            "Отправьте новый текст сообщением.\n"
                            "Например: <code>Могу предоставить портфолио</code>"
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "📝 Введите новый текст",
                            "show_alert": False
                        })

                    elif data == "template_show":
                        send_telegram_message(
                            f"📝 <b>ШАБЛОН ОТКЛИКА</b>\n\n"
                            f"💰 Цена: {template['price']} UAH\n"
                            f"📅 Срок: {template['deadline']} дня\n"
                            f"🎯 Стиль: {template['style']}\n"
                            f"📝 Доп. текст: {template['extra_text']}",
                            create_template_keyboard()
                        )

                    elif data == "clear_cache":
                        count = len(ai_responses_cache)
                        ai_responses_cache.clear()
                        send_telegram_message(
                            f"🗑️ <b>Кэш AI-ответов очищен!</b>\n\nУдалено: {count} ответов"
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": f"✅ Удалено {count} ответов",
                            "show_alert": False
                        })

                    elif data == "show_main_menu":
                        send_telegram_message("🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n\nВыберите действие:", create_main_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "🏠 Главное меню",
                            "show_alert": False
                        })

                    elif data == "open_settings":
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
                        for cat, enabled in config.get("kabanchik", {}).get("categories", {}).items():
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
                            "kw_montage": "монтаж",
                            "kw_ai_video": "ai видео",
                            "kw_ads": "реклама",
                            "kw_youtube": "youtube видео",
                            "kw_ai_ads": "ai реклама",
                            "kw_ai_film": "ai фильм",
                            "kw_davinci": "davinci resolve",
                            "kw_color": "цветокоррекция"
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
                        send_telegram_message(get_status_message())

                    elif data == "bot_help":
                        send_telegram_message(
                            "📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n"
                            "⚙️ Настройки\n"
                            "📊 Статус бота\n"
                            "🗑️ Очистить кэш\n"
                            "🔄 Перезапуск\n\n"
                            "❓ Помощь — это меню",
                            create_help_keyboard()
                        )

                    elif data == "bot_restart":
                        send_telegram_message("🔄 Перезапуск...", create_main_keyboard())
                        os._exit(0)

                    elif data == "close_settings":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })

        except Exception as e:
            print(f"DEBUG: Ошибка в handle_updates: {e}")
            time.sleep(5)

def monitor_freelancehunt():
    while True:
        try:
            parse_freelancehunt()
        except Exception as e:
            print(f"DEBUG: monitor_freelancehunt error: {e}")
        time.sleep(FH_INTERVAL)

def monitor_kabanchik():
    while True:
        try:
            parse_kabanchik()
        except Exception as e:
            print(f"DEBUG: monitor_kabanchik error: {e}")
        time.sleep(KABANCHIK_INTERVAL)

def monitor_weblancer():
    while True:
        try:
            parse_weblancer()
        except Exception as e:
            print(f"DEBUG: monitor_weblancer error: {e}")
        time.sleep(WEBLANCER_INTERVAL)

def main():
    try:
        print("🚀 Бот запускается...")
        
        if not BOT_TOKEN or not CHAT_ID:
            print("❌ BOT_TOKEN или CHAT_ID не заданы!")
            sys.exit(1)
        
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=5)
            print("✅ Webhook удален")
        except Exception as e:
            print(f"⚠️ Ошибка удаления webhook: {e}")

        if GEMINI_API_KEY:
            print("✅ GEMINI_API_KEY найден!")
        else:
            print("⚠️ GEMINI_API_KEY не задан!")

        if FH_API_TOKEN:
            print("✅ FH_API_TOKEN найден!")
        else:
            print("⚠️ FH_API_TOKEN не задан!")

        if KABANCHIK_EMAIL and KABANCHIK_PASSWORD:
            print("✅ KABANCHIK_EMAIL и KABANCHIK_PASSWORD найдены!")
            login_to_kabanchik()

        ensure_config_exists()
        setup_bot_menu()

        threads = [
            Thread(target=run_web_server, daemon=True),
            Thread(target=monitor_freelancehunt, daemon=True),
            Thread(target=monitor_kabanchik, daemon=True),
            Thread(target=monitor_weblancer, daemon=True),
            Thread(target=handle_updates, daemon=True)
        ]
        
        for t in threads:
            t.start()
            print(f"✅ Поток {t.name} запущен")

        print("✅ Все потоки запущены. Ожидание...")
        
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        try:
            send_telegram_message(f"❌ Бот упал с ошибкой:\n{str(e)[:300]}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
