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
pending_orders = {}
ai_responses_cache = {}

stats = {
    "orders_found": 0,
    "orders_sent": 0,
    "ai_generated": 0,
    "start_time": time.time(),
    "freelancehunt": 0,
    "kabanchik": 0
}

errors = {
    "freelancehunt": 0,
    "kabanchik": 0,
    "gemini": 0,
    "telegram": 0,
    "last_errors": []
}

# Функция для генерации короткого ID
def get_short_id(project_id):
    """Генерирует короткий ID для callback_data"""
    return hashlib.md5(project_id.encode()).hexdigest()[:8]


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
        print(f"DEBUG: Web server error: {e}")


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
            print(f"❌ Telegram API error {method}: {r.status_code} {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        print(f"❌ Telegram API exception {method}: {e}")
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
                "youtube монтаж", "ютуб монтаж", "видео для youtube",
                "youtube шортс", "ai видео", "генерация видео",
                "нейросеть", "sora", "midjourney", "генерация фото",
                "ai фото", "ai реклама", "реклама с ии", "ai фильм",
                "короткометражка", "ai кино", "davinci resolve",
                "цветокоррекция", "color grading", "постпродакшн",
                "color correction", "визуальные эффекты", "vfx",
                "motion", "анимация", "динамичный", "монтаж reels",
                "обработка видео", "ретушь"
            ]
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
        print("❌ BOT_TOKEN или CHAT_ID не заданы!")
        return None

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    print(f"📤 Отправка сообщения... (длина: {len(text)})")
    result = telegram_api("sendMessage", payload)
    if result is None:
        errors["telegram"] += 1
        errors["last_errors"].append(f"Telegram: {time.strftime('%H:%M')} - не удалось отправить сообщение")
        print("❌ Не удалось отправить сообщение!")
    else:
        print(f"✅ Сообщение отправлено! ID: {result.get('result', {}).get('message_id', 'unknown')}")
    return result


def send_telegram_message_with_ai_button(text, button_url, project_id):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN или CHAT_ID не заданы!")
        return None

    print(f"📤 Отправка с кнопками для: {project_id[:30]}...")
    print(f"   CHAT_ID: {CHAT_ID}")

    # Берём AI-ответ из кэша
    ai_text = ai_responses_cache.get(project_id, "AI-ответ ещё не сгенерирован")
    ai_text_short = ai_text[:250]  # Максимум 250 символов

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔗 Открыть", "url": button_url.strip()},
                {
                    "text": "🤖 AI ответ",
                    "copy_text": {"text": ai_text_short}  # ← Копирует сразу!
                }
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
        errors["telegram"] += 1
        errors["last_errors"].append(f"Telegram: {time.strftime('%H:%M')} - не удалось отправить кнопку")
        print(f"   ❌ Ошибка отправки!")
    else:
        message_id = result.get('result', {}).get('message_id', 'unknown')
        print(f"   ✅ Отправлено! message_id: {message_id}")
        stats["orders_sent"] += 1
    return result


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
                {"text": "AI реклама", "callback_data": "kw_ai_ads"},
                {"text": "AI фильм", "callback_data": "kw_ai_film"}
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


def translate_to_russian(text):
    return text


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
        "AI создание видео": ["ai", "нейросеть", "генерация видео", "создать видео ии", "sora", "midjourney", "искусственный интеллект", "генерация", "роблокс", "roblox", "аватар"],
        "Анимация": ["анимация", "motion", "2d", "3d", "after effects", "moho", "анимация персонажа"],
        "Аудио/видео монтаж": ["монтаж", "видеомонтаж", "нарезка", "склейка", "редактирование видео"],
        "Видео реклама": ["рекламный ролик", "видеореклама", "промо", "реклама для соцсетей", "рекламное видео", "динамичный ролик", "promo", "reels", "ролик"],
        "Обработка аудио": ["аудио", "звук", "обработка звука", "звукорежиссер", "очистка звука", "запись голоса", "музыка", "озвучка", "диктор", "голос"],
        "Обработка видео": ["обработка видео", "цветокор", "post production", "color correction", "color grading", "davinci resolve", "визуальные эффекты", "vfx"],
        "Обработка фото": ["обработка фото", "ретушь", "photoshop", "ai фото", "генерация фото"],
        "Услуги диктора": ["диктор", "озвучка", "голос", "voice over", "voiceover", "закадровый голос", "профессиональный голос", "озвучивание"]
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


def format_kabanchik_message(title, category, description="Описание на сайте Kabanchik", budget=None, currency=""):
    budget_text = "Не указана"
    if budget is not None:
        budget_text = f"{budget} {currency}".strip()

    title, title_translated = maybe_translate(title)
    description, description_translated = maybe_translate(description)

    title_line = f"📌 <b>{clean_html_text(title)}</b>"
    if title_translated:
        title_line += " <i>(переведен)</i>"

    category_formatted = f"<code>{clean_html_text(category)}</code>"

    description_quoted = format_quote(clean_html_text(description))
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


def get_uptime():
    diff = time.time() - stats["start_time"]
    hours = int(diff // 3600)
    minutes = int((diff % 3600) // 60)
    return f"{hours} ч {minutes} мин"


def get_status_message():
    total_errors = sum([errors["freelancehunt"], errors["kabanchik"], errors["gemini"], errors["telegram"]])
    
    status = "✅ БОТ РАБОТАЕТ" if total_errors < 10 else "⚠️ БОТ РАБОТАЕТ С ОШИБКАМИ"
    
    error_lines = []
    if errors["freelancehunt"] > 0:
        error_lines.append(f"• Freelancehunt: {errors['freelancehunt']} ошибок")
    if errors["kabanchik"] > 0:
        error_lines.append(f"• Kabanchik: {errors['kabanchik']} ошибок")
    if errors["gemini"] > 0:
        error_lines.append(f"• Gemini: {errors['gemini']} ошибок")
    if errors["telegram"] > 0:
        error_lines.append(f"• Telegram: {errors['telegram']} ошибок")
    
    if not error_lines:
        error_lines.append("• Ошибок нет ✅")
    
    last_errors = "\n".join([f"• {e}" for e in errors["last_errors"][-3:]]) if errors["last_errors"] else "• Нет"
    gemini_status = "✅ Доступен" if GEMINI_API_KEY else "❌ Не настроен"
    
    kiev_time = time.localtime(stats["start_time"] + 10800)
    
    return (
        f"📊 <b>СТАТУС БОТА</b>\n\n"
        f"{status}\n\n"
        f"📋 <b>Статистика:</b>\n"
        f"• Всего найдено: {stats['orders_found']}\n"
        f"• Freelancehunt: {stats['freelancehunt']}\n"
        f"• Kabanchik: {stats['kabanchik']}\n"
        f"• Отправлено в Telegram: {stats['orders_sent']}\n"
        f"• AI-ответов сгенерировано: {stats['ai_generated']}\n\n"
        f"⚠️ <b>Ошибки:</b>\n" + "\n".join(error_lines) + f"\n"
        f"📌 <b>Последние ошибки:</b>\n{last_errors}\n\n"
        f"🤖 <b>Gemini API:</b> {gemini_status}\n"
        f"⏱ <b>Работает:</b> {get_uptime()}\n"
        f"🔄 <b>Запущен (Киев):</b> {time.strftime('%d.%m.%Y %H:%M', kiev_time)}"
    )


def generate_ai_response(project_title, project_description, project_category):
    """Генерирует AI-ответ (вызывается при находке заказа)"""
    if not GEMINI_API_KEY:
        return f"""Здравствуйте! Меня заинтересовал ваш заказ «{project_title}».

Я специализируюсь в области {project_category} и имею успешный опыт.

Жду вашего ответа для обсуждения деталей!"""
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""
Ты — профессиональный фрилансер в сфере {project_category}.
Напиши ПЕРСОНАЛЬНЫЙ продающий ответ на этот конкретный заказ:

Заголовок заказа: {project_title}
Описание заказа: {project_description[:500]}

Твой ответ должен:
1. Быть уникальным для ЭТОГО КОНКРЕТНОГО заказа
2. Показать понимание задачи (упомяни детали из описания)
3. Предложить конкретные идеи решения
4. Быть уверенным и профессиональным
5. Заканчиваться призывом к действию

Ответ: 3-5 предложений на русском языке, кратко и по делу.
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
        
        if response.status_code == 429:
            errors["gemini"] += 1
            errors["last_errors"].append(f"Gemini: {time.strftime('%H:%M')} - лимит превышен (429)")
        
        print(f"DEBUG: Gemini error: {response.status_code}")
        return f"""Здравствуйте! Меня заинтересовал ваш заказ «{project_title}».

Я специализируюсь в области {project_category} и имею успешный опыт.

Готов обсудить детали. Жду вашего ответа!"""
            
    except Exception as e:
        errors["gemini"] += 1
        errors["last_errors"].append(f"Gemini: {time.strftime('%H:%M')} - {str(e)[:30]}")
        print(f"DEBUG: AI generation error: {e}")
        return f"""Здравствуйте! Меня заинтересовал ваш заказ «{project_title}».

Я специализируюсь в области {project_category} и имею опыт в таких проектах.

Жду вашего ответа для обсуждения деталей!"""


def setup_bot_menu():
    telegram_api("setMyCommands", {
        "commands": [
            {"command": "start", "description": "🏠 Главное меню"},
            {"command": "settings", "description": "⚙️ Настройки"},
            {"command": "status", "description": "📊 Статус бота"},
            {"command": "help", "description": "❓ Помощь"}
        ]
    })


def parse_freelancehunt():
    config = ensure_config_exists()
    enabled_keywords = config["freelancehunt"]["keywords"]
    min_budget = config["freelancehunt"]["min_budget"]
    
    print(f"🔍 Начинаю парсинг Freelancehunt...")

    for category_name, category_url in FH_CATEGORIES.items():
        try:
            print(f"   📂 Категория: {category_name}")
            feed = feedparser.parse(category_url)
            
            if not feed.entries:
                print(f"   ⚠️ RSS пустой! Проверь URL: {category_url}")
                continue
                
            print(f"   📊 Найдено записей: {len(feed.entries)}")
            
            for entry in feed.entries:
                title = getattr(entry, "title", "")
                link = getattr(entry, "link", "")
                summary = getattr(entry, "summary", "")
                project_id = link or title
                
                print(f"      📌 {title[:40]}...")

                if project_id in fh_sent_projects:
                    print(f"      ⏭️ Уже отправлен")
                    continue

                text_for_filter = f"{title} {summary}"
                budget, currency = extract_budget_and_currency(text_for_filter)

                if min_budget and budget is not None and budget < min_budget:
                    print(f"      ⏭️ Бюджет {budget} < {min_budget}")
                    continue

                if enabled_keywords and not matches_keywords(text_for_filter, enabled_keywords):
                    print(f"      ⏭️ Нет ключевых слов")
                    continue

                print(f"      ✅ ОТПРАВЛЯЮ!")
                
                category = detect_fh_category(text_for_filter)
                fh_sent_projects.add(project_id)
                
                stats["orders_found"] += 1
                stats["freelancehunt"] += 1

                pending_orders[project_id] = {
                    "title": title,
                    "description": summary,
                    "category": category
                }

                ai_response = generate_ai_response(title, summary, category)
                ai_responses_cache[project_id] = ai_response
                stats["ai_generated"] += 1

                message_text = format_freelancehunt_message(
                    title, summary, category, budget, currency
                )

                result = send_telegram_message_with_ai_button(
                    message_text,
                    link,
                    project_id
                )
                if result:
                    print(f"      ✅ Отправлено в Telegram!")
                else:
                    print(f"      ❌ Не отправлено в Telegram")
                    
        except Exception as e:
            errors["freelancehunt"] += 1
            errors["last_errors"].append(f"Freelancehunt: {time.strftime('%H:%M')} - {str(e)[:30]}")
            print(f"   ❌ Ошибка {category_name}: {e}")
            import traceback
            traceback.print_exc()


def parse_kabanchik():
    config = ensure_config_exists()

    try:
        for url in KABANCHIK_URLS:
            try:
                response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            except requests.exceptions.Timeout:
                errors["kabanchik"] += 1
                errors["last_errors"].append(f"Kabanchik: {time.strftime('%H:%M')} - таймаут")
                print(f"DEBUG: Kabanchik timeout for {url}")
                continue
                
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
                stats["orders_found"] += 1
                stats["kabanchik"] += 1

                pending_orders[full_link] = {
                    "title": title,
                    "description": "Описание на сайте Kabanchik",
                    "category": category
                }

                ai_response = generate_ai_response(title, "Описание на сайте", category)
                ai_responses_cache[full_link] = ai_response
                stats["ai_generated"] += 1
                print(f"DEBUG: AI-ответ сгенерирован для Kabanchik: {title[:30]}...")

                message_text = format_kabanchik_message(
                    title, category, "Описание на сайте", None, ""
                )

                result = send_telegram_message_with_ai_button(
                    message_text,
                    full_link,
                    full_link
                )
                if result:
                    print(f"      ✅ Отправлено в Telegram!")
                else:
                    print(f"      ❌ Не отправлено в Telegram")
    except Exception as e:
        errors["kabanchik"] += 1
        errors["last_errors"].append(f"Kabanchik: {time.strftime('%H:%M')} - {str(e)[:30]}")
        print(f"DEBUG: parse_kabanchik error: {e}")


def handle_updates():
    offset = 0
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30",
                timeout=40
            )

            if r.status_code != 200:
                print(f"DEBUG: Ошибка getUpdates: {r.status_code}")
                time.sleep(5)
                continue

            updates = r.json().get("result", [])

            for u in updates:
                offset = max(offset, u["update_id"] + 1)

                if "message" in u:
                    message = u["message"]
                    text = message.get("text", "").strip()

                    if text == "/start":
                        send_telegram_message("🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n\nВыберите действие:", create_main_keyboard())
                    elif text == "/settings":
                        send_telegram_message("⚙️ <b>Настройки</b>", create_settings_keyboard())
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
                        send_telegram_message(get_status_message())

                elif "callback_query" in u:
                    cb = u["callback_query"]
                    data = cb["data"]
                    cid = cb["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    message_id = cb["message"]["message_id"]
                    config = ensure_config_exists()

                    if data == "open_settings":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        send_telegram_message("⚙️ <b>Настройки</b>", create_settings_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "⚙️ Настройки",
                            "show_alert": False
                        })

                    elif data == "open_budget":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        send_telegram_message("💰 <b>Выберите минимальный бюджет:</b>", create_budget_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "💰 Бюджет",
                            "show_alert": False
                        })

                    elif data == "open_keywords":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        send_telegram_message("🔍 <b>Выберите ключевое слово:</b>", create_keywords_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "🔍 Ключевые слова",
                            "show_alert": False
                        })

                    elif data == "back_to_settings":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        send_telegram_message("⚙️ <b>Настройки</b>", create_settings_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "⬅️ Назад",
                            "show_alert": False
                        })

                    elif data == "show_fh_categories":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        text = "📁 <b>Freelancehunt категории:</b>\n\n"
                        for cat, enabled in config["freelancehunt"]["categories"].items():
                            text += f"{'✅' if enabled else '❌'} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "📁 Freelancehunt",
                            "show_alert": False
                        })

                    elif data == "show_kb_categories":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        text = "📁 <b>Kabanchik категории:</b>\n\n"
                        for cat, enabled in config["kabanchik"]["categories"].items():
                            text += f"{'✅' if enabled else '❌'} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "📁 Kabanchik",
                            "show_alert": False
                        })

                    elif data.startswith("budget_"):
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        budget = int(data.replace("budget_", ""))
                        config["freelancehunt"]["min_budget"] = budget
                        save_config(config)
                        send_telegram_message(
                            f"✅ Минимальный бюджет установлен: ${budget}",
                            create_settings_keyboard()
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": f"✅ Бюджет ${budget}",
                            "show_alert": False
                        })

                    elif data.startswith("kw_"):
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
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
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "✅ Готово",
                            "show_alert": False
                        })

                    elif data == "reset_config":
                        telegram_api("deleteMessage", {
                            "chat_id": chat_id,
                            "message_id": message_id
                        })
                        config = get_default_config()
                        save_config(config)
                        send_telegram_message("🔄 Настройки сброшены", create_settings_keyboard())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "🔄 Сброшено",
                            "show_alert": False
                        })

                    elif data == "bot_status":
                        send_telegram_message(get_status_message())
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "📊 Статус бота",
                            "show_alert": False
                        })

                    elif data == "bot_help":
                        send_telegram_message(
                            "📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n"
                            "⚙️ Настройки\n"
                            "📊 Статус бота\n"
                            "❓ Help\n"
                            "🔄 Перезапуск",
                            create_main_keyboard()
                        )
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": cid,
                            "text": "❓ Help",
                            "show_alert": False
                        })

                    elif data == "bot_restart":
                        send_telegram_message("🔄 Перезапуск...", create_main_keyboard())
                        os._exit(0)

                    elif data == "close_settings":
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
            print("✅ GEMINI_API_KEY найден! AI-ответы будут генерироваться при находке заказа.")
        else:
            print("⚠️ GEMINI_API_KEY не задан! AI-ответы будут ШАБЛОННЫМИ.")

        ensure_config_exists()
        setup_bot_menu()

        threads = [
            Thread(target=run_web_server, daemon=True),
            Thread(target=monitor_freelancehunt, daemon=True),
            Thread(target=monitor_kabanchik, daemon=True),
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
