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

# Безопасное экранирование текста, чтобы знаки < и > не ломали HTML-разметку Telegram
def clean_html_text(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Функция отправки сообщения с ДВУМЯ кнопками в ряд
def send_telegram_message_with_two_buttons(text, b1_text, b1_url, b2_text, b2_url):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    b1_url = b1_url.strip()
    b2_url = b2_url.strip()
    
    # Создаем две инлайн-кнопки в один ряд
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": b1_text, "url": b1_url},
                {"text": b2_text, "url": b2_url}
            ]
        ]
    }
    
    payload = {
        "chat_id": CHAT_ID, 
        "text": text, 
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    
    try:
        response = requests.post(url, json=payload)
        # Если Telegram забраковал сложную клавиатуру, отправляем резервный вариант со ссылками в тексте
        if response.status_code != 200:
            print(f"Ошибка Telegram API при отправке кнопок: {response.text}")
            fallback_text = text + f"\n\n🔗 <b>Просмотр:</b> {b1_url}\n⚡ <b>Ставка:</b> {b2_url}"
            requests.post(url, json={"chat_id": CHAT_ID, "text": fallback_text, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# --- МОНИТОРИНГ FREELANCEHUNT ---
def check_freelancehunt_loop():
    print("Запущена служба Freelancehunt.")
    while True:
        try:
            print("Проверяю Freelancehunt...")
            feed = feedparser.parse(FH_RSS_URL)
            is_first_run = len(fh_sent_projects) == 0

            for entry in reversed(feed.entries):
                project_id = entry.get('id', entry.link)
                if project_id not in fh_sent_projects:
                    fh_sent_projects.add(project_id)
                    if is_first_run: 
                        continue
                    
                    # Достаем категорию заказа из RSS (если ее нет, пишем "Не указана")
                    category_name = entry.get('category', 'Не указана')
                    
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    description = soup.get_text(separator="\n")
                    if len(description) > 400: 
                        description = description[:400] + "..."

                    # Очищаем все данные от опасных HTML-символов
                    safe_title = clean_html_text(entry.title)
                    safe_description = clean_html_text(description)
                    safe_category = clean_html_text(category_name)

                    message = (
                        f"💼 <b>НОВЫЙ ПРОЕКТ • Freelancehunt</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📁 <b>Категория:</b> {safe_category}\n"
                        f"📌 <b>Задание:</b> {safe_title}\n\n"
                        f"📝 <b>Описание:</b>\n"
                        f"<blockquote>{safe_description}</blockquote>"
                    )
                    
                    # Прямая ссылка на блок ставки на сайте Freelancehunt
                    bid_url = f"{entry.link}#make-bid"
                    
                    send_telegram_message_with_two_buttons(
                        text=message, 
                        b1_text="🔎 Открыть", 
                        b1_url=entry.link,
                        b2_text="💰 Сделать ставку",
                        b2_url=bid_url
                    )
        except Exception as e:
            print(f"Ошибка во Freelancehunt: {e}")
            
        time.sleep(FH_INTERVAL)

# --- МОНИТОРИНГ КАБАНЧИКА ---
def check_kabanchik_loop():
    print("Запущена служба Kabanchik.ua.")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    while True:
        try:
            is_first_run = len(kabanchik_sent_tasks) == 0
            
            for url in KABANCHIK_URLS:
                # Извлекаем категорию Кабанчика из самого URL для наглядности
                raw_cat = url.split('/')[-1]
                category_name = "AI Послуги" if "ai-poslugi" in raw_cat else "Фото и Видео" if "foto" in raw_cat else "Дизайн"
                
                print(f"Проверяю категорию Кабанчика: {raw_cat}")
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    tasks = soup.find_all("div", class_="task-card")
                    if not tasks:
                        tasks = soup.find_all("li", class_="b-task-item")
                        
                    for task in reversed(tasks):
                        link_tag = task.find("a", href=True)
                        if not link_tag: 
                            continue
                            
                        href = link_tag['href'].strip()
                        
                        if href.startswith("http"):
                            task_link = href
                        else:
                            if not href.startswith("/"):
                                href = "/" + href
                            task_link = "https://kabanchik.ua" + href
                        
                        task_id = task_link.split("-")[-1].replace("/", "")
                        
                        if task_id not in kabanchik_sent_tasks:
                            kabanchik_sent_tasks.add(task_id)
                            
                            if is_first_run: 
                                continue
                            
                            title_tag = task.find(["a", "span"], class_=["task-card__title", "b-task-item__title"])
                            title = title_tag.get_text(strip=True) if title_tag else "Новый заказ"
                            
                            price_tag = task.find("span", class_=["task-card__price", "b-task-item__price"])
                            price = price_tag.get_text(strip=True) if price_tag else "Бюджет не указан"
                            
                            safe_title = clean_html_text(title)
                            safe_price = clean_html_text(price)
                            safe_category = clean_html_text(category_name)

                            message = (
                                f"🐗 <b>НОВЫЙ ЗАКАЗ • Kabanchik</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                                f"📁 <b>Категория:</b> {safe_category}\n"
                                f"📌 <b>Что сделать:</b> {safe_title}\n\n"
                                f"💰 <b>Бюджет:</b> <code>{safe_price}</code>"
                            )
                            
                            # Для Кабанчика тоже делаем две аккуратные кнопки
                            send_telegram_message_with_two_buttons(
                                text=message, 
                                b1_text="🔎 Открыть", 
                                b1_url=task_link,
                                b2_text="🤝 Откликнуться",
                                b2_url=task_link
                            )
                else:
                    print(f"Кабанчик ответил ошибкой {response.status_code} для ссылки: {url}")
                
                time.sleep(2)
                
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
