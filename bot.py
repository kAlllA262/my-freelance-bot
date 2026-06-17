import time
import requests
import feedparser
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8917936924:AAGdutlt5pgvAsTaZxTvoVboSul6NUUGADQ"
CHAT_ID = "419172431"

# Настройки для Freelancehunt (Монтаж + Анимация/3D + AI генерация фото и видео)
FH_RSS_URL = "https://freelancehunt.com/projects.rss?category=10&category=27&category=28&category=40"
FH_INTERVAL = 60  # Проверка раз в минуту

# Настройки для Кабанчика (Кривой Рог + Удаленная работа по всей Украине)
KABANCHIK_URLS = [
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/foto-i-video-posluhy",
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/ai-poslugi", 
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/dyzain",
    "https://kabanchik.ua/ua/projects/category/ai-poslugi",          
    "https://kabanchik.ua/ua/projects/category/foto-i-video-posluhy" 
]
KABANCHIK_INTERVAL = 30  # Пауза между полными кругами проверок всех категорий
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

def clean_html_text(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

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
            fallback_text = text + f"\n\n🔗 <b>Просмотр:</b> {b1_url}\n⚡ <b>Ставка:</b> {b2_url}"
            requests.post(url, json={"chat_id": CHAT_ID, "text": fallback_text, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# --- МОНИТОРИНГ FREELANCEHUNT ---
def check_freelancehunt_loop():
    print("Запущена служба Freelancehunt с умным разделением категорий.")
    while True:
        try:
            feed = feedparser.parse(FH_RSS_URL)
            is_first_run = len(fh_sent_projects) == 0

            for entry in reversed(feed.entries):
                project_id = entry.get('id', entry.link)
                if project_id not in fh_sent_projects:
                    fh_sent_projects.add(project_id)
                    if is_first_run: 
                        continue
                    
                    raw_title = entry.title
                    if " : " in raw_title:
                        category_name, project_title = raw_title.split(" : ", 1)
                    elif ":" in raw_title:
                        category_name, project_title = raw_title.split(":", 1)
                    else:
                        category_name = entry.get('category', 'Freelancehunt')
                        project_title = raw_title

                    soup = BeautifulSoup(entry.summary, "html.parser")
                    description = soup.get_text(separator="\n")
                    if len(description) > 400: 
                        description = description[:400] + "..."

                    safe_title = clean_html_text(project_title.strip())
                    safe_description = clean_html_text(description)
                    safe_category = clean_html_text(category_name.strip())

                    # Изменено: Убран знак 'ъ', добавлен пустой перенос строки перед Категорией
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

# --- УЛУЧШЕННЫЙ МОНИТОРИНГ КАБАНЧИКА ---
def check_kabanchik_loop():
    print("Запущена обновленная служба Kabanchik.ua.")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    while True:
        try:
            is_first_run = len(kabanchik_sent_tasks) == 0
            
            for url in KABANCHIK_URLS:
                raw_cat = url.split('/')[-1]
                category_name = "AI Послуги" if "ai-poslugi" in raw_cat else "Фото и Видео" if "foto" in raw_cat else "Дизайн"
                
                print(f"Проверяю Кабанчик: {raw_cat}...")
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
                        
                        if href.startswith("http"):
                            task_link = href
                        else:
                            if not href.startswith("/"):
                                href = "/" + href
                            task_link = "https://kabanchik.ua" + href
                        
                        try:
                            task_id = task_link.split("-")[-1].replace("/", "").split("?")[0]
                        except:
                            task_id = task_link
                        
                        if task_id not in kabanchik_sent_tasks:
                            kabanchik_sent_tasks.add(task_id)
                            if is_first_run: 
                                continue
                            
                            title_tag = task.find(["a", "span", "p", "div"], class_=["task-card__title", "b-task-item__title", "task-title"])
                            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
                            if not title or len(title) < 5:
                                title = "Новый заказ на Кабанчике"
                            
                            price_tag = task.find("span", class_=["task-card__price", "b-task-item__price", "task-price"])
                            price = price_tag.get_text(strip=True) if price_tag else "Бюджет не указан"
                            
                            safe_title = clean_html_text(title)
                            safe_price = clean_html_text(price)
                            safe_category = clean_html_text(category_name)

                            # Изменено: Убран знак 'ъ', добавлен пустой перенос строки перед Категорией
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
                else:
                    print(f"Кабанчик ответил кодом {response.status_code}")
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
    
    print("Все службы мониторинга успешно запущены в облаке!")
    
    while True:
        time.sleep(3600)
