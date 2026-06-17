<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Кнопка Меню для Telegram бота</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Fraunces:wght@600;700&display=swap');

    :root{
      --bg:#111111;
      --panel:#1a1a1a;
      --panel-2:#222222;
      --text:#f4efe8;
      --muted:#b6aa9a;
      --line:#2f2a25;
      --accent:#f0b34a;
      --accent-2:#6fcf97;
      --shadow:0 24px 60px rgba(0,0,0,.35);
      --radius:24px;
    }

    *{box-sizing:border-box}
    html,body{margin:0;padding:0}
    body{
      min-height:100vh;
      background:
        radial-gradient(circle at top right, rgba(240,179,74,.12), transparent 22%),
        radial-gradient(circle at bottom left, rgba(111,207,151,.08), transparent 24%),
        var(--bg);
      color:var(--text);
      font-family:"Space Grotesk", sans-serif;
      padding:28px;
    }

    .wrap{
      max-width:1100px;
      margin:0 auto;
      display:grid;
      gap:24px;
    }

    .hero,.code{
      background:linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.015));
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      overflow:hidden;
      animation:fadeUp .7s ease both;
    }

    .hero{
      display:grid;
      grid-template-columns:1.1fr .9fr;
      gap:0;
    }

    .hero-copy{
      padding:34px;
    }

    .eyebrow{
      display:inline-block;
      color:var(--accent);
      text-transform:uppercase;
      letter-spacing:.18em;
      font-size:.8rem;
      font-weight:700;
      margin-bottom:14px;
    }

    h1{
      margin:0 0 14px;
      font-family:"Fraunces", serif;
      font-size:clamp(2rem,4vw,4.2rem);
      line-height:.95;
      letter-spacing:-.03em;
    }

    .hero p{
      margin:0;
      color:var(--muted);
      line-height:1.75;
      max-width:62ch;
    }

    .preview{
      border-left:1px solid var(--line);
      padding:28px;
      display:grid;
      place-items:center;
      background:
        linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,.01)),
        #141414;
    }

    .phone{
      width:min(100%, 340px);
      background:#0f0f10;
      border:1px solid #2d2d2f;
      border-radius:32px;
      padding:14px;
      box-shadow:0 30px 80px rgba(0,0,0,.45);
    }

    .phone-top{
      height:28px;
      display:flex;
      justify-content:center;
      align-items:center;
      color:#8c8c8c;
      font-size:.8rem;
      letter-spacing:.08em;
    }

    .screen{
      background:#1b1c1f;
      border-radius:24px;
      padding:16px;
      min-height:520px;
      position:relative;
      overflow:hidden;
    }

    .msg{
      width:82%;
      background:#2a2b30;
      border-radius:18px 18px 18px 8px;
      padding:12px 14px;
      color:#f3efe8;
      line-height:1.45;
      font-size:.92rem;
      box-shadow:0 10px 18px rgba(0,0,0,.18);
    }

    .input-zone{
      position:absolute;
      left:14px;
      right:14px;
      bottom:14px;
      background:#23242a;
      border:1px solid #34353b;
      border-radius:18px;
      min-height:54px;
      display:flex;
      align-items:center;
      gap:10px;
      padding:10px 12px;
    }

    .menu-btn{
      background:rgba(240,179,74,.12);
      color:var(--accent);
      border:1px solid rgba(240,179,74,.3);
      border-radius:12px;
      padding:8px 12px;
      font-weight:700;
      font-size:.9rem;
      white-space:nowrap;
    }

    .gif{
      color:#9ea0a8;
      font-size:.92rem;
      border:1px solid #3a3c43;
      border-radius:12px;
      padding:8px 10px;
    }

    .field{
      flex:1;
      color:#7f8490;
      font-size:.95rem;
    }

    .code-head{
      padding:18px 22px;
      border-bottom:1px solid #2a2722;
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:16px;
      background:#171717;
    }

    .code-head strong{
      font-size:.82rem;
      letter-spacing:.18em;
      text-transform:uppercase;
      color:var(--muted);
    }

    .chip{
      font-size:.78rem;
      padding:8px 12px;
      border-radius:999px;
      color:#111;
      background:var(--accent);
      font-weight:800;
    }

    pre{
      margin:0;
      padding:22px;
      overflow:auto;
      background:#101010;
      color:#f5efe5;
      font:500 14px/1.72 "Space Grotesk", sans-serif;
      white-space:pre-wrap;
      word-break:break-word;
    }

    .tip{
      padding:18px 22px 24px;
      border-top:1px solid var(--line);
      color:var(--muted);
      line-height:1.7;
      background:#151515;
    }

    @keyframes fadeUp{
      from{opacity:0;transform:translateY(18px)}
      to{opacity:1;transform:none}
    }

    @media (max-width:900px){
      .hero{grid-template-columns:1fr}
      .preview{border-left:0;border-top:1px solid var(--line)}
    }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="hero-copy">
        <span class="eyebrow">Telegram Bot UI</span>
        <h1>Кнопка «Меню» слева возле GIF</h1>
        <p>
          Для этого нужна не inline-кнопка в сообщении, а <b>кнопка меню у поля ввода</b> через Telegram Bot API.
          Она появляется внутри бота рядом с системными кнопками, если задать команду меню через <b>MenuButtonCommands</b>.
        </p>
      </div>

      <div class="preview">
        <div class="phone">
          <div class="phone-top">TELEGRAM</div>
          <div class="screen">
            <div class="msg">Привет. Нажми <b>Меню</b>, чтобы открыть команды бота.</div>

            <div class="input-zone">
              <div class="menu-btn">Меню</div>
              <div class="gif">GIF</div>
              <div class="field">Сообщение</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="code">
      <div class="code-head">
        <strong>Полный bot.py с кнопкой меню</strong>
        <span class="chip">Готово</span>
      </div>
<pre>import time
import requests
import feedparser
import json
import os
import re
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

FH_RSS_URL = "https://freelancehunt.com/projects.rss?skills%5B%5D=113&amp;skills%5B%5D=192&amp;skills%5B%5D=144&amp;skills%5B%5D=101&amp;skills%5B%5D=18&amp;skills%5B%5D=91"
FH_INTERVAL = 60

KABANCHIK_URLS = [
    "https://kabanchik.ua/projects/category/ai-poslugi",
    "https://kabanchik.ua/projects/category/foto-i-video-posluhy",
    "https://kabanchik.ua/projects/category/roboty-v-interneti",
]
KABANCHIK_INTERVAL = 30

CONFIG_FILE = "config.json"


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


def telegram_api(method, payload):
    if not BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            print(f"Ошибка Telegram API ({method}): {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"Ошибка Telegram API ({method}): {e}")
        return None


def setup_bot_menu():
    commands = [
        {"command": "settings", "description": "Открыть настройки"},
        {"command": "status", "description": "Статус бота"},
        {"command": "help", "description": "Справка"},
    ]

    telegram_api("setMyCommands", {"commands": commands})

    telegram_api("setChatMenuButton", {
        "chat_id": CHAT_ID,
        "menu_button": {
            "type": "commands"
        }
    })


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
    text = "⚙️ &lt;b&gt;НАСТРОЙКИ БОТА&lt;/b&gt;\n\n"

    text += "📁 &lt;b&gt;FREELANCEHUNT КАТЕГОРИИ:&lt;/b&gt;\n"
    for cat, enabled in config["freelancehunt"]["categories"].items():
        status = "✅" if enabled else "❌"
        text += f"{status} {cat}\n"

    text += f"\n💰 &lt;b&gt;МИНИМАЛЬНЫЙ БЮДЖЕТ:&lt;/b&gt; ${config['freelancehunt']['min_budget']}\n"

    text += "\n🔍 &lt;b&gt;КЛЮЧЕВЫЕ СЛОВА:&lt;/b&gt;\n"
    text += ", ".join(config["freelancehunt"]["keywords"]) + "\n"

    text += "\n📁 &lt;b&gt;KABANCHIK КАТЕГОРИИ:&lt;/b&gt;\n"
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
    return text.replace("&amp;", "&amp;amp;").replace("&lt;", "&amp;lt;").replace("&gt;", "&amp;gt;").replace("&", "&amp;").replace("&amp;amp;", "&amp;").replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;")


def send_telegram_message(text, reply_markup=None):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN или CHAT_ID не заданы")
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
        print("BOT_TOKEN или CHAT_ID не заданы")
        return

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

    telegram_api("sendMessage", payload)


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
        for word in words:
            if word in text_low:
                return category

    return "Без категории"


def format_freelancehunt_message(title, summary, category, budget=None):
    budget_text = f"{budget}" if budget else "Не указана"
    return (
        f"🟡 &lt;b&gt;Freelancehunt&lt;/b&gt;\n\n"
        f"{clean_html_text(title)}\n\n"
        f"🏷 Категория\n"
        f"{clean_html_text(category)}\n\n"
        f"💰 {clean_html_text(budget_text)}\n\n"
        f"📝 Описание\n"
        f"{clean_html_text(summary[:900])}"
    )


def format_kabanchik_message(title, category, description="Описание на сайте Kabanchik", budget=None):
    budget_text = f"{budget}" if budget else "Не указана"
    return (
        f"🟢 &lt;b&gt;Kabanchik&lt;/b&gt;\n\n"
        f"{clean_html_text(title)}\n\n"
        f"🏷 Категория\n"
        f"{clean_html_text(category)}\n\n"
        f"💰 {clean_html_text(budget_text)}\n\n"
        f"📝 Описание\n"
        f"{clean_html_text(description)}"
    )


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

            if min_budget and budget &lt; min_budget:
                continue

            if enabled_keywords and not matches_keywords(text_for_filter, enabled_keywords):
                continue

            category = detect_fh_category(text_for_filter)

            fh_sent_projects.add(project_id)

            msg = format_freelancehunt_message(title, summary, category, budget if budget else None)
            send_telegram_message_with_button(msg, "🔗 Открыть проект", link)

    except Exception as e:
        print(f"Ошибка парсинга Freelancehunt: {e}")


def parse_kabanchik():
    config = ensure_config_exists()

    try:
        for url in KABANCHIK_URLS:
            response = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=True)

            for a in links:
                href = a["href"]
                title = a.get_text(" ", strip=True)

                if not title or len(title) &lt; 5:
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

                if "ai-poslugi" in url:
                    category = "AI услуги"
                elif "foto-i-video-posluhy" in url:
                    category = "Фото и видео услуги"
                elif "roboty-v-interneti" in url:
                    category = "Работы в интернете"
                else:
                    category = "Без категории"

                kabanchik_sent_tasks.add(task_id)

                msg = format_kabanchik_message(title, category, "Описание на сайте Kabanchik", None)
                send_telegram_message_with_button(msg, "🔗 Открыть задачу", full_link)

    except Exception as e:
        print(f"Ошибка парсинга Kabanchik: {e}")


def handle_updates():
    offset = 0
    ensure_config_exists()

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&amp;timeout=30"
            response = requests.get(url, timeout=40)
            updates = response.json().get("result", [])

            for update in updates:
                offset = max(offset, update["update_id"] + 1)

                if "message" in update:
                    message = update["message"]
                    text = message.get("text", "").lower()

                    if text == "/start":
                        send_telegram_message(
                            "Привет! Нажми кнопку Menu возле поля ввода или используй команды:\n/settings\n/status\n/help"
                        )

                    elif text == "/settings":
                        config = ensure_config_exists()
                        send_telegram_message(get_settings_text(config), create_settings_keyboard(config))

                    elif text == "/help":
                        help_text = (
                            "📚 &lt;b&gt;ДОСТУПНЫЕ КОМАНДЫ:&lt;/b&gt;\n\n"
                            "/settings - Открыть настройки\n"
                            "/help - Эта справка\n"
                            "/status - Статус бота"
                        )
                        send_telegram_message(help_text)

                    elif text == "/status":
                        config = ensure_config_exists()
                        status_text = "✅ &lt;b&gt;БОТ РАБОТАЕТ&lt;/b&gt;\n\n"
                        status_text += f"💰 Бюджет: ${config['freelancehunt']['min_budget']}\n"
                        status_text += f"🔍 Ключевые слова: {', '.join(config['freelancehunt']['keywords'])}\n"
                        send_telegram_message(status_text)

                elif "callback_query" in update:
                    callback = update["callback_query"]
                    callback_id = callback["id"]
                    data = callback["data"]
                    config = ensure_config_exists()

                    if data == "open_settings":
                        send_telegram_message(get_settings_text(config), create_settings_keyboard(config))

                    elif data == "open_budget":
                        send_telegram_message("💰 &lt;b&gt;Выберите минимальный бюджет:&lt;/b&gt;", create_budget_keyboard())

                    elif data == "open_keywords":
                        send_telegram_message("🔍 &lt;b&gt;Выберите ключевое слово:&lt;/b&gt;", create_keywords_keyboard())

                    elif data == "back_to_settings":
                        send_telegram_message(get_settings_text(config), create_settings_keyboard(config))

                    elif data == "show_fh_categories":
                        text = "📁 &lt;b&gt;Freelancehunt категории:&lt;/b&gt;\n\n"
                        for cat, enabled in config["freelancehunt"]["categories"].items():
                            status = "✅" if enabled else "❌"
                            text += f"{status} {cat}\n"
                        send_telegram_message(text, create_settings_keyboard(config))

                    elif data == "show_kb_categories":
                        text = "📁 &lt;b&gt;Kabanchik категории:&lt;/b&gt;\n\n"
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

                    elif data == "reset_config":
                        config = get_default_config()
                        save_config(config)
                        send_telegram_message("🔄 Настройки сброшены", create_settings_keyboard(config))

                    elif data == "close_settings":
                        telegram_api("answerCallbackQuery", {
                            "callback_query_id": callback_id,
                            "text": "Меню закрыто"
                        })
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
    setup_bot_menu()
    print("Бот запущен")

    Thread(target=run_web_server, daemon=True).start()
    Thread(target=monitor_freelancehunt, daemon=True).start()
    Thread(target=monitor_kabanchik, daemon=True).start()
    Thread(target=handle_updates, daemon=True).start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()</pre>
      <div class="tip">
        Важное: это не обычная кнопка в сообщении. Это кнопка меню Telegram у поля ввода.  
        Если хотите, следующим сообщением я пришлю <b>чистый обычный Python-файл `bot.py` без HTML-обёртки</b>, тоже свернутым кодом.
      </div>
    </section>
  </main>
</body>
</html>
