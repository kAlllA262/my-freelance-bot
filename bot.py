<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Готовый формат сообщений для Telegram-бота</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Prata&family=Inter:wght@400;500;600;700;800&display=swap');

    :root{
      --bg:#f4efe7;
      --panel:#fffaf4;
      --ink:#1f1a16;
      --muted:#6d645c;
      --line:#dacdbf;
      --accent:#9f4f2d;
      --accent-2:#2e6d62;
      --soft:#efe4d7;
      --shadow:0 18px 45px rgba(63,39,21,.08);
      --radius:24px;
    }

    *{box-sizing:border-box}
    html,body{margin:0;padding:0}
    body{
      background:
        radial-gradient(circle at top left, rgba(159,79,45,.10), transparent 24%),
        radial-gradient(circle at right 20%, rgba(46,109,98,.10), transparent 20%),
        linear-gradient(180deg, #f7f2ea 0%, #f1eadf 100%);
      color:var(--ink);
      font-family:"Inter", sans-serif;
      padding:28px;
    }

    .shell{
      max-width:1100px;
      margin:0 auto;
      display:grid;
      gap:24px;
    }

    .hero,.card,.code{
      background:rgba(255,250,244,.78);
      backdrop-filter:blur(10px);
      border:1px solid rgba(218,205,191,.85);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      animation:up .7s ease both;
    }

    .hero{padding:28px}
    .hero h1{
      margin:0 0 10px;
      font-family:"Prata", serif;
      font-size:clamp(2rem,4vw,3.8rem);
      line-height:.95;
      letter-spacing:-.02em;
    }
    .hero p{
      margin:0;
      color:var(--muted);
      max-width:70ch;
      line-height:1.7;
    }

    .preview{
      overflow:hidden;
    }

    .preview-head{
      padding:18px 22px;
      border-bottom:1px solid var(--line);
      display:flex;
      justify-content:space-between;
      gap:16px;
      align-items:center;
      background:linear-gradient(180deg, rgba(255,255,255,.65), rgba(255,250,244,.96));
    }

    .preview-head strong{
      font-size:.82rem;
      letter-spacing:.18em;
      text-transform:uppercase;
      color:var(--muted);
    }

    .tag{
      font-size:.8rem;
      font-weight:800;
      color:var(--accent-2);
      background:rgba(46,109,98,.08);
      border:1px solid rgba(46,109,98,.18);
      border-radius:999px;
      padding:8px 12px;
    }

    .telegram{
      padding:24px;
      display:grid;
      gap:18px;
      background:var(--panel);
    }

    .bubble{
      width:min(100%, 760px);
      background:#fffdf9;
      border:1px solid #eadfce;
      border-radius:22px 22px 22px 10px;
      padding:22px;
      box-shadow:0 10px 24px rgba(48,31,18,.06);
      display:grid;
      gap:16px;
    }

    .row{
      display:grid;
      gap:8px;
    }

    .label{
      font-size:.74rem;
      text-transform:uppercase;
      letter-spacing:.18em;
      color:var(--muted);
      font-weight:800;
    }

    .exchange{
      display:inline-flex;
      width:max-content;
      align-items:center;
      gap:10px;
      background:var(--soft);
      color:var(--accent);
      border:1px solid rgba(159,79,45,.16);
      padding:10px 14px;
      border-radius:999px;
      font-weight:800;
    }

    .dot{
      width:10px;height:10px;border-radius:50%;
      background:linear-gradient(135deg, var(--accent), #d18f54);
      box-shadow:0 0 0 5px rgba(159,79,45,.10);
    }

    .title{
      font-family:"Prata", serif;
      font-size:clamp(1.45rem,2.6vw,2.3rem);
      line-height:1.08;
      margin:0;
    }

    .category{
      display:inline-flex;
      width:max-content;
      align-items:center;
      gap:10px;
      background:rgba(46,109,98,.08);
      color:var(--accent-2);
      border:1px solid rgba(46,109,98,.18);
      padding:10px 14px;
      border-radius:999px;
      font-weight:800;
    }

    .text{
      color:#2b241f;
      line-height:1.8;
      white-space:pre-line;
    }

    .button{
      display:inline-flex;
      width:max-content;
      align-items:center;
      justify-content:center;
      min-width:220px;
      text-decoration:none;
      padding:15px 20px;
      border-radius:16px;
      color:#fffaf4;
      background:linear-gradient(135deg, var(--accent), #7f3417);
      font-weight:800;
      box-shadow:0 14px 28px rgba(127,52,23,.18);
      transition:.25s ease;
    }

    .button:hover{
      transform:translateY(-2px);
      box-shadow:0 18px 34px rgba(127,52,23,.24);
    }

    .code{
      padding:0;
      overflow:hidden;
    }

    .code-head{
      padding:16px 22px;
      border-bottom:1px solid rgba(255,255,255,.08);
      background:#1f1a17;
      color:#f0e7dc;
      font-size:.82rem;
      letter-spacing:.16em;
      text-transform:uppercase;
      font-weight:800;
    }

    pre{
      margin:0;
      padding:24px;
      overflow:auto;
      background:#181412;
      color:#f6ede2;
      font:500 14px/1.7 "Inter", sans-serif;
      white-space:pre-wrap;
      word-break:break-word;
    }

    @keyframes up{
      from{opacity:0;transform:translateY(18px)}
      to{opacity:1;transform:none}
    }

    @media (max-width:700px){
      body{padding:16px}
      .preview-head{flex-direction:column;align-items:flex-start}
      .button{width:100%}
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>Аккуратный формат сообщений для бота</h1>
      <p>
        Ниже — уже готовый код. Он делает сообщение более чистым: отдельно показывает <b>биржу</b>, <b>название заказа</b>, <b>категорию</b> и <b>описание</b>. Ссылка остаётся в красивой кнопке.
      </p>
    </section>

    <section class="card preview">
      <div class="preview-head">
        <strong>Пример того, как будет выглядеть сообщение</strong>
        <span class="tag">Telegram message preview</span>
      </div>

      <div class="telegram">
        <article class="bubble">
          <div class="row">
            <span class="label">Биржа</span>
            <div class="exchange"><span class="dot"></span> Freelancehunt</div>
          </div>

          <div class="row">
            <span class="label">Заказ</span>
            <h2 class="title">Смонтировать рекламный ролик для Instagram Reels</h2>
          </div>

          <div class="row">
            <span class="label">Категория</span>
            <div class="category">Видео реклама</div>
          </div>

          <div class="row">
            <span class="label">Описание</span>
            <div class="text">Нужен динамичный ролик до 30 секунд.
Добавить титры, музыку, аккуратные переходы и сделать адаптацию под вертикальный формат.
Желателен опыт в рекламном монтаже и понимание трендов соцсетей.</div>
          </div>

          <a class="button" href="#">🔗 Открыть проект</a>
        </article>
      </div>
    </section>

    <section class="code">
      <div class="code-head">Замените этим кодом функции в bot.py</div>
<pre>def detect_fh_category(text):
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


def format_freelancehunt_message(title, summary, category):
    return (
        f"🟢 &lt;b&gt;БИРЖА&lt;/b&gt;\n"
        f"Freelancehunt\n\n"
        f"📌 &lt;b&gt;НАЗВАНИЕ ЗАКАЗА&lt;/b&gt;\n"
        f"{clean_html_text(title)}\n\n"
        f"🏷 &lt;b&gt;КАТЕГОРИЯ&lt;/b&gt;\n"
        f"{clean_html_text(category)}\n\n"
        f"📝 &lt;b&gt;ОПИСАНИЕ&lt;/b&gt;\n"
        f"{clean_html_text(summary[:900])}"
    )


def format_kabanchik_message(title, category, description="Описание на сайте Kabanchik"):
    return (
        f"🟠 &lt;b&gt;БИРЖА&lt;/b&gt;\n"
        f"Kabanchik\n\n"
        f"📌 &lt;b&gt;НАЗВАНИЕ ЗАКАЗА&lt;/b&gt;\n"
        f"{clean_html_text(title)}\n\n"
        f"🏷 &lt;b&gt;КАТЕГОРИЯ&lt;/b&gt;\n"
        f"{clean_html_text(category)}\n\n"
        f"📝 &lt;b&gt;ОПИСАНИЕ&lt;/b&gt;\n"
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

            msg = format_freelancehunt_message(title, summary, category)
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

                msg = format_kabanchik_message(title, category)
                send_telegram_message_with_button(msg, "🔗 Открыть задачу", full_link)

    except Exception as e:
        print(f"Ошибка парсинга Kabanchik: {e}")</pre>
    </section>
  </main>
</body>
</html>
