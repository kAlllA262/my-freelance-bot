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

KABANCHIK_EMAIL = os.environ.get("KABANCHIK_EMAIL")
KABANCHIK_PASSWORD = os.environ.get("KABANCHIK_PASSWORD")

template = {
    "price": 500,
    "deadline": 3,
    "style": "Профессиональный",
    "extra_text": "Могу предоставить портфолио по запросу."
}

waiting_for_template_input = False
template_input_type = None

# ========== KABANCHIK (ВАШИ ССЫЛКИ) ==========
KABANCHIK_BASE_URL = "https://kabanchik.ua"
KABANCHIK_LOGIN_URL = "https://kabanchik.ua/ua/login"
KABANCHIK_URLS = [
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/ai-poslugi",
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/dyzain",
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/foto-i-video-posluhy"
]
KABANCHIK_CATEGORY_NAMES = {
    "ai-poslugi": "AI услуги",
    "dyzain": "Дизайн",
    "foto-i-video-posluhy": "Фото и видео услуги"
}

# ========== FREELANCEHUNT ==========
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

# ========== WEBLANCER ==========
WEBLANCER_URL = "https://www.weblancer.net/projects/"
WEBLANCER_KEYWORDS = ["монтаж видео", "видеомонтаж", "анимация", "after effects", "davinci resolve"]

# ========== НАСТРОЙКИ ==========
CONFIG_FILE = "config.json"
FH_INTERVAL = 60
KABANCHIK_INTERVAL = 60
WEBLANCER_INTERVAL = 60

fh_sent = set()
kabanchik_sent = set()
weblancer_sent = set()
pending_orders = {}
ai_cache = {}
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

errors = {"freelancehunt": 0, "kabanchik": 0, "weblancer": 0, "gemini": 0, "telegram": 0, "last_errors": []}
check_stats = {
    "freelancehunt": {"last_check": None, "last_count": 0, "total_checks": 0, "categories": {}},
    "kabanchik": {"last_check": None, "last_count": 0, "total_checks": 0, "categories": {}},
    "weblancer": {"last_check": None, "last_count": 0, "total_checks": 0, "keywords": {}}
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
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=20)
        if r.status_code != 200:
            print(f"Telegram API error {method}: {r.status_code}")
            return None
        return r.json()
    except Exception as e:
        print(f"Telegram API exception {method}: {e}")
        return None

def send_telegram_message(text, reply_markup=None):
    if not BOT_TOKEN or not CHAT_ID:
        return None
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = telegram_api("sendMessage", payload)
    if result is None:
        log_error("telegram", "не удалось отправить сообщение")
    else:
        print(f"Сообщение отправлено! ID: {result.get('result', {}).get('message_id', 'unknown')}")
    return result

def send_telegram_message_with_buttons(text, button_url, project_id):
    if not BOT_TOKEN or not CHAT_ID:
        return None
    short_id = get_short_id(project_id)
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 Открыть", "url": button_url.strip()}, {"text": "💼 Откликнуться", "callback_data": f"bid_{short_id}"}]
        ]
    }
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "reply_markup": keyboard}
    result = telegram_api("sendMessage", payload)
    if result is None:
        log_error("telegram", "не удалось отправить кнопку")
    else:
        stats["orders_sent"] += 1
    return result

def generate_ai_bid(project_title, project_description, project_category):
    if not GEMINI_API_KEY:
        return f"Здравствуйте! Меня заинтересовал ваш заказ «{project_title}». Я специализируюсь в области {project_category} и имею успешный опыт. Буду рад обсудить детали."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        prompt = f"Напиши отклик фрилансера на заказ: {project_title}. Описание: {project_description[:300]}. Стиль: {template['style']}. Доп. текст: {template['extra_text']}. Ответ: 3-5 предложений."
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if text:
                return text.strip()
    except:
        pass
    return f"Здравствуйте! Меня заинтересовал ваш заказ «{project_title}». Я специализируюсь в области {project_category}. Буду рад обсудить детали."

def send_bid(project_id, price, deadline, comment):
    if not FH_API_TOKEN:
        return {"status": "error", "message": "❌ FH_API_TOKEN не настроен"}
    try:
        match = re.search(r'/(\d+)/?', project_id)
        if not match:
            return {"status": "error", "message": "❌ Не удалось определить ID"}
        project_id_clean = match.group(1)
        url = "https://api.freelancehunt.com/v2/bids"
        headers = {"Authorization": f"Bearer {FH_API_TOKEN}", "Content-Type": "application/json"}
        data = {"project_id": int(project_id_clean), "price": price, "deadline": deadline, "comment": comment}
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code in [200, 201]:
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"Ошибка {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def clean_html_text(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def extract_budget_and_currency(text):
    if not text:
        return None, ""
    patterns = [r'(\d[\d\s]*)\s*(₴|грн|uah|usd|\$|€|eur)', r'(₴|грн|uah|usd|\$|€|eur)\s*(\d[\d\s]*)']
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            if m.group(1).replace(" ", "").isdigit():
                return int(m.group(1).replace(" ", "")), m.group(2).upper()
            else:
                return int(m.group(2).replace(" ", "")), m.group(1).upper()
    m = re.search(r'(\d[\d\s]*)', text)
    if m:
        try:
            return int(m.group(1).replace(" ", "")), ""
        except:
            return None, ""
    return None, ""

def matches_keywords(text, keywords):
    if not text:
        return False
    return any(kw.lower() in text.lower() for kw in keywords)

def detect_fh_category(text):
    text_low = text.lower()
    category_map = {
        "AI создание видео": ["ai", "нейросеть", "генерация видео"],
        "Анимация": ["анимация", "motion", "2d", "3d"],
        "Аудио/видео монтаж": ["монтаж", "видеомонтаж", "нарезка", "склейка"],
        "Видео реклама": ["рекламный ролик", "видеореклама", "промо"],
        "Обработка аудио": ["аудио", "звук", "обработка звука"],
        "Обработка видео": ["обработка видео", "цветокор", "color grading"],
        "Обработка фото": ["обработка фото", "ретушь", "photoshop"],
        "Услуги диктора": ["диктор", "озвучка", "voice over"]
    }
    for category, words in category_map.items():
        if any(word in text_low for word in words):
            return category
    return "Без категории"

def format_quote(text):
    lines = text.split('\n')
    return '\n'.join([f"> {line}" for line in lines if line.strip()]) if lines else "> (описание отсутствует)"

def format_freelancehunt_message(title, summary, category, budget=None, currency=""):
    budget_text = f"{budget} {currency}".strip() if budget else "Не указана"
    return f"""🟡 <b>Freelancehunt</b>

📌 <b>{clean_html_text(title)}</b>

🏷 Категория: <code>{category}</code>
💰 Бюджет: {budget_text}

📝 Описание:
{format_quote(clean_html_text(summary[:500]))}"""

def format_kabanchik_message(title, description, category, budget=None, currency=""):
    budget_text = f"{budget} {currency}".strip() if budget else "Не указана"
    return f"""🟢 <b>Kabanchik</b>

📌 <b>{clean_html_text(title)}</b>

🏷 Категория: <code>{category}</code>
💰 Бюджет: {budget_text}

📝 Описание:
{format_quote(clean_html_text(description[:500]))}"""

def format_weblancer_message(title, description, budget_text):
    return f"""🟣 <b>Weblancer</b>

📌 <b>{clean_html_text(title)}</b>

💰 Бюджет: {budget_text}

📝 Описание:
{format_quote(clean_html_text(description[:500]))}"""

def get_uptime():
    diff = time.time() - stats["start_time"]
    return f"{int(diff // 3600)} ч {int((diff % 3600) // 60)} мин"

def get_status_message():
    total_errors = sum([errors["freelancehunt"], errors["kabanchik"], errors["weblancer"], errors["gemini"], errors["telegram"]])
    status = "✅ БОТ РАБОТАЕТ" if total_errors < 10 else "⚠️ БОТ РАБОТАЕТ С ОШИБКАМИ"
    error_lines = []
    if errors["freelancehunt"] > 0: error_lines.append(f"• Freelancehunt: {errors['freelancehunt']} ошибок")
    if errors["kabanchik"] > 0: error_lines.append(f"• Kabanchik: {errors['kabanchik']} ошибок")
    if errors["weblancer"] > 0: error_lines.append(f"• Weblancer: {errors['weblancer']} ошибок")
    if errors["gemini"] > 0: error_lines.append(f"• Gemini: {errors['gemini']} ошибок")
    if errors["telegram"] > 0: error_lines.append(f"• Telegram: {errors['telegram']} ошибок")
    if not error_lines: error_lines.append("• Ошибок нет ✅")
    last_errors = "\n".join([f"• {e}" for e in errors["last_errors"][-3:]]) if errors["last_errors"] else "• Нет"
    
    checks_lines = []
    fh = check_stats["freelancehunt"]
    if fh["last_check"]:
        checks_lines.append(f"> <b>Freelancehunt:</b> {fh['last_check']} (найдено: {fh['last_count']})")
    else:
        checks_lines.append("> Freelancehunt: ожидание...")
    kb = check_stats["kabanchik"]
    if kb["last_check"]:
        checks_lines.append(f"> <b>Kabanchik:</b> {kb['last_check']} (найдено: {kb['last_count']})")
    else:
        checks_lines.append("> Kabanchik: ожидание...")
    wl = check_stats["weblancer"]
    if wl["last_check"]:
        checks_lines.append(f"> <b>Weblancer:</b> {wl['last_check']} (найдено: {wl['last_count']})")
    else:
        checks_lines.append("> Weblancer: ожидание...")
    
    return f"""📊 <b>СТАТУС БОТА</b>

{status}

📋 Статистика:
• Всего найдено: {stats['orders_found']}
• Freelancehunt: {stats['freelancehunt']}
• Kabanchik: {stats['kabanchik']}
• Weblancer: {stats['weblancer']}
• Отправлено: {stats['orders_sent']}
• AI ответов: {stats['ai_generated']}

🔄 Проверки:
{chr(10).join(checks_lines)}

⚠️ Ошибки:
{chr(10).join(error_lines)}

📌 Последние ошибки:
{last_errors}

⏱ Работает: {get_uptime()}"""

def login_to_kabanchik():
    global kabanchik_session
    try:
        if not KABANCHIK_EMAIL or not KABANCHIK_PASSWORD:
            print("❌ Нет данных для входа")
            return False
        print("🔐 Вход на Kabanchik...")
        kabanchik_session = requests.Session()
        kabanchik_session.headers.update({"User-Agent": "Mozilla/5.0"})
        response = kabanchik_session.get(KABANCHIK_LOGIN_URL, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "_token"})
        csrf = token.get("value") if token else ""
        data = {"email": KABANCHIK_EMAIL, "password": KABANCHIK_PASSWORD, "_token": csrf, "remember": "1"}
        response = kabanchik_session.post(KABANCHIK_LOGIN_URL, data=data, timeout=30, allow_redirects=True)
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
    total = 0
    for url in KABANCHIK_URLS:
        try:
            category = "Неизвестно"
            for slug, name in KABANCHIK_CATEGORY_NAMES.items():
                if slug in url:
                    category = name
                    break
            print(f"📂 {category}: {url}")
            response = kabanchik_session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"❌ Ошибка: {response.status_code}")
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("div", class_="project-item") or soup.find_all("div", class_="order-item") or soup.find_all("div", class_="task-item")
            count = 0
            for item in items:
                title_elem = item.find("a", class_="title") or item.find("h3") or item.find("h2")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link_elem = title_elem if title_elem.name == "a" else title_elem.find("a")
                link = "https://kabanchik.ua" + link_elem.get("href") if link_elem and link_elem.get("href") else ""
                desc_elem = item.find("div", class_="description") or item.find("p")
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                if not link or link in kabanchik_sent:
                    continue
                kabanchik_sent.add(link)
                stats["orders_found"] += 1
                stats["kabanchik"] += 1
                count += 1
                total += 1
                msg = format_kabanchik_message(title, description, category)
                keyboard = {"inline_keyboard": [[{"text": "🔗 Открыть", "url": link}]]}
                send_telegram_message(msg, keyboard)
                print(f"✅ {title[:50]}...")
            update_check_stats("kabanchik", category, count)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            log_error("kabanchik", str(e)[:30])
    check_stats["kabanchik"]["last_count"] = total
    print(f"📊 Kabanchik: найдено {total}")

def parse_freelancehunt():
    print("🔍 Парсинг Freelancehunt...")
    config = load_config() or get_default_config()
    keywords = config.get("freelancehunt", {}).get("keywords", [])
    min_budget = config.get("freelancehunt", {}).get("min_budget", 0)
    total = 0
    for key, url in FH_CATEGORIES.items():
        try:
            category = FH_CATEGORY_NAMES.get(key, key)
            print(f"📂 {category}")
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                project_id = link or title
                if project_id in fh_sent:
                    continue
                text = f"{title} {summary}"
                budget, currency = extract_budget_and_currency(text)
                if min_budget and budget and budget < min_budget:
                    continue
                if keywords and not matches_keywords(text, keywords):
                    continue
                fh_sent.add(project_id)
                stats["orders_found"] += 1
                stats["freelancehunt"] += 1
                count += 1
                total += 1
                cat = detect_fh_category(text)
                pending_orders[project_id] = {"title": title, "description": summary, "category": cat, "link": link}
                bid = generate_ai_bid(title, summary, cat)
                ai_cache[project_id] = bid
                stats["ai_generated"] += 1
                msg = format_freelancehunt_message(title, summary, cat, budget, currency)
                send_telegram_message_with_buttons(msg, link, project_id)
                print(f"✅ {title[:50]}...")
            update_check_stats("freelancehunt", category, count)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            log_error("freelancehunt", str(e)[:30])
    check_stats["freelancehunt"]["last_count"] = total
    print(f"📊 Freelancehunt: найдено {total}")

def parse_weblancer():
    print("🔍 Парсинг Weblancer...")
    config = load_config() or get_default_config()
    keywords = config.get("freelancehunt", {}).get("keywords", [])
    min_budget = config.get("freelancehunt", {}).get("min_budget", 0)
    total = 0
    for keyword in WEBLANCER_KEYWORDS[:5]:
        try:
            url = f"{WEBLANCER_URL}?q={keyword.replace(' ', '+')}"
            response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            projects = soup.find_all("div", class_="col-sm-12") or soup.find_all("div", class_="row")
            count = 0
            for project in projects:
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
                if project_id in weblancer_sent:
                    continue
                text = f"{title} {description}"
                budget, _ = extract_budget_and_currency(budget_text)
                if min_budget and budget and budget < min_budget:
                    continue
                if keywords and not matches_keywords(text, keywords):
                    continue
                weblancer_sent.add(project_id)
                stats["orders_found"] += 1
                stats["weblancer"] += 1
                count += 1
                total += 1
                msg = format_weblancer_message(title, description, budget_text)
                keyboard = {"inline_keyboard": [[{"text": "🔗 Открыть", "url": link}]]}
                send_telegram_message(msg, keyboard)
                print(f"✅ {title[:50]}...")
            update_check_stats("weblancer", keyword, count)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    check_stats["weblancer"]["last_count"] = total
    print(f"📊 Weblancer: найдено {total}")

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
            "keywords": ["монтаж", "видеомонтаж", "анимация", "after effects", "davinci resolve"]
        },
        "kabanchik": {
            "categories": {"AI услуги": True, "Дизайн": True, "Фото и видео услуги": True},
            "min_budget": 0
        }
    }

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return None

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def ensure_config_exists():
    c = load_config()
    if not c:
        c = get_default_config()
        save_config(c)
    return c

def setup_bot_menu():
    telegram_api("setMyCommands", {
        "commands": [
            {"command": "start", "description": "🏠 Главное меню"},
            {"command": "status", "description": "📊 Статус бота"},
            {"command": "help", "description": "❓ Помощь"}
        ]
    })

def handle_updates():
    global waiting_for_template_input, template_input_type
    offset = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30", timeout=40)
            if r.status_code != 200:
                time.sleep(5)
                continue
            updates = r.json().get("result", [])
            for u in updates:
                offset = max(offset, u["update_id"] + 1)
                if "message" in u:
                    msg = u["message"]
                    text = msg.get("text", "").strip()
                    if text == "/start":
                        keyboard = {"inline_keyboard": [[{"text": "📊 Статус", "callback_data": "bot_status"}, {"text": "❓ Help", "callback_data": "bot_help"}]]}
                        send_telegram_message("🏠 <b>ГЛАВНОЕ МЕНЮ</b>", keyboard)
                    elif text == "/status":
                        send_telegram_message(get_status_message())
                    elif text == "/help":
                        keyboard = {"inline_keyboard": [[{"text": "📊 Статус", "callback_data": "bot_status"}, {"text": "🏠 Главное меню", "callback_data": "show_main_menu"}]]}
                        send_telegram_message("📚 <b>ПОМОЩЬ</b>\n\nБот ищет заказы на Kabanchik, Freelancehunt и Weblancer", keyboard)
                elif "callback_query" in u:
                    cb = u["callback_query"]
                    data = cb["data"]
                    cid = cb["id"]
                    if data == "bot_status":
                        send_telegram_message(get_status_message())
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cid})
                    elif data == "bot_help":
                        keyboard = {"inline_keyboard": [[{"text": "📊 Статус", "callback_data": "bot_status"}, {"text": "🏠 Главное меню", "callback_data": "show_main_menu"}]]}
                        send_telegram_message("📚 <b>ПОМОЩЬ</b>\n\nБот ищет заказы на Kabanchik, Freelancehunt и Weblancer", keyboard)
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cid})
                    elif data == "show_main_menu":
                        keyboard = {"inline_keyboard": [[{"text": "📊 Статус", "callback_data": "bot_status"}, {"text": "❓ Help", "callback_data": "bot_help"}]]}
                        send_telegram_message("🏠 <b>ГЛАВНОЕ МЕНЮ</b>", keyboard)
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cid})
                    elif data.startswith("bid_"):
                        short_id = data.replace("bid_", "")
                        project_id = None
                        for pid in pending_orders.keys():
                            if get_short_id(pid) == short_id:
                                project_id = pid
                                break
                        if project_id and project_id in pending_orders:
                            order = pending_orders[project_id]
                            bid = ai_cache.get(project_id, generate_ai_bid(order["title"], order["description"], order["category"]))
                            ai_cache[project_id] = bid
                            msg = f"📤 <b>ОТКЛИК</b>\n\n📌 {order['title']}\n💰 {template['price']} UAH\n📅 {template['deadline']} дня\n\n{bid}"
                            keyboard = {"inline_keyboard": [[{"text": "✅ Отправить", "callback_data": f"send_{short_id}"}, {"text": "❌ Отмена", "callback_data": f"cancel_{short_id}"}]]}
                            send_telegram_message(msg, keyboard)
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cid, "text": "📝 Отклик готов!"})
                    elif data.startswith("send_"):
                        short_id = data.replace("send_", "")
                        project_id = None
                        for pid in pending_orders.keys():
                            if get_short_id(pid) == short_id:
                                project_id = pid
                                break
                        if project_id and project_id in pending_orders:
                            order = pending_orders[project_id]
                            bid = ai_cache.get(project_id, "")
                            result = send_bid(project_id, template['price'], template['deadline'], bid)
                            if result["status"] == "success":
                                send_telegram_message(f"✅ <b>ОТКЛИК ОТПРАВЛЕН!</b>\n\n📌 {order['title']}")
                            else:
                                send_telegram_message(f"❌ <b>Ошибка:</b> {result.get('message', 'Неизвестная ошибка')}")
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cid})
                    elif data.startswith("cancel_"):
                        send_telegram_message("❌ Отменено")
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cid})
        except Exception as e:
            print(f"Ошибка handle_updates: {e}")
            time.sleep(5)

def monitor_kabanchik():
    while True:
        parse_kabanchik()
        time.sleep(KABANCHIK_INTERVAL)

def monitor_freelancehunt():
    while True:
        parse_freelancehunt()
        time.sleep(FH_INTERVAL)

def monitor_weblancer():
    while True:
        parse_weblancer()
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
        except:
            pass
        if GEMINI_API_KEY:
            print("✅ GEMINI_API_KEY найден")
        if FH_API_TOKEN:
            print("✅ FH_API_TOKEN найден")
        if KABANCHIK_EMAIL and KABANCHIK_PASSWORD:
            print("✅ Данные Kabanchik найдены")
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
        print("✅ Все потоки запущены")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        try:
            send_telegram_message(f"❌ Бот упал: {str(e)[:200]}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
