import time,requests,feedparser,json,os,re
from bs4 import BeautifulSoup
from threading import Thread
from http.server import HTTPServer,BaseHTTPRequestHandler

BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHAT_ID=os.environ.get("CHAT_ID")
PORT=int(os.environ.get("PORT",10000))
FH_RSS_URL="https://freelancehunt.com/projects.rss?skills%5B%5D=113&skills%5B%5D=192&skills%5B%5D=144&skills%5B%5D=101&skills%5B%5D=18&skills%5B%5D=91"
FH_INTERVAL=60
KABANCHIK_URLS=["https://kabanchik.ua/projects/category/ai-poslugi","https://kabanchik.ua/projects/category/foto-i-video-posluhy","https://kabanchik.ua/projects/category/roboty-v-interneti"]
KABANCHIK_INTERVAL=30
CONFIG_FILE="config.json"
fh_sent_projects=set()
kabanchik_sent_tasks=set()

class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200);self.send_header("Content-type","text/plain; charset=utf-8");self.end_headers();self.wfile.write(b"Bot is running")
    def log_message(self,format,*args): return

def run_web_server(): HTTPServer(("0.0.0.0",PORT),HealthCheckServer).serve_forever()

def telegram_api(method,payload):
    if not BOT_TOKEN: return None
    try:
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",json=payload,timeout=20)
        if r.status_code!=200: print(f"Ошибка Telegram API ({method}): {r.text}");return None
        return r.json()
    except Exception as e:
        print(f"Ошибка Telegram API ({method}): {e}");return None

def get_default_config():
    return {"freelancehunt":{"categories":{"Аудио/видео монтаж":True,"AI создание видео":True,"Видео реклама":True,"Обработка видео":True,"Обработка фото":True,"Анимация":True},"min_budget":0,"keywords":["видео","монтаж","AI","анимация","реклама"]},"kabanchik":{"categories":{"AI услуги":True,"Фото и видео услуги":True,"Работы в интернете":True}}}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except Exception as e: print(f"Ошибка загрузки конфига: {e}")
    return None

def save_config(config):
    try:
        with open(CONFIG_FILE,"w",encoding="utf-8") as f: json.dump(config,f,ensure_ascii=False,indent=2);return True
    except Exception as e: print(f"Ошибка сохранения конфига: {e}");return False

def ensure_config_exists():
    c=load_config()
    if not c: c=get_default_config();save_config(c)
    return c

def clean_html_text(text): return "" if not text else text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def send_telegram_message(text,reply_markup=None):
    if not BOT_TOKEN or not CHAT_ID: print("BOT_TOKEN или CHAT_ID не заданы");return None
    p={"chat_id":CHAT_ID,"text":text,"parse_mode":"HTML"}
    if reply_markup: p["reply_markup"]=reply_markup
    return telegram_api("sendMessage",p)

def send_telegram_message_with_button(text,button_text,button_url):
    if not BOT_TOKEN or not CHAT_ID: print("BOT_TOKEN или CHAT_ID не заданы");return
    telegram_api("sendMessage",{"chat_id":CHAT_ID,"text":text,"parse_mode":"HTML","reply_markup":{"inline_keyboard":[[{"text":button_text,"url":button_url.strip()}]]}})

def create_main_keyboard():
    return {"inline_keyboard":[[{"text":"⚙️ Настройки","callback_data":"open_settings"},{"text":"📊 Статус бота","callback_data":"bot_status"}],[{"text":"❓ Help","callback_data":"bot_help"},{"text":"🔄 Перезапуск","callback_data":"bot_restart"}]]}

def create_settings_keyboard():
    return {"inline_keyboard":[[{"text":"💰 Бюджет","callback_data":"open_budget"},{"text":"🔍 Ключевые слова","callback_data":"open_keywords"}],[{"text":"📁 Freelancehunt","callback_data":"show_fh_categories"}],[{"text":"📁 Kabanchik","callback_data":"show_kb_categories"}],[{"text":"🔄 Сброс","callback_data":"reset_config"},{"text":"❌ Закрыть","callback_data":"close_settings"}]]}

def create_budget_keyboard():
    return {"inline_keyboard":[[{"text":"$0","callback_data":"budget_0"},{"text":"$50","callback_data":"budget_50"},{"text":"$100","callback_data":"budget_100"}],[{"text":"$200","callback_data":"budget_200"},{"text":"$500","callback_data":"budget_500"}],[{"text":"⬅️ Назад","callback_data":"back_to_settings"}]]}

def create_keywords_keyboard():
    return {"inline_keyboard":[[{"text":"Видео","callback_data":"kw_video"},{"text":"Монтаж","callback_data":"kw_edit"}],[{"text":"AI","callback_data":"kw_ai"},{"text":"Анимация","callback_data":"kw_anim"}],[{"text":"Реклама","callback_data":"kw_ads"},{"text":"Фото","callback_data":"kw_photo"}],[{"text":"⬅️ Назад","callback_data":"back_to_settings"}]]}

def get_settings_text(c):
    t="⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n📁 <b>FREELANCEHUNT КАТЕГОРИИ:</b>\n"
    for cat,en in c["freelancehunt"]["categories"].items(): t+=f"{'✅' if en else '❌'} {cat}\n"
    t+=f"\n💰 <b>МИНИМАЛЬНЫЙ БЮДЖЕТ:</b> ${c['freelancehunt']['min_budget']}\n\n🔍 <b>КЛЮЧЕВЫЕ СЛОВА:</b>\n"+", ".join(c["freelancehunt"]["keywords"])+"\n\n📁 <b>KABANCHIK КАТЕГОРИИ:</b>\n"
    for cat,en in c["kabanchik"]["categories"].items(): t+=f"{'✅' if en else '❌'} {cat}\n"
    return t

def extract_budget(text):
    m=re.search(r'(\d[\d\s]*)',text.replace(",","")) if text else None
    if m:
        try: return int(m.group(1).replace(" ",""))
        except: return 0
    return 0

def matches_keywords(text,keywords):
    low=(text or "").lower()
    return any(kw.lower() in low for kw in keywords)

def detect_fh_category(text):
    low=text.lower()
    m={"Аудио/видео монтаж":["монтаж","видеомонтаж","нарезка","склейка","редактирование видео"],"AI создание видео":["ai","нейросеть","генерация видео","создать видео ии","sora","midjourney"],"Видео реклама":["реклама","рекламный ролик","promo","promotional","reels","ads"],"Обработка видео":["обработка видео","цветокор","post production","color correction"],"Обработка фото":["фото","ретушь","обработка фото","photoshop"],"Анимация":["анимация","motion","2d","3d","after effects","moho"]}
    for cat,words in m.items():
        if any(w in low for w in words): return cat
    return "Без категории"

def format_freelancehunt_message(title,summary,category,budget=None):
    return f"🟡 <b>Freelancehunt</b>\n\n{clean_html_text(title)}\n\n🏷 Категория\n{clean_html_text(category)}\n\n💰 {clean_html_text(str(budget) if budget else 'Не указана')}\n\n📝 Описание\n{clean_html_text(summary[:900])}"

def format_kabanchik_message(title,category,description="Описание на сайте Kabanchik",budget=None):
    return f"🟢 <b>Kabanchik</b>\n\n{clean_html_text(title)}\n\n🏷 Категория\n{clean_html_text(category)}\n\n💰 {clean_html_text(str(budget) if budget else 'Не указана')}\n\n📝 Описание\n{clean_html_text(description)}"

def setup_bot_menu():
    telegram_api("setChatMenuButton",{"menu_button":{"type":"commands"}})

def parse_freelancehunt():
    c=ensure_config_exists();kw=c["freelancehunt"]["keywords"];min_budget=c["freelancehunt"]["min_budget"]
    try:
        feed=feedparser.parse(FH_RSS_URL)
        for e in feed.entries:
            title=getattr(e,"title","");link=getattr(e,"link","");summary=getattr(e,"summary","");pid=link or title
            if pid in fh_sent_projects: continue
            txt=f"{title} {summary}";budget=extract_budget(txt)
            if min_budget and budget<min_budget: continue
            if kw and not matches_keywords(txt,kw): continue
            cat=detect_fh_category(txt);fh_sent_projects.add(pid)
            send_telegram_message_with_button(format_freelancehunt_message(title,summary,cat,budget if budget else None),"🔗 Открыть проект",link)
    except Exception as e: print(f"Ошибка парсинга Freelancehunt: {e}")

def parse_kabanchik():
    c=ensure_config_exists()
    try:
        for url in KABANCHIK_URLS:
            r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code!=200: continue
            soup=BeautifulSoup(r.text,"html.parser")
            for a in soup.find_all("a",href=True):
                href=a["href"];title=a.get_text(" ",strip=True)
                if not title or len(title)<5 or ("project" not in href and "task" not in href): continue
                full=href if href.startswith("http") else f"https://kabanchik.ua{href}"
                if full in kabanchik_sent_tasks: continue
                if c["freelancehunt"]["keywords"] and not matches_keywords(title.lower(),c["freelancehunt"]["keywords"]): continue
                cat="AI услуги" if "ai-poslugi" in url else "Фото и видео услуги" if "foto-i-video-posluhy" in url else "Работы в интернете" if "roboty-v-interneti" in url else "Без категории"
                kabanchik_sent_tasks.add(full)
                send_telegram_message_with_button(format_kabanchik_message(title,cat),"🔗 Открыть задачу",full)
    except Exception as e: print(f"Ошибка парсинга Kabanchik: {e}")

def handle_updates():
    offset=0;ensure_config_exists()
    while True:
        try:
            r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30",timeout=40)
            updates=r.json().get("result",[])
            for u in updates:
                offset=max(offset,u["update_id"]+1)
                if "message" in u:
                    text=u["message"].get("text","").lower()
                    if text=="/start": send_telegram_message("Привет! Выбери действие:",create_main_keyboard())
                    elif text=="/settings": send_telegram_message(get_settings_text(ensure_config_exists()),create_settings_keyboard())
                    elif text=="/help": send_telegram_message("📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n⚙️ Настройки\n📊 Статус бота\n❓ Help\n🔄 Перезапуск",create_main_keyboard())
                    elif text=="/status": c=ensure_config_exists();send_telegram_message(f"✅ <b>БОТ РАБОТАЕТ</b>\n\n💰 Бюджет: ${c['freelancehunt']['min_budget']}\n🔍 Ключевые слова: {', '.join(c['freelancehunt']['keywords'])}",create_main_keyboard())
                elif "callback_query" in u:
                    cb=u["callback_query"];data=cb["data"];cid=cb["id"];c=ensure_config_exists()
                    if data=="open_settings": send_telegram_message(get_settings_text(c),create_settings_keyboard())
                    elif data=="open_budget": send_telegram_message("💰 <b>Выберите минимальный бюджет:</b>",create_budget_keyboard())
                    elif data=="open_keywords": send_telegram_message("🔍 <b>Выберите ключевое слово:</b>",create_keywords_keyboard())
                    elif data=="back_to_settings": send_telegram_message(get_settings_text(c),create_settings_keyboard())
                    elif data=="show_fh_categories":
                        t="📁 <b>Freelancehunt категории:</b>\n\n"
                        for cat,en in c["freelancehunt"]["categories"].items(): t+=f"{'✅' if en else '❌'} {cat}\n"
                        send_telegram_message(t,create_settings_keyboard())
                    elif data=="show_kb_categories":
                        t="📁 <b>Kabanchik категории:</b>\n\n"
                        for cat,en in c["kabanchik"]["categories"].items(): t+=f"{'✅' if en else '❌'} {cat}\n"
                        send_telegram_message(t,create_settings_keyboard())
                    elif data.startswith("budget_"):
                        c["freelancehunt"]["min_budget"]=int(data.replace("budget_",""));save_config(c);send_telegram_message(f"✅ Минимальный бюджет установлен: ${c['freelancehunt']['min_budget']}",create_settings_keyboard())
                    elif data.startswith("kw_"):
                        km={"kw_video":"видео","kw_edit":"монтаж","kw_ai":"AI","kw_anim":"анимация","kw_ads":"реклама","kw_photo":"фото"};k=km.get(data)
                        if k:
                            kws=c["freelancehunt"]["keywords"]
                            msg=f"❌ Ключевое слово удалено: {k}" if k in kws else f"✅ Ключевое слово добавлено: {k}"
                            if k in kws: kws.remove(k)
                            else: kws.append(k)
                            c["freelancehunt"]["keywords"]=kws;save_config(c);send_telegram_message(msg,create_settings_keyboard())
                    elif data=="reset_config": c=get_default_config();save_config(c);send_telegram_message("🔄 Настройки сброшены",create_settings_keyboard())
                    elif data=="bot_status": c=ensure_config_exists();send_telegram_message(f"✅ <b>БОТ РАБОТАЕТ</b>\n\n💰 Бюджет: ${c['freelancehunt']['min_budget']}\n🔍 Ключевые слова: {', '.join(c['freelancehunt']['keywords'])}",create_main_keyboard())
                    elif data=="bot_help": send_telegram_message("📚 <b>ДОСТУПНЫЕ ДЕЙСТВИЯ:</b>\n\n⚙️ Настройки\n📊 Статус бота\n❓ Help\n🔄 Перезапуск",create_main_keyboard())
                    elif data=="bot_restart": send_telegram_message("🔄 Перезапуск...",create_main_keyboard());os._exit(0)
                    elif data=="close_settings": telegram_api("answerCallbackQuery",{"callback_query_id":cid,"text":"Меню закрыто"})
        except Exception as e:
            print(f"Ошибка в handle_updates: {e}");time.sleep(5)

def monitor_freelancehunt():
    while True: parse_freelancehunt();time.sleep(FH_INTERVAL)

def monitor_kabanchik():
    while True: parse_kabanchik();time.sleep(KABANCHIK_INTERVAL)

def main():
    if not BOT_TOKEN or not CHAT_ID: print("BOT_TOKEN или CHAT_ID не заданы в переменных окружения");return
    ensure_config_exists();setup_bot_menu();print("Бот запущен")
    Thread(target=run_web_server,daemon=True).start()
    Thread(target=monitor_freelancehunt,daemon=True).start()
    Thread(target=monitor_kabanchik,daemon=True).start()
    Thread(target=handle_updates,daemon=True).start()
    while True: time.sleep(60)

if __name__=="__main__": main()
