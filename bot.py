import time
import requests
import feedparser
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8917936924:AAGdutlt5pgvAsTaZxTvoVboSul6NUUGADQ"
CHAT_ID = "419172431"

# Настройки для Freelancehunt
FH_RSS_URL = "https://freelancehunt.com/ua/projects.rss"
FH_INTERVAL = 60  # Проверка раз в минуту

# Настройки для Кабанчика (СПИСОК КАТЕГОРИЙ)
# Просто добавь свои ссылки внутрь квадратных скобок через запятую
KABANCHIK_URLS = [
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/foto-i-video-posluhy",
    "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/ai-poslugi", "https://kabanchik.ua/ua/cabinet/kryvyi-rih/category/dyzain",
    # Можно добавить еще 3 ссылки сюда по такому же принципу
]
KABANCHIK_INTERVAL = 30  # Пауза между полными кругами проверок всех категорий
# ====================================================

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Combo Multi-Category Bot is running")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckServer)
    server.serve_forever()

fh_sent_projects = set()
kabanchik_sent_tasks = set()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
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
                    
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    description = soup.get_text(separator="\n")
                    if len(description) > 500: 
                        description = description[:500] + "..."

                    message = (
                        f"🚨 <b>Новый заказ! [Freelancehunt]</b>\n\n"
                        f"📌 <b>{entry.title}</b>\n"
                        f"📝 {description}\n\n"
                        f"🔗 <a href='{entry.link}'>Открыть проект</a>"
                    )
                    send_telegram_message(message)
        except Exception as e:
            print(f"Ошибка во Freelancehunt: {e}")
            
        time.sleep(FH_INTERVAL)

# --- МОНИТОРИНГ КАБАНЧИКА (МНОГОКАТЕГОРИЙНЫЙ) ---
def check_kabanchik_loop():
    print("Запущена служба Kabanchik.ua (Мультикатегории).")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    while True:
        try:
            is_first_run = len(kabanchik_sent_tasks) == 0
            
            # Бот по очереди заходит на каждую ссылку из твоего списка
            for url in KABANCHIK_URLS:
                print(f"Проверяю категорию Кабанчика: {url.split('/')[-1]}")
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
                            
                        href = link_tag['href']
                        task_link = href if href.startswith("http") else "https://kabanchik.ua" + href
                        task_id = task_link.split("-")[-1].replace("/", "")
                        
                        if task_id not in kabanchik_sent_tasks:
                            kabanchik_sent_tasks.add(task_id)
                            
                            # Пропускаем старые заказы при самом первом запуске бота
                            if is_first_run: 
                                continue
                            
                            title_tag = task.find(["a", "span"], class_=["task-card__title", "b-task-item__title"])
                            title = title_tag.get_text(strip=True) if title_tag else "Новый заказ"
                            
                            price_tag = task.find("span", class_=["task-card__price", "b-task-item__price"])
                            price = price_tag.get_text(strip=True) if price_tag else "Цена не указана"
                            
                            message = (
                                f"🐗 <b>Новый заказ! [Кабанчик]</b>\n\n"
                                f"📌 <b>Что сделать:</b> {title}\n"
                                f"💰 <b>Бюджет:</b> {price}\n\n"
                                f"🔗 <a href='{task_link}'>Открыть заказ</a>"
                            )
                            send_telegram_message(message)
                else:
                    print(f"Кабанчик ответил ошибкой {response.status_code} для ссылки: {url}")
                
                # Крошечная пауза в 2 секунды между категориями, чтобы Кабанчик не заподозрил спам
                time.sleep(2)
                
        except Exception as e:
            print(f"Ошибка в модуле Кабанчика: {e}")
            
        # Пауза перед тем, как начать новый круг проверки всех категорий
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
