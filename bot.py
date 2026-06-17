<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bot Message Formatter</title>
  <style>
    :root{
      --bg:#f6f1e8;
      --paper:#fffaf2;
      --ink:#1f1a17;
      --muted:#6f655c;
      --line:#d8ccbf;
      --accent:#a34b2a;
      --accent-2:#2f6b5f;
      --gold:#c89b3c;
      --shadow:0 18px 50px rgba(56,35,20,.08);
      --radius:22px;
    }

    *{box-sizing:border-box}
    html,body{margin:0;padding:0}
    body{
      min-height:100vh;
      background:
        radial-gradient(circle at 15% 20%, rgba(200,155,60,.12), transparent 28%),
        radial-gradient(circle at 85% 15%, rgba(163,75,42,.12), transparent 24%),
        linear-gradient(180deg, #f8f3ea 0%, #f3ecdf 100%);
      color:var(--ink);
      font-family:"Manrope", sans-serif;
      display:grid;
      place-items:center;
      padding:32px;
    }

    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    .wrap{
      width:min(920px, 100%);
      display:grid;
      gap:22px;
    }

    .note{
      background:rgba(255,250,242,.72);
      border:1px solid rgba(216,204,191,.8);
      backdrop-filter:blur(10px);
      border-radius:var(--radius);
      padding:24px;
      box-shadow:var(--shadow);
      animation:rise .6s ease both;
    }

    .title{
      font-family:"Cormorant Garamond", serif;
      font-size:clamp(2rem, 4vw, 3.8rem);
      line-height:.95;
      margin:0 0 10px;
      letter-spacing:-.02em;
    }

    .lead{
      margin:0;
      color:var(--muted);
      font-size:1rem;
      max-width:65ch;
    }

    .code{
      background:#201b18;
      color:#f6efe6;
      border-radius:24px;
      padding:22px;
      overflow:auto;
      box-shadow:var(--shadow);
      border:1px solid rgba(255,255,255,.06);
      animation:rise .8s ease both;
    }

    pre{
      margin:0;
      white-space:pre-wrap;
      word-break:break-word;
      font:500 14px/1.7 "Manrope", sans-serif;
    }

    .sample{
      background:var(--paper);
      border:1px solid var(--line);
      border-radius:28px;
      overflow:hidden;
      box-shadow:var(--shadow);
      animation:rise 1s ease both;
    }

    .sample-head{
      padding:18px 22px;
      border-bottom:1px solid var(--line);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:16px;
      background:linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,250,242,.95));
    }

    .sample-head strong{
      font-size:.86rem;
      letter-spacing:.18em;
      text-transform:uppercase;
      color:var(--muted);
    }

    .chip{
      border:1px solid rgba(47,107,95,.2);
      color:var(--accent-2);
      background:rgba(47,107,95,.08);
      padding:8px 12px;
      border-radius:999px;
      font-size:.82rem;
      font-weight:800;
    }

    .message{
      padding:28px 22px 24px;
      display:grid;
      gap:18px;
    }

    .exchange{
      display:flex;
      align-items:center;
      gap:12px;
      padding-bottom:14px;
      border-bottom:1px solid var(--line);
    }

    .exchange-mark{
      width:12px;height:12px;border-radius:50%;
      background:linear-gradient(135deg, var(--gold), var(--accent));
      box-shadow:0 0 0 6px rgba(200,155,60,.12);
      flex:0 0 auto;
    }

    .exchange-name{
      font-size:.82rem;
      text-transform:uppercase;
      letter-spacing:.22em;
      color:var(--muted);
      font-weight:800;
    }

    .job{
      display:grid;
      gap:10px;
      padding-bottom:18px;
      border-bottom:1px dashed var(--line);
    }

    .job-title{
      margin:0;
      font-family:"Cormorant Garamond", serif;
      font-size:clamp(1.6rem, 3vw, 2.35rem);
      line-height:.95;
      letter-spacing:-.02em;
    }

    .meta{
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      align-items:center;
    }

    .category{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:8px 12px;
      border-radius:999px;
      background:rgba(163,75,42,.08);
      color:var(--accent);
      border:1px solid rgba(163,75,42,.18);
      font-size:.84rem;
      font-weight:800;
    }

    .divider-label{
      font-size:.72rem;
      letter-spacing:.22em;
      text-transform:uppercase;
      color:var(--muted);
      font-weight:800;
    }

    .desc{
      display:grid;
      gap:12px;
    }

    .desc p{
      margin:0;
      color:#2d2622;
      font-size:1rem;
      line-height:1.75;
    }

    .btn-row{
      padding-top:6px;
    }

    .btn{
      display:inline-flex;
      align-items:center;
      justify-content:center;
      min-width:220px;
      padding:15px 22px;
      border-radius:16px;
      text-decoration:none;
      color:#fff9f2;
      background:linear-gradient(135deg, var(--accent), #7f3117);
      font-weight:800;
      letter-spacing:.02em;
      box-shadow:0 14px 28px rgba(127,49,23,.18);
      transition:transform .25s ease, box-shadow .25s ease, filter .25s ease;
    }

    .btn:hover{
      transform:translateY(-2px) scale(1.01);
      box-shadow:0 18px 34px rgba(127,49,23,.24);
      filter:saturate(1.05);
    }

    .btn:active{transform:translateY(0) scale(.99)}

    @keyframes rise{
      from{opacity:0; transform:translateY(18px)}
      to{opacity:1; transform:none}
    }

    @media (max-width:640px){
      body{padding:18px}
      .sample-head{align-items:flex-start; flex-direction:column}
      .btn{width:100%}
    }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="note">
      <h1 class="title">Готовый формат текста для бота</h1>
      <p class="lead">
        Ниже — уже готовые строки для Python. Они красиво отделяют <b>биржу</b>, <b>название заказа</b>, <b>категорию</b> и <b>описание</b>, а ссылка остаётся в кнопке.
      </p>
    </section>

    <section class="sample" aria-label="Пример оформления сообщения">
      <div class="sample-head">
        <strong>Пример сообщения</strong>
        <span class="chip">Telegram Format</span>
      </div>

      <div class="message">
        <div class="exchange">
          <span class="exchange-mark"></span>
          <div class="exchange-name">Freelancehunt</div>
        </div>

        <div class="job">
          <h2 class="job-title">Смонтировать рекламный ролик для Instagram</h2>
          <div class="meta">
            <span class="category">Категория: Видео реклама</span>
          </div>
        </div>

        <div class="desc">
          <div class="divider-label">Описание заказа</div>
          <p>
            Нужен короткий динамичный ролик до 30 секунд, с титрами, музыкой и адаптацией под формат Reels. Желательно опыт в рекламном монтаже и понимание трендов соцсетей.
          </p>
        </div>

        <div class="btn-row">
          <a class="btn" href="#">Открыть проект</a>
        </div>
      </div>
    </section>

    <section class="code">
<pre># =========================
# 1. ДОБАВЬТЕ ЭТУ ФУНКЦИЮ
# =========================

def detect_fh_category(text):
    text_low = text.lower()

    category_map = {
        "Аудио/видео монтаж": ["монтаж", "видеомонтаж", "нарезка", "склейка"],
        "AI создание видео": ["ai", "нейросеть", "генерация видео", "создать видео ии"],
        "Видео реклама": ["реклама", "рекламный ролик", "promo", "promotional"],
        "Обработка видео": ["обработка видео", "цветокор", "color correction", "post production"],
        "Обработка фото": ["фото", "ретушь", "обработка фото"],
        "Анимация": ["анимация", "motion", "2d", "3d", "moho", "after effects"]
    }

    for category, words in category_map.items():
        for word in words:
            if word in text_low:
                return category

    return "Без категории"


# =========================
# 2. ЗАМЕНИТЕ parse_freelancehunt()
# =========================

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

            msg = (
                f"🟢 &lt;b&gt;БИРЖА:&lt;/b&gt; Freelancehunt\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 &lt;b&gt;ЗАКАЗ:&lt;/b&gt;\n"
                f"{clean_html_text(title)}\n\n"
                f"🏷 &lt;b&gt;КАТЕГОРИЯ:&lt;/b&gt; {clean_html_text(category)}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📝 &lt;b&gt;ОПИСАНИЕ:&lt;/b&gt;\n"
                f"{clean_html_text(summary[:700])}"
            )

            send_telegram_message_with_button(msg, "🔗 Открыть проект", link)

    except Exception as e:
        print(f"Ошибка парсинга Freelancehunt: {e}")


# =========================
# 3. ЗАМЕНИТЕ parse_kabanchik()
# =========================

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

                msg = (
                    f"🟠 &lt;b&gt;БИРЖА:&lt;/b&gt; Kabanchik\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📌 &lt;b&gt;ЗАКАЗ:&lt;/b&gt;\n"
                    f"{clean_html_text(title)}\n\n"
                    f"🏷 &lt;b&gt;КАТЕГОРИЯ:&lt;/b&gt; {clean_html_text(category)}"
                )

                send_telegram_message_with_button(msg, "🔗 Открыть задачу", full_link)

    except Exception as e:
        print(f"Ошибка парсинга Kabanchik: {e}")</pre>
    </section>
  </main>
</body>
</html>
