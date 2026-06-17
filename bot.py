import time
import requests
import feedparser
import json
import os
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== НАСТРОЙКИ ====================
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Настройки для Freelancehunt (Видео категории)
# Аудио видео монтаж=113, AI создание видео=192, Видео реклама=144, 
# Обработка видео=101, Обработка фото=18, Анимация=91
FH_RSS_URL = "https://freelancehunt.com/projects.rss?skills%5B%5D=113&skills%5B%5D=192&skills%5B%5D=144&skills%5B%5D=101&skills%5B%5D=18&skills%5B%5D=91"
FH_INTERVAL = 60  # Проверка раз в минуту

# Настройки для Кабанчика (публичные ссылки)
KABANCHIK_URLS = [
    "https://kabanchik.ua/projects/category/ai-poslugi",
    "https://kabanchik.ua/projects/category/foto-i-video-posluhy",
    "https://kabanchik.ua/projects/category/roboty-v-interneti",
]
KABANCHIK_INTERVAL = 30  # Пауза между полными кругами проверок всех категорий

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
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckServer)
    server.serve_forever()

fh_sent_projects = set()
kabanchik_sent_tasks = set()

def load_config():
    """Загружает конфиг из JSON файла"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки конфига: {e}")
    return None

def save_config(config):
    """Сохраняет конфиг в JSON файл"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Ошибка сохранения конфига: {e}")
        return False

def get_settings_text(config):
    """Генерирует текст с текущими настройками"""
    text = "⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n"
    
    # Freelancehunt категории
    text += "📁 <b>FREELANCEHUNT КАТЕГОРИИ:</b>\n"
    for cat, enabled in config['freelancehunt']['categories'].items():
        status = "☑️" if enabled else "☐"
        text += f"{status} {cat}\n"
    
    text += f"\n💰 <b>МИНИМАЛЬНЫЙ БЮДЖЕТ:</b> ${config['freelancehunt']['min_budget']}\n"
    
    text += f"\n🔍 <b>КЛЮЧЕВЫЕ СЛОВА:</b>\n"
    keywords = ", ".join(config['freelancehunt']['keywords'])
    text += f"<code>{keywords}</code>\n"
    
    # Kabanchik категории
    text += "\n📁 <b>KABANCHIK КАТЕГОРИИ:</b>\n"
    for cat, enabled in config['kabanchik']['categories'].items():
        status = "☑️" if enabled else "☐"
        text += f"{status} {cat}\n"
    
    return text

def create_settings_keyboard(config):
    """Создаёт клавиатуру с кнопками категорий"""
    keyboard = {
        "inline_keyboard": []
    }
    
    # Freelancehunt категории
    for cat in config['freelancehunt']['categories'].keys():
        status = "✅" if config['freelancehunt']['categories'][cat] else "❌"
        keyboard["inline_keyboard"].append([
            {
                "text": f"{status} {cat}",
                "callback_data": f"toggle_fh_{cat}"
            }
        ])
    
    # Kabanchik категории
    keyboard["inline_keyboard"].append([{"text": "────────────────", "callback_data": "dummy"}])
    for cat in config['kabanchik']['categories'].keys():
        status = "✅" if config['kabanchik']['categories'][cat] else "❌"
        keyboard["inline_keyboard"].append([
            {
                "text": f"{status} KB: {cat}",
                "callback_data": f"toggle_kb_{cat}"
            }
        ])
    
    # Кнопки управления
    keyboard["inline_keyboard"].append([{"text": "────────────────", "callback_data": "dummy"}])
    keyboard["inline_keyboard"].append([
        {"text": "🔄 Сброс", "callback_data": "reset_config"},
        {"text": "❌ Закрыть", "callback_data": "close_settings"}
    ])
    
    return keyboard

def clean_html_text(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send_telegram_message(text, reply_markup=None):
    """Отправляет сообщение в Telegram"""
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
    """Слушает обновления от Telegram (команды и callback)"""
    offset = 0
    config = load_config()
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url)
            updates = response.json().get('result', [])
            
            for update in updates:
                offset = max(offset, update['update_id'] + 1)
                
                # Обработка команд
                if 'message' in update:
                    message = update['message']
                    text = message.get('text', '').lower()
                    
                    if text == '/settings':
                        config = load_config()
                        settings_text = get_settings_text(config)
                        keyboard = create_settings_keyboard(config)
                        send_telegram_message(settings_text, keyboard)
                        print("✅ Меню /settings отправлено")
                    
                    elif text == '/help':
                        help_text = """
📚 <b>ДОСТУПНЫЕ КОМАНДЫ:</b>

/settings - Открыть настройки категорий
/help - Эта справка
/status - Статус бота

<b>В меню настроек:</b>
- Нажимай на категорию чтобы включить/выключить
- 🔄 Сброс - вернуть дефолтные настройки
- ❌ Закрыть - закрыть меню
"""
                        send_telegram_message(help_text)
                        print("✅ Справка отправлена")
                
                # Обработка кликов на кнопки
                elif 'callback_query' in update:
                    callback = update['callback_query']
                    callback_id = callback['id']
                    data = callback['data']
                    
                    config = load_config()
                    
                    # Переключение категорий Freelancehunt
                    if data.startswith('toggle_fh_'):
                        cat_name = data.replace('toggle_fh_', '')
                        if cat_name in config['freelancehunt']['categories']:
                            config['freelancehunt']['categories'][cat_name] = not config['freelancehunt']['categories'][cat_name]
                            save_config(config)
                            print(f"✅ Freelancehunt: {cat_name} -> {config['freelancehunt']['categories'][cat_name]}")
                    
                    # Переключение категорий Kabanchik
                    elif data.startswith('toggle_kb_'):
                        cat_name = data.replace('toggle_kb_', '')
                        if cat_name in config['kabanchik']['categories']:
                            config['kabanchik']['categories'][cat_name] = not config['kabanchik']['categories'][cat_name]
                            save_config(config)
                            print(f"✅ Kabanchik: {cat_name} -> {config['kabanchik']['categories'][cat_name]}")
                    
                    # Сброс конфига
                    elif data == 'reset_config':
                        config = load_config()
                        for cat in config['freelancehunt']['categories']:
                            config['freelancehunt']['categories'][cat] = True
                        for cat in config['kabanchik']['categories']:
                            config['kabanchik']['categories'][cat] = True
                        config['freelancehunt']['min_budget'] = 0
                        save_config(config)
                        print("✅ Конфиг сброшен")
                    
                    # Закрыть меню
                    elif data == 'close_settings':
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                        requests.post(url, json={"callback_query_id": callback_id, "text": "Меню закрыто"})
                        return
                    
                    # Обновляем сообщение с новыми кнопками
                    if data not in ['close_settings', 'dummy']:
                        config = load_config()
                        settings_text = get_settings_text(config)
                        keyboard = create_settings_keyboard(config)
                        
                        edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
                        edit_payload = {
                            "chat_id": CHAT_ID,
                            "message_id": callback['message']['message_id'],
                            "text": settings_text,
                            "parse_mode": "HTML",
                            "reply_markup": keyboard
                        }
                        requests.post(edit_url, json=edit_payload)
                        
                        # Ответ на callback
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                        requests.post(url, json={"callback_query_id": callback_id, "text": "✅ Сохранено!"})
        
        except Exception as e:
            print(f"Ошибка в обработчике обновлений: {e}")
            time.sleep(1)

# --- МОНИТОРИНГ FREELANCEHUNT ---
def check_freelancehunt_loop():
    print("Запущена служба Freelancehunt.")
    config = load_config()
    
    try:
        feed = feedparser.parse(FH_RSS_URL)
        for entry in feed.entries:
            fh_sent_projects.add(entry.get('id', entry.link))
    except Exception as e:
        print(f"Первичный сбор Freelancehunt не удался: {e}")

    while True:
        try:
            config = load_config()
            feed = feedparser.parse(FH_RSS_URL)
            
            for entry in reversed(feed.entries):
                project_id = entry.get('id', entry.link)
                if project_id not in fh_sent_projects:
                    fh_sent_projects.add(project_id)
                    
                    raw_title = entry.title
                    if " : " in raw_title:
                        category_name, project_title = raw_title.split(" : ", 1)
                    elif ":" in raw_title:
                        category_name, project_title = raw_title.split(":", 1)
                    else:
                        category_name = entry.get('category', 'Freelancehunt')
                        project_title = raw_title

                    category_name = category_name.strip()

                    # ✅ ФИЛЬТР: Проверяем, в разрешённых ли категориях
                    category_allowed = False
                    for cat in config['freelancehunt']['categories']:
                        if config['freelancehunt']['categories'][cat] and cat.lower() in category_name.lower():
                            category_allowed = True
                            break
                    
                    if not category_allowed:
                        print(f"⏭️  Пропущен проект (категория не в списке): {category_name}")
                        continue

                    soup = BeautifulSoup(entry.summary, "html.parser")
                    description = soup.get_text(separator="\n")
                    if len(description) > 400: 
                        description = description[:400] + "..."

                    safe_title = clean_html_text(project_title.strip())
                    safe_description = clean_html_text(description)
                    safe_category = clean_html_text(category_name)

                    message = (
                        f"💼 <b>НОВЫЙ ПРОЕКТ • Freelancehunt</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📌 <b>Задание:</b> {safe_title}\n\n"
                        f"📁 <b>Категория:</b> {safe_category}\n\n"
                        f"📝 <b>Описание:</b>\n"
                        f"<blockquote>{safe_description}</blockquote>"
                    )
                    
                    bid_url = f"{entry.link}#make-bid"
                    send_telegram_message_with_two_buttons(
                        text=message, b1_text="🔎 Открыть", b1_url=entry.link, b2_text="💰 Сделать ставку", b2_url=bid_url
                    )
        except Exception as e:
            print(f"Ошибка во Freelancehunt: {e}")
            
        time.sleep(FH_INTERVAL)

# --- МОНИТОРИНГ КАБАНЧИКА ---
def check_kabanchik_loop():
    print("Запущена служба Kabanchik.ua.")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    for url in KABANCHIK_URLS:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    if "/tasks/" in a['href'] or "/work/" in a['href']:
                        task_id = a['href'].strip().split("-")[-1].replace("/", "").split("?")[0]
                        if task_id:
                            kabanchik_sent_tasks.add(task_id)
        except Exception as e:
            print(f"Ошибка при первичном сборе Кабанчика ({url}): {e}")

    print("Первичная база Кабанчика собрана. Начинаем мониторинг.")

    while True:
        try:
            config = load_config()
            for url in KABANCHIK_URLS:
                raw_cat = url.split('/')[-1]
                if "ai-poslugi" in raw_cat:
                    category_name = "AI Послуги"
                elif "foto" in raw_cat:
                    category_name = "Фото и Видео"
                else:
                    category_name = "Работа в интернете"
                
                # Проверяем, включена ли эта категория
                if not config['kabanchik']['categories'].get(category_name, False):
                    continue
                
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    tasks = soup.find_all("div", class_=["task-card", "b-task-item"])
                    if not tasks:
                        tasks = soup.find_all("li", class_=["b-task-item", "task-card"])
                    if not tasks:
                        tasks = [a.find_parent("div") for a in soup.find_all("a", href=True) if "/tasks/" in a['href'] or "/work/" in a['href']]
                        tasks = list(filter(None, set(tasks)))

                    for task in reversed(tasks):
                        link_tag = task.find("a", href=True) if hasattr(task, 'find') else None
                        if not link_tag and hasattr(task, 'name') and task.name == 'a':
                            link_tag = task
                            
                        if not link_tag: 
                            continue
                            
                        href = link_tag['href'].strip()
                        if not ("/tasks/" in href or "/work/" in href or "kabanchik.ua" in href):
                            continue
                        
                        task_link = href if href.startswith("http") else "https://kabanchik.ua" + ("" if href.startswith("/") else "/") + href
                        
                        try:
                            task_id = task_link.split("-")[-1].replace("/", "").split("?")[0]
                        except:
                            task_id = task_link
                        
                        if task_id and task_id not in kabanchik_sent_tasks:
                            kabanchik_sent_tasks.add(task_id)
                            
                            title_tag = task.find(["a", "span", "p", "div"], class_=["task-card__title", "b-task-item__title", "task-title"])
                            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
                            if not title or len(title) < 5:
                                title = "Новый заказ на Кабанчике"
                            
                            price_tag = task.find("span", class_=["task-card__price", "b-task-item__price", "task-price"])
                            price = price_tag.get_text(strip=True) if price_tag else "Бюджет не указан"
                            
                            safe_title = clean_html_text(title)
                            safe_price = clean_html_text(price)
                            safe_category = clean_html_text(category_name)

                            message = (
                                f"🐗 <b>НОВЫЙ ЗАКАЗ • Kabanchik</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                                f"📌 <b>Что сделать:</b> {safe_title}\n\n"
                                f"📁 <b>Категория:</b> {safe_category}\n\n"
                                f"💰 <b>Бюджет:</b> <code>{safe_price}</code>"
                            )
                            
                            send_telegram_message_with_two_buttons(
                                text=message, b1_text="🔎 Открыть", b1_url=task_link, b2_text="🤝 Откликнуться", b2_url=task_link
                            )
                time.sleep(3)
        except Exception as e:
            print(f"Ошибка в модуле Кабанчика: {e}")
        time.sleep(KABANCHIK_INTERVAL)

# --- ГЛАВНЫЙ ЗАПУСК ---
if __name__ == "__main__":
    Thread(target=run_web_server, daemon=True).start()
    print("Системный веб-сервер запущен.")
    
    Thread(target=check_freelancehunt_loop, daemon=True).start()
    Thread(target=check_kabanchik_loop, daemon=True).start()
    Thread(target=handle_updates, daemon=True).start()
    
    print("✅ Все службы мониторинга успешно запущены в облаке!")
    print("📱 Бот готов к работе. Команды доступны без ограничений.")
    
    while True:
        time.sleep(3600)
