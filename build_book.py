# -*- coding: utf-8 -*-
"""Builds the biography index.html from chapter .md files (liquid-glass design)."""
import glob, html, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
CHAPTERS_DIR = os.path.join(BASE, "03-פרקים")
TIMELINE_MD = os.path.join(BASE, "ציר-זמן.md")
OUT = os.path.join(BASE, "05-גרסה-סופית", "index.html")
KICKER_TEXT = "ביוגרפיה משפחתית · חלק ראשון: 1922–1969"

LETTER = """לכם, שלושת ילדיי,
ולכם, שבעת נכדיי,

אם יום אחד תקראו את המילים האלה, דעו זאת תחילה: הייתם חלק מהותי מחיי. כל אחד מכם, בדרכו שלו, העניק משמעות לימיי — גם כשהדבר לא תמיד בא לידי ביטוי במילים.

לא הייתי הורה או סב מושלמים. לעתים חסרו לי המילים, הזמן והסבלנות. אך אהבה — מעולם לא חסרה. גם בשתיקה, גם בעייפות, היא הייתה שם.

הייתי רוצה שתזכרו אותי כמי שעשה כמיטב יכולתו. כמי שמנסה להנחיל ערכים פשוטים: כבוד, הגינות, טוב-לב והאומץ להיות מי שאתם. אם הצלחתי ללמד אתכם דבר אחד, אני מקווה שזהו הדבר: יש לכם ערך, מעצם היותכם קיימים.

לנכדים — שאולי לא הספקתי להכיר כפי שהייתי רוצה — דעו שהעתיד שלכם תמיד היה חשוב לי. גם כשכבר לא אהיה כאן, אני מאחל לכם חיים שבהם תעזו לאהוב, ללמוד, ליפול ולקום מחדש.

אם תחשבו עליי יום אחד, אין צורך שזה יהיה בעצב. חיוך, זיכרון או מחשבה חולפת — די בהם. משמעות הדבר תהיה שהשארתי חותם — לא בהיסטוריה של העולם, אלא בסיפור חייכם שלכם.

ועבורי, זה יהיה די והותר."""

def parse_chapter(path):
    text = open(path, encoding="utf-8").read()
    lines = text.strip().split("\n")
    title = lines[0].lstrip("# ").strip()
    period = ""
    body_start = 1
    for i, ln in enumerate(lines[1:], 1):
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^_(תקופה:.*)_$", s)
        if m:
            period = m.group(1)
            body_start = i + 1
        else:
            body_start = i
        break
    body = "\n".join(lines[body_start:]).strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
    return title, period, blocks

def render_marks(text):
    """ממיר טקסט גולמי (שעשוי להכיל סימוני {{...}} ל'טעון שיפור') ל-HTML,
    עם escaping תקין, ועוטף כל סימון בתג span אדום-קו-תחתי."""
    parts = re.split(r"\{\{(.+?)\}\}", text, flags=re.S)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(f'<span class="needs-rework">{html.escape(part)}</span>')
        else:
            out.append(html.escape(part))
    return "".join(out)

def render_block(b):
    """Returns (kind, html) where kind is 'body' or 'note'."""
    if b.startswith(">"):
        quote = " ".join(ln.lstrip("> ").strip() for ln in b.split("\n"))
        return "body", f'    <blockquote contenteditable="true">{render_marks(quote)}</blockquote>'
    m = re.match(r"^\*\*הערת רקע היסטורי:\*\*\s*(.*)$", b, re.S)
    if m:
        return "note", ('    <div class="historical-note"><strong>הערת רקע היסטורי</strong>'
                        + html.escape(m.group(1).strip()) + "</div>")
    m = re.match(r"^\*\*(שאלות פתוחות[^*]*):\*\*\s*(.*)$", b, re.S)
    if m:
        return "note", ('    <div class="questions"><strong>' + html.escape(m.group(1).strip())
                        + "</strong>" + html.escape(m.group(2).strip()) + "</div>")
    para = " ".join(ln.strip() for ln in b.split("\n"))
    # strip markdown bold/italic markers for plain paragraphs
    para = re.sub(r"\*\*(.+?)\*\*", r"\1", para)
    return "body", f'    <p contenteditable="true">{render_marks(para)}</p>'

def parse_md_tables(path):
    """מפרסר את כל טבלאות ה-markdown בקובץ. מחזיר רשימת (כותרות, שורות)."""
    tables = []
    lines = open(path, encoding="utf-8").read().split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]*\|$", lines[i + 1].strip()):
            header = [c.strip() for c in ln.strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tables.append((header, rows))
            i = j
        else:
            i += 1
    return tables

def clean_cell(c):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", c).strip()

# שיוך דמויות לענף משפחתי (מפתח = השם המלא בטבלת מילון הדמויות)
BRANCH_OF = {
    "אדלברט (אלברט) קליין": "core", "דולי (בת-שבע) דישי": "core", "ז'קי": "core",
    "תרז": "core", "אהובה": "core", "מיכאל, דניאל ונטלי": "core",
    "יהלי, אורי, איתי ואריאל": "core", "יונתן, עמית ועוד אחד": "core",
    "דזירה (Dezső) קליין": "klein", "אליזבת קליין": "klein", "אדל": "klein",
    "לילי (ליליאן)": "klein", "פאולו, רוז'ה": "klein", "גסטון": "klein",
    "יוסף דישי": "dishi", "אסתר דישי": "dishi", "לואיז": "dishi", "אודט": "dishi",
    "בלה, אווה": "dishi", "ויקטור": "dishi", "דינה": "dishi", "הדוד מקנדה": "dishi",
    "ז'ילבר": "dishi",
}

def branch_of(name, rel):
    if name in BRANCH_OF:
        return BRANCH_OF[name]
    if "דישי" in name or "דולי" in rel:
        return "dishi"
    if "קליין" in name or "האב" in rel:
        return "klein"
    return "core"

chapter_files = sorted(glob.glob(os.path.join(CHAPTERS_DIR, "פרק-*.md")))
chapters = [parse_chapter(p) for p in chapter_files]

toc_items = [
    '      <li class="toc-category">פרולוג</li>',
    '      <li class="toc-prologue"><a href="#prologue">לילדיי ולנכדיי — מכתב מסבא</a></li>',
    f'      <li class="toc-category">{html.escape(KICKER_TEXT)}</li>',
]
articles = []

letter_paras = "\n".join(f"    <p>{html.escape(p.strip())}</p>"
                         for p in LETTER.split("\n\n"))
articles.append(f"""  <article class="chapter prologue" id="prologue">
    <span class="eyebrow">פתח דבר</span>
    <h2>לילדיי ולנכדיי</h2>
{letter_paras}
    <p class="signature">- יוסי קליין</p>
  </article>""")

for i, (title, period, blocks) in enumerate(chapters, 1):
    cid = f"chapter-{i}"
    source_file = "03-פרקים/" + os.path.basename(chapter_files[i - 1])
    toc_items.append(f'      <li class="toc-chapter"><a href="#{cid}">{html.escape(title)}</a></li>')
    rendered = [render_block(b) for b in blocks]
    body_html = "\n".join(h for kind, h in rendered if kind == "body")
    notes = [h for kind, h in rendered if kind == "note"]
    notes_html = ""
    if notes:
        notes_html = '\n    <aside class="margin-notes">\n' + "\n".join(notes) + "\n    </aside>"
    eyebrow = html.escape(period) if period else f"פרק {i}"
    grandpa_note = f"""
    <div class="grandpa-note">
      <div class="grandpa-note-label">💬 המקום שלך, סבא</div>
      <div class="grandpa-note-hint">כאן אפשר להוסיף הערות, תיקונים, ותשובות לשאלות הפתוחות שבצד. מה שתכתוב נשמר ישירות באתר, בלי צורך להתחבר לשום מקום.</div>
      <div class="grandpa-note-box" contenteditable="true" data-note-id="{cid}"
           data-placeholder="כתוב כאן..."></div>
      <div class="grandpa-note-status" data-status-for="{cid}"></div>
    </div>"""
    articles.append(f"""  <article class="chapter" id="{cid}">
    <span class="eyebrow">{eyebrow}</span>
    <span class="inline-edit-status" data-inline-status="{cid}"></span>
    <div class="chapter-rendered" data-rendered-for="{cid}" data-source-file="{source_file}">
      <h2>{html.escape(title)}</h2>
{body_html}{notes_html}
    </div>{grandpa_note}
  </article>""")

# ---------- נספחים: הנתונים נמשכים מציר-זמן.md ----------
tables = parse_md_tables(TIMELINE_MD)
timeline_rows, char_rows, place_rows = [], [], []
for header, rows in tables:
    if header and "תאריך" in header[0]:
        timeline_rows = rows
    elif header and header[0] == "שם":
        char_rows = rows
    elif header and header[0] == "מקום":
        place_rows = rows

# --- נספח א: תחנות המסע (קווי מסלול בסגנון קווי רכבת + טבלת מקומות) ---
routes = [
    ("מסלול משפחת קליין", [("בודפשט", "chapter-1"), ("פריז", "chapter-2"), ("ליון", "chapter-2"),
                            ("מרסיי", "chapter-3"), ("חיפה", "chapter-3")]),
    ("מסלול משפחת דישי",  [("מצרים", "chapter-1"), ("ביירות", "chapter-1"), ("ישראל", "chapter-3")]),
    ("מסעו של יוסי",      [("ירושלים", "chapter-3"), ("פריז", "chapter-4"), ("ישראל", "chapter-10")]),
]
routes_html = []
for rname, stops in routes:
    stop_parts = []
    for j, (stop, ch) in enumerate(stops):
        if j:
            stop_parts.append('<span class="leg"></span>')
        stop_parts.append(f'<a class="stop" href="#{ch}"><span class="stop-dot"></span>'
                          f'<span class="stop-name">{html.escape(stop)}</span></a>')
    routes_html.append(f"""    <div class="route-line">
      <div class="route-name">{html.escape(rname)}</div>
      <div class="route-stops">{"".join(stop_parts)}</div>
    </div>""")
places_rows_html = "\n".join(
    f'        <tr><td class="place-name">{html.escape(clean_cell(r[0]))}</td>'
    f'<td>{html.escape(clean_cell(r[1]))}</td></tr>'
    for r in place_rows if len(r) >= 2
)
articles.append(f"""  <article class="chapter appendix" id="appendix-map">
    <span class="eyebrow">נספח א</span>
    <h2>תחנות המסע</h2>
    <p class="appendix-intro">שלושה מסלולים מתכנסים לארץ אחת: ענף קליין מבודפשט דרך פריז ומרסיי, ענף דישי ממצרים דרך ביירות, ויוסי - שנולד בירושלים, גדל בפריז וחזר ב-1968. לחיצה על תחנה מובילה לפרק המתאים.</p>
{chr(10).join(routes_html)}
    <h3 class="places-title">מקומות מרכזיים</h3>
    <table class="places-table">
      <thead><tr><th>מקום</th><th>ההקשר בסיפור</th></tr></thead>
      <tbody>
{places_rows_html}
      </tbody>
    </table>
  </article>""")

# --- נספח ב: ציר הזמן (ציר מרכזי, כרטיסים לפי תקופות) ---
ERAS = [
    (0,    "שורשים",             "עד 1939"),
    (1940, "מלחמת העולם",        "1940–1944"),
    (1945, "עלייה, אהבה ולידה",  "1945–1952"),
    (1953, "ילדות בצרפת",        "1953–1959"),
    (1960, "פוטו והנעורים",      "1960–1967"),
    (1968, "חזרה לישראל",        "1968 ואילך"),
]

def era_index(date_text, prev):
    """קובע תקופה לפי השנה בתאריך; שורות בלי שנה יורשות את התקופה הקודמת."""
    m = re.search(r"19\d\d", date_text)
    if not m:
        return prev
    y = int(m.group(0))
    idx = 0
    for i, (start, _name, _rng) in enumerate(ERAS):
        if y >= start:
            idx = i
    return max(prev, idx)  # התקופות רק מתקדמות, לא חוזרות אחורה

tl_items = []
cur_era = -1
side = 0
for cells in timeline_rows:
    if len(cells) < 5:
        continue
    date_raw, event, people, place, source = cells[:5]
    e = era_index(date_raw, max(cur_era, 0))
    if e != cur_era:
        _start, ename, erange = ERAS[e]
        tl_items.append(f'      <div class="tl-era"><span class="tl-era-pill">{html.escape(ename)}'
                        f' <small>{erange}</small></span></div>')
        cur_era = e
        side = 0  # כל תקופה מתחילה מחדש בצד ימין
    is_key = "**" in date_raw
    uncertain = "(?)" in date_raw
    date = clean_cell(date_raw).replace("(?)", "").strip()
    cls = ("tl-item " + ("tl-a" if side == 0 else "tl-b")
           + (" tl-key" if is_key else "") + (" tl-uncertain" if uncertain else ""))
    side ^= 1
    p = clean_cell(place)
    place_html = ""
    if p and p not in ("-", "—"):
        place_html = f'<span class="tl-place">{html.escape(p)}</span>'
    tl_items.append(f"""      <div class="{cls}">
        <div class="tl-head"><span class="tl-date">{html.escape(date)}</span>{place_html}</div>
        <div class="tl-event">{html.escape(clean_cell(event))}</div>
      </div>""")
articles.append(f"""  <article class="chapter appendix" id="appendix-timeline">
    <span class="eyebrow">נספח ב</span>
    <h2>ציר הזמן</h2>
    <p class="appendix-intro">האירועים מסודרים כרונולוגית על הציר ומקובצים לתקופות. תאריכים המסומנים "טעון אימות" ממתינים לבירור בפגישות הבאות.</p>
    <div class="timeline">
{chr(10).join(tl_items)}
    </div>
  </article>""")

# --- נספח ג: מי ומי - עץ משפחתי + כרטיסי דמויות ---
GROUP_TITLES = [("core", "המשפחה הקרובה"), ("klein", "ענף קליין - הונגריה וצרפת"), ("dishi", "ענף דישי - ביירות")]
char_id = {}
cards_by = {"core": [], "klein": [], "dishi": []}
for i, cells in enumerate(char_rows, 1):
    if len(cells) < 3:
        continue
    name, desc, rel = (clean_cell(c) for c in cells[:3])
    cid = f"char-{i}"
    char_id[name] = cid
    rel_html = "" if rel in ("-", "—", "") else f'<span class="char-rel">{html.escape(rel)}</span>'
    cards_by[branch_of(name, rel)].append(f"""      <div class="char-card" id="{cid}">
        <div class="char-name">{html.escape(name)}</div>
        {rel_html}
        <p>{html.escape(desc)}</p>
      </div>""")
groups_html = []
for gkey, gtitle in GROUP_TITLES:
    if cards_by[gkey]:
        groups_html.append(f'    <h3 class="char-group-title">{gtitle}</h3>\n    <div class="char-grid">\n'
                           + "\n".join(cards_by[gkey]) + "\n    </div>")

def tnode(x, y, w, label, key=None, cls="tn"):
    inner = (f'<rect x="{x - w / 2:g}" y="{y - 14}" width="{w}" height="28" rx="9"/>'
             f'<text x="{x}" y="{y + 4}" text-anchor="middle">{html.escape(label)}</text>')
    href = char_id.get(key) if key else None
    if href:
        return f'<a class="{cls}" href="#{href}">{inner}</a>'
    return f'<g class="{cls}">{inner}</g>'

def tline(x1, y1, x2, y2, dash=False):
    cls = ' class="dash"' if dash else ""
    return f'<line{cls} x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'

tree_parts = [
    # ענף קליין: הורים ← ילדים
    tline(568, 50, 568, 80), tline(430, 80, 706, 80),
    *[tline(x, 80, x, 106) for x in (430, 492, 545, 598, 651)],
    tline(706, 80, 706, 106, dash=True),
    # ענף דישי: הורים ← ילדים
    tline(200, 50, 200, 80), tline(40, 80, 360, 80),
    *[tline(x, 80, x, 106) for x in (360, 310, 260, 208, 158, 100, 40)],
    # נישואי אלברט ודולי ← יוסי + ז'קי
    tline(430, 134, 430, 168), tline(360, 134, 360, 168), tline(360, 168, 430, 168),
    tline(395, 168, 395, 192), tline(340, 192, 430, 192),
    tline(430, 192, 430, 206), tline(340, 192, 340, 206, dash=True),
    # תרז - נישואים שניים
    tline(445, 134, 560, 206, dash=True),
    # המשפחה של יוסי: אהובה, שלושה ילדים ושבעה נכדים
    tline(430, 234, 430, 262), tline(430, 262, 500, 262), tline(500, 262, 500, 268),
    tline(465, 262, 465, 300), tline(370, 300, 560, 300),
    tline(370, 300, 370, 304), tline(465, 300, 465, 304), tline(560, 300, 560, 304),
    tline(370, 332, 370, 346), tline(302, 346, 450, 346),
    *[tline(x, 346, x, 354) for x in (302, 350, 398, 450)],
    tline(560, 332, 560, 346), tline(520, 346, 618, 346),
    *[tline(x, 346, x, 354) for x in (520, 572, 618)],
    # צמתים
    tnode(568, 36, 150, "דזירה ♦ אליזבת", "דזירה (Dezső) קליין"),
    tnode(200, 36, 140, "יוסף ♦ אסתר", "יוסף דישי"),
    tnode(430, 120, 58, "אלברט", "אדלברט (אלברט) קליין", "tn strong"),
    tnode(492, 120, 48, "לילי", "לילי (ליליאן)"),
    tnode(545, 120, 44, "אדל", "אדל"),
    tnode(598, 120, 48, "פאולו", "פאולו, רוז'ה"),
    tnode(651, 120, 46, "רוז'ה", "פאולו, רוז'ה"),
    tnode(706, 120, 52, "גסטון", "גסטון"),
    tnode(360, 120, 50, "דולי", "דולי (בת-שבע) דישי", "tn strong"),
    tnode(310, 120, 40, "בלה", "בלה, אווה"),
    tnode(260, 120, 44, "אודט", "אודט"),
    tnode(208, 120, 48, "לואיז", "לואיז"),
    tnode(158, 120, 42, "אווה", "בלה, אווה"),
    tnode(100, 120, 62, "3 אחיות ?", None, "tn unk"),
    tnode(40, 120, 54, "ויקטור", "ויקטור"),
    tnode(560, 220, 48, "תרז", "תרז"),
    tnode(430, 220, 54, "יוסי", None, "tn key"),
    tnode(340, 220, 48, "ז'קי", "ז'קי"),
    tnode(500, 282, 60, "אהובה", "אהובה"),
    tnode(370, 318, 48, "נטלי", "מיכאל, דניאל ונטלי"),
    tnode(465, 318, 50, "מיכאל", "מיכאל, דניאל ונטלי"),
    tnode(560, 318, 54, "דניאל", "מיכאל, דניאל ונטלי"),
    tnode(302, 368, 44, "יהלי", "יהלי, אורי, איתי ואריאל"),
    tnode(350, 368, 42, "אורי", "יהלי, אורי, איתי ואריאל"),
    tnode(398, 368, 42, "איתי", "יהלי, אורי, איתי ואריאל"),
    tnode(450, 368, 46, "אריאל", "יהלי, אורי, איתי ואריאל"),
    tnode(520, 368, 46, "יונתן", "יונתן, עמית ועוד אחד"),
    tnode(572, 368, 42, "עמית", "יונתן, עמית ועוד אחד"),
    tnode(618, 368, 30, "?", None, "tn unk"),
    # תוויות
    '<text class="lbl" x="395" y="162" text-anchor="middle">נישאו 1950</text>',
    '<text class="lbl" x="512" y="162" text-anchor="middle">נישואים שניים · 1960</text>',
    '<text class="lbl" x="322" y="252" text-anchor="middle">אב אחר · נודע בגיל 40</text>',
]
tree_svg = ('<svg viewBox="0 0 740 395" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="עץ משפחתי">\n  '
            + "\n  ".join(tree_parts) + "\n</svg>")
articles.append(f"""  <article class="chapter appendix" id="appendix-characters">
    <span class="eyebrow">נספח ג</span>
    <h2>מי ומי - הדמויות</h2>
    <p class="appendix-intro">שני ענפים שמתכנסים: קליין מהונגריה ודישי מביירות. העץ נותן את התמונה, הכרטיסים שמתחתיו את הסיפורים.</p>
    <div class="family-tree">{tree_svg}</div>
    <p class="tree-caption">לחיצה על שם בעץ קופצת אל כרטיס הדמות · סימני "?" הם שאלות פתוחות לפגישות הבאות</p>
{chr(10).join(groups_html)}
  </article>""")

toc_items.append('      <li class="toc-category">נספחים</li>')
toc_items.append('      <li class="toc-appendix"><a href="#appendix-map">תחנות המסע</a></li>')
toc_items.append('      <li class="toc-appendix"><a href="#appendix-timeline">ציר הזמן</a></li>')
toc_items.append('      <li class="toc-appendix"><a href="#appendix-characters">מי ומי - הדמויות</a></li>')

toc_html = "\n".join(toc_items)
articles_html = "\n\n".join(articles)

page = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>סיפור חייו של יוסי קליין</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;800&family=Frank+Ruhl+Libre:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #1B2A41;
    --ink-2: #4A5A70;
    --ink-3: #8493A8;
    --glass: rgba(255,255,255,.55);
    --glass-strong: rgba(255,255,255,.85);
    --glass-border: rgba(255,255,255,.8);
    --shadow-card: 0 12px 32px rgba(27,42,65,.10), inset 0 1px 0 rgba(255,255,255,.9);
    --shadow-soft: 0 4px 14px rgba(27,42,65,.07);
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    background: #EEF1F5;
    color: var(--ink);
    font-family: "Heebo", sans-serif;
    line-height: 1.9;
  }
  body::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    background: linear-gradient(180deg, #F2F4F8 0%, #E9EDF2 40%, #EEF1F5 100%);
  }
  header { text-align: center; padding: 7rem 1.5rem 4.5rem; }
  header .kicker {
    display: inline-flex; align-items: center; gap: 10px;
    padding: 8px 18px; border-radius: 999px;
    background: var(--glass);
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border); box-shadow: var(--shadow-soft);
    color: var(--ink-2); font-size: .9rem; font-weight: 500;
    letter-spacing: .06em; margin-bottom: 1.6rem;
  }
  header h1 { font-weight: 800; font-size: 2.8rem; margin: 0 0 .6rem; color: var(--ink); letter-spacing: -.01em; }
  header p.subtitle { color: var(--ink-3); font-size: 1.05rem; margin: 0; font-weight: 300; }
  main { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem 6rem; }
  /* תוכן עניינים מקובע בצד ימין (RTL) */
  nav.toc {
    position: fixed;
    top: 50%;
    right: 28px;
    transform: translateY(-50%);
    width: 340px;
    max-height: 82vh;
    overflow-y: auto;
    overscroll-behavior: contain;
    background: var(--glass);
    backdrop-filter: blur(22px) saturate(1.4); -webkit-backdrop-filter: blur(22px) saturate(1.4);
    border: 1px solid var(--glass-border); border-radius: 20px;
    box-shadow: var(--shadow-card); padding: 1.3rem 1.4rem;
    z-index: 100;
    scrollbar-width: thin;
    scrollbar-color: rgba(27,42,65,.2) transparent;
  }
  nav.toc h2 {
    margin: 0 0 .9rem; padding-bottom: .8rem;
    font-size: 1rem; font-weight: 800; letter-spacing: 0; text-align: center;
    color: var(--ink);
    border-bottom: 1px solid rgba(27,42,65,.12);
  }
  nav.toc ol { list-style: none; padding: 0; margin: 0; counter-reset: toc; }
  nav.toc li { margin: 0; }
  nav.toc li.toc-chapter { counter-increment: toc; }
  nav.toc li.toc-category {
    padding: .9rem .7rem .3rem;
    font-size: .68rem; font-weight: 700; letter-spacing: .05em;
    color: var(--ink-3); text-transform: none;
    border-top: 1px solid rgba(27,42,65,.1);
    margin-top: .4rem;
  }
  nav.toc li.toc-category:first-child { border-top: none; margin-top: 0; padding-top: 0; }
  nav.toc a {
    display: flex; align-items: baseline; gap: .55em;
    color: var(--ink-2); text-decoration: none; font-weight: 400;
    font-size: .88rem; line-height: 1.5;
    padding: .38rem .7rem; border-radius: 10px;
    border-inline-end: 2px solid transparent;
    transition: background .15s ease, color .15s ease;
  }
  nav.toc li.toc-chapter a::before {
    content: counter(toc);
    font-size: .7rem; font-weight: 600; color: var(--ink-3);
    min-width: 1.1em; text-align: center;
  }
  nav.toc li.toc-prologue a::before {
    content: "✦";
    font-size: .7rem; font-weight: 600; color: var(--ink-3);
    min-width: 1.1em; text-align: center;
  }
  nav.toc a:hover { background: var(--glass-strong); color: var(--ink); }
  nav.toc a.active {
    background: var(--glass-strong);
    color: var(--ink); font-weight: 600;
    border-inline-end-color: var(--ink);
    box-shadow: var(--shadow-soft);
  }
  /* במסכים צרים — התוכן עניינים חוזר לזרימה הרגילה כקלף מעל הפרקים */
  @media (max-width: 1360px) {
    nav.toc {
      position: static;
      transform: none;
      width: auto;
      max-height: none;
      margin: 0 auto 3rem;
      padding: 1.8rem 2rem;
      border-radius: 24px;
    }
  }
  article.chapter {
    position: relative;
    max-width: 880px; margin-inline: auto;
    background: var(--glass);
    backdrop-filter: blur(22px) saturate(1.4); -webkit-backdrop-filter: blur(22px) saturate(1.4);
    border: 1px solid var(--glass-border); border-radius: 24px;
    box-shadow: var(--shadow-card); padding: 3rem 3rem 2.5rem; margin-bottom: 2.5rem;
    scroll-margin-top: 2rem;
  }
  article.chapter.appendix { max-width: none; }
  article.chapter .eyebrow {
    display: inline-block; padding: 4px 14px; border-radius: 999px;
    background: var(--glass-strong); border: 1px solid rgba(255,255,255,.9);
    box-shadow: var(--shadow-soft); color: var(--ink-2);
    font-size: .8rem; font-weight: 600; letter-spacing: .05em; margin-bottom: 1rem;
  }
  /* עריכה ישירה על גבי הטקסט עצמו - בלי כפתור, בלי מצב נפרד, בלי התחברות */
  .chapter-rendered p, .chapter-rendered blockquote { outline: none; border-radius: 6px; transition: background .15s ease; }
  .chapter-rendered p:hover, .chapter-rendered blockquote:hover { background: rgba(27,42,65,.035); }
  .chapter-rendered p:focus, .chapter-rendered blockquote:focus {
    background: rgba(27,42,65,.05); box-shadow: 0 0 0 1px rgba(27,42,65,.18);
  }
  .needs-rework {
    text-decoration: underline; text-decoration-color: #e11d48; text-decoration-thickness: 2px;
    text-underline-offset: 3px; cursor: pointer;
  }
  .mark-rework-btn {
    position: absolute; z-index: 500;
    font-family: "Heebo", sans-serif; font-size: .78rem; font-weight: 600;
    background: #e11d48; color: #fff; border: none; border-radius: 999px;
    padding: 6px 14px; cursor: pointer; box-shadow: 0 6px 16px rgba(225,29,72,.35);
  }
  .mark-rework-btn[hidden] { display: none; }
  .inline-edit-status {
    display: inline-block; margin-inline-start: .6rem;
    font-family: "Heebo", sans-serif; font-size: .78rem; color: var(--ink-3); vertical-align: middle;
  }
  .inline-edit-status.saving { color: var(--ink-3); }
  .inline-edit-status.saved { color: #2f7a4d; }
  .inline-edit-status.error { color: #b3432b; cursor: pointer; text-decoration: underline; }
  article.chapter h2 { font-weight: 800; font-size: 1.9rem; color: var(--ink); margin: 0 0 1.8rem; }
  article.chapter p {
    font-family: "Frank Ruhl Libre", serif; font-size: 1.2rem;
    color: var(--ink); margin: 0 0 1.4rem; text-align: justify;
  }
  article.prologue p { font-style: normal; }
  p.signature { color: var(--ink-3); font-size: 1rem !important; text-align: left !important; }
  blockquote {
    margin: 2rem 0; padding: 1rem 1.6rem;
    border-inline-end: 3px solid var(--ink);
    font-family: "Frank Ruhl Libre", serif; font-style: italic; font-size: 1.1rem;
    color: var(--ink); background: var(--glass-strong);
    border-radius: 12px; box-shadow: var(--shadow-soft);
  }
  .historical-note {
    margin: 2rem 0; padding: 1.2rem 1.6rem;
    background: rgba(27,42,65,.05); border: 1px solid rgba(27,42,65,.08);
    border-radius: 14px; font-size: .95rem; color: var(--ink-2);
  }
  .historical-note strong { color: var(--ink); display: block; margin-bottom: .4rem; }
  .questions {
    margin: 2.2rem 0 0; padding: 1.2rem 1.6rem;
    border: 1.5px dashed rgba(27,42,65,.18); border-radius: 14px;
    font-size: .95rem; color: var(--ink-2);
  }
  .questions strong { color: var(--ink); display: block; margin-bottom: .4rem; font-weight: 600; }
  /* הודעת טיוטה לסבא */
  .draft-banner {
    max-width: 880px; margin: 0 auto 2.5rem;
    background: rgba(255,255,255,.55);
    backdrop-filter: blur(18px) saturate(1.3); -webkit-backdrop-filter: blur(18px) saturate(1.3);
    border: 1.5px dashed rgba(27,42,65,.28); border-radius: 20px;
    padding: 1.5rem 1.8rem; box-shadow: var(--shadow-soft);
  }
  .draft-banner-title { font-weight: 800; font-size: 1.05rem; color: var(--ink); margin-bottom: .7rem; }
  .draft-banner p {
    font-family: "Heebo", sans-serif; font-size: .92rem; line-height: 1.8;
    color: var(--ink-2); margin: 0 0 .6rem;
  }
  .draft-banner p:last-child { margin-bottom: 0; }
  .draft-banner strong { color: var(--ink); }
  /* אזור התייחסות של סבא בסוף כל פרק */
  .grandpa-note {
    margin-top: 2.4rem; padding: 1.3rem 1.5rem;
    background: rgba(27,42,65,.04); border: 1.5px dashed rgba(27,42,65,.22);
    border-radius: 16px;
  }
  .grandpa-note-label { font-weight: 700; font-size: .95rem; color: var(--ink); margin-bottom: .3rem; }
  .grandpa-note-hint {
    font-family: "Heebo", sans-serif; font-size: .8rem; color: var(--ink-3);
    line-height: 1.6; margin-bottom: .8rem;
  }
  .grandpa-note-box {
    min-height: 90px; padding: .8rem 1rem;
    background: rgba(255,255,255,.7); border: 1px solid var(--glass-border);
    border-radius: 12px; font-family: "Heebo", sans-serif; font-size: .92rem;
    line-height: 1.7; color: var(--ink); outline: none;
  }
  .grandpa-note-box:focus { border-color: rgba(27,42,65,.35); background: #fff; }
  .grandpa-note-box:empty::before {
    content: attr(data-placeholder); color: var(--ink-3);
  }
  .grandpa-note-status {
    min-height: 1.2em; margin-top: .5rem; font-size: .74rem; color: var(--ink-3);
  }
  .grandpa-note-status.saving { color: var(--ink-3); }
  .grandpa-note-status.saved { color: #2f7a4d; }
  .grandpa-note-status.error { color: #b3432b; }
  /* במסך רחב — התוכן ממורכז בשטח שבין התפריט (ימין) להערות השוליים (שמאל) */
  @media (min-width: 1361px) {
    main {
      width: min(1100px, calc(100vw - 704px));
      max-width: none;
      margin-inline-start: calc(380px + max(0px, (100vw - 1804px) / 2));
      margin-inline-end: 0;
    }
  }
  /* במסך רחב — הרקע ההיסטורי והשאלות עוברים לשוליים השמאליים, צמודים לפרק שלהם.
     המיקום האנכי נשלט ב-JS (transform: translateY) כדי "לרחף" עם הגלילה
     ולעצור בתחתית הפרק, בלי לצאת מתחומו כלפי מעלה או מטה. */
  @media (min-width: 1361px) {
    .margin-notes {
      position: absolute;
      top: 0;
      inset-inline-start: calc(100% + 22px); /* RTL: start=ימין → דוחף את הבלוק אל מעבר לקצה השמאלי של הכרטיס */
      width: 270px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      transform: translateY(3.2rem);
      will-change: transform;
      transition: transform .05s linear;
    }
    .margin-notes .historical-note,
    .margin-notes .questions {
      margin: 0;
      font-size: .84rem;
      line-height: 1.75;
      padding: 1rem 1.2rem;
      backdrop-filter: blur(18px) saturate(1.3);
      -webkit-backdrop-filter: blur(18px) saturate(1.3);
    }
    .margin-notes .historical-note {
      background: var(--glass);
      border: 1px solid var(--glass-border);
      box-shadow: var(--shadow-soft);
    }
    .margin-notes .questions {
      background: rgba(255,255,255,.35);
      border: 1.5px dashed rgba(27,42,65,.22);
    }
    .margin-notes .historical-note strong,
    .margin-notes .questions strong { font-size: .78rem; letter-spacing: .04em; }
  }
  /* ---- נספחים ---- */
  nav.toc li.toc-appendix a::before {
    content: "◆";
    font-size: .55rem; font-weight: 600; color: var(--ink-3);
    min-width: 1.1em; text-align: center;
  }
  article.appendix p.appendix-intro {
    font-family: "Heebo", sans-serif; font-size: .95rem; color: var(--ink-2);
    text-align: start; line-height: 1.8; margin-bottom: 2rem;
  }
  /* תחנות המסע */
  .route-line {
    background: rgba(255,255,255,.5); border: 1px solid var(--glass-border);
    border-radius: 16px; padding: 1.1rem 1.4rem 1.3rem; margin-bottom: 1rem;
    box-shadow: var(--shadow-soft);
  }
  .route-name {
    display: inline-block; padding: 2px 12px; border-radius: 999px;
    background: rgba(27,42,65,.07); font-size: .78rem; font-weight: 600;
    color: var(--ink-2); margin-bottom: 1rem;
  }
  .route-stops { display: flex; align-items: flex-start; }
  .route-stops .stop {
    display: flex; flex-direction: column; align-items: center; gap: .35rem;
    text-decoration: none; min-width: 54px;
  }
  .route-stops .stop-dot {
    width: 13px; height: 13px; border-radius: 50%;
    background: #fff; border: 3px solid var(--ink);
    transition: transform .15s ease;
  }
  .route-stops .stop:hover .stop-dot { transform: scale(1.35); }
  .route-stops .stop-name {
    font-size: .82rem; font-weight: 600; color: var(--ink-2); white-space: nowrap;
  }
  .route-stops .stop:hover .stop-name { color: var(--ink); }
  .route-stops .leg {
    flex: 1; height: 0; margin-top: 6px;
    border-top: 2px dashed rgba(27,42,65,.3);
  }
  /* טבלת מקומות */
  .places-title { font-size: 1.05rem; font-weight: 700; color: var(--ink); margin: 2.2rem 0 1rem; }
  .places-table {
    width: 100%; border-collapse: separate; border-spacing: 0;
    background: rgba(255,255,255,.5); border: 1px solid var(--glass-border);
    border-radius: 16px; overflow: hidden; box-shadow: var(--shadow-soft);
    font-family: "Heebo", sans-serif; font-size: .88rem;
  }
  .places-table th {
    text-align: start; padding: .7rem 1.2rem;
    background: rgba(27,42,65,.06); color: var(--ink);
    font-size: .78rem; font-weight: 700; letter-spacing: .03em;
  }
  .places-table td {
    padding: .6rem 1.2rem; color: var(--ink-2); line-height: 1.7;
    border-top: 1px solid rgba(27,42,65,.07); vertical-align: top;
  }
  .places-table td.place-name { font-weight: 700; color: var(--ink); white-space: nowrap; }
  @media (max-width: 600px) {
    .route-stops .stop-name { font-size: .72rem; }
    .places-table td.place-name { white-space: normal; }
  }
  /* ציר הזמן - ציר מרכזי, כרטיסי זכוכית לפי תקופות; כל האירועים פתוחים */
  .timeline {
    position: relative; display: grid;
    grid-template-columns: 1fr 1fr; column-gap: 60px; row-gap: .9rem;
    margin-top: .6rem;
  }
  .timeline::before {
    content: ""; position: absolute; top: 14px; bottom: 8px;
    inset-inline-start: calc(50% - 1px); width: 2px;
    background: rgba(27,42,65,.18); border-radius: 2px;
  }
  .tl-era {
    grid-column: 1 / -1; display: flex; justify-content: center;
    position: relative; z-index: 1; margin: .9rem 0 .1rem;
  }
  .timeline .tl-era:first-child { margin-top: 0; }
  .tl-era-pill {
    background: var(--ink); color: #fff;
    border-radius: 999px; padding: 4px 18px;
    font-size: .78rem; font-weight: 700; letter-spacing: .02em;
    box-shadow: var(--shadow-soft);
  }
  .tl-era-pill small { font-weight: 400; font-size: .7rem; color: rgba(255,255,255,.65); margin-inline-start: .3em; }
  .tl-item {
    position: relative;
    background: rgba(255,255,255,.55); border: 1px solid var(--glass-border);
    border-radius: 14px; padding: .65rem .9rem .7rem;
    box-shadow: var(--shadow-soft);
    transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
  }
  .tl-item.tl-a { grid-column: 1; }
  .tl-item.tl-b { grid-column: 2; }
  /* נקודה על הציר + קו מחבר מהכרטיס אליה */
  .tl-item::before {
    content: ""; position: absolute; top: .8rem; z-index: 1;
    width: 11px; height: 11px; border-radius: 50%;
    background: #fff; border: 2.5px solid var(--ink);
    inset-inline-end: -38px;
  }
  .tl-item::after {
    content: ""; position: absolute; top: calc(.8rem + 7px);
    width: 22px; height: 1.5px; background: rgba(27,42,65,.22);
    inset-inline-end: -22px;
  }
  .tl-item.tl-b::before { inset-inline-end: auto; inset-inline-start: -38px; }
  .tl-item.tl-b::after { inset-inline-end: auto; inset-inline-start: -22px; }
  .tl-head { display: flex; align-items: center; gap: .5rem; }
  .tl-date { font-weight: 800; font-size: .84rem; color: var(--ink); unicode-bidi: plaintext; }
  .tl-place {
    display: inline-block; padding: 0 9px; border-radius: 999px;
    background: rgba(27,42,65,.07); font-size: .68rem; color: var(--ink-2);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 45%;
  }
  .tl-event {
    font-size: .78rem; line-height: 1.55; color: var(--ink-2); margin-top: .2rem;
  }
  .tl-item.tl-key { background: var(--ink); border-color: var(--ink); }
  .tl-item.tl-key:hover { background: var(--ink); }
  .tl-item.tl-key::before { background: var(--ink); }
  .tl-item.tl-key .tl-date, .tl-item.tl-key .tl-event { color: #fff; }
  .tl-item.tl-key .tl-place { background: rgba(255,255,255,.18); color: #fff; }
  .tl-item.tl-uncertain .tl-date::after {
    content: " · טעון אימות"; font-weight: 500; font-size: .68rem; color: var(--ink-3);
  }
  @media (max-width: 700px) {
    .timeline { display: block; }
    .timeline::before { inset-inline-start: 5px; }
    .tl-era { margin: 1.1rem 0 .8rem; }
    .tl-item, .tl-item.tl-a, .tl-item.tl-b { margin-bottom: .9rem; margin-inline-start: 1.6rem; }
    .tl-item::before, .tl-item.tl-b::before { inset-inline-end: auto; inset-inline-start: -26px; }
    .tl-item::after, .tl-item.tl-b::after { inset-inline-end: auto; inset-inline-start: -16px; width: 16px; }
  }
  /* עץ משפחתי */
  .family-tree { margin: 1.2rem 0 .6rem; }
  .family-tree svg { width: 100%; height: auto; display: block; }
  .family-tree line { stroke: rgba(27,42,65,.3); stroke-width: 1.4; }
  .family-tree line.dash { stroke-dasharray: 4 4; }
  .family-tree .tn rect { fill: rgba(255,255,255,.75); stroke: rgba(27,42,65,.3); stroke-width: 1.1; }
  .family-tree .tn text { font: 600 12px "Heebo", sans-serif; fill: var(--ink-2); }
  .family-tree .strong rect { fill: rgba(255,255,255,.95); stroke: var(--ink); stroke-width: 1.7; }
  .family-tree .strong text { fill: var(--ink); }
  .family-tree .key rect { fill: var(--ink); stroke: none; }
  .family-tree .key text { fill: #fff; font-weight: 700; }
  .family-tree .unk rect { stroke-dasharray: 4 3; fill: rgba(255,255,255,.35); }
  .family-tree .unk text { fill: var(--ink-3); }
  .family-tree a { cursor: pointer; }
  .family-tree a:hover rect { stroke: var(--ink); stroke-width: 2; }
  .family-tree text.lbl { font: 500 10.5px "Heebo", sans-serif; fill: var(--ink-3); }
  article.appendix p.tree-caption {
    font-family: "Heebo", sans-serif; font-size: .8rem; color: var(--ink-3);
    text-align: center; margin: 0 0 1.8rem;
  }
  /* כרטיסי דמויות */
  .char-group-title { font-size: 1.05rem; font-weight: 700; color: var(--ink); margin: 2rem 0 1rem; }
  .char-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  @media (min-width: 1361px) { .char-grid { grid-template-columns: repeat(3, 1fr); } }
  @media (max-width: 700px) { .char-grid { grid-template-columns: 1fr; } }
  .char-card {
    background: rgba(255,255,255,.5); border: 1px solid var(--glass-border);
    border-radius: 16px; padding: 1rem 1.2rem; box-shadow: var(--shadow-soft);
    scroll-margin-top: 90px;
    transition: background .3s ease, border-color .3s ease;
  }
  .char-card:target { border-color: var(--ink); background: var(--glass-strong); }
  .char-card .char-name { font-weight: 700; color: var(--ink); margin-bottom: .2rem; }
  .char-card .char-rel {
    display: inline-block; padding: 1px 10px; border-radius: 999px;
    background: rgba(27,42,65,.07); font-size: .72rem; color: var(--ink-2); margin-bottom: .4rem;
  }
  article.appendix .char-card p {
    font-family: "Heebo", sans-serif; font-size: .88rem; line-height: 1.7;
    color: var(--ink-2); margin: 0; text-align: start;
  }
  footer { text-align: center; padding: 3rem 1.5rem; color: var(--ink-3); font-size: .85rem; }
  @media (max-width: 600px) {
    header h1 { font-size: 2rem; }
    article.chapter { padding: 2rem 1.4rem; }
  }
</style>
</head>
<body>

<header>
  <div class="kicker">__KICKER__</div>
  <h1>סיפור חייו של יוסי קליין</h1>
  <p class="subtitle">כפי שסיפר במילותיו, נאסף ונכתב באהבה</p>
</header>

<main>
  <nav class="toc">
    <h2>תוכן העניינים</h2>
    <ol>
__TOC__
    </ol>
  </nav>

  <div class="draft-banner">
    <div class="draft-banner-title">✍️ סבא יקר, קרא לפני הכל</div>
    <p>זו <strong>טיוטה ראשונה בלבד</strong>. הסיפור עוד יעבור שכתובים רבים עד שנמצא יחד את הדרך הנכונה לספר אותו - באיזה קול לספר (בגוף ראשון, בקולך שלך, או בגוף שלישי), באיזה סדר, ובאיזה גוון. שום דבר כאן אינו סופי.</p>
    <p>ההערות בשוליים - <strong>הקשר היסטורי</strong> ו<strong>שאלות פתוחות</strong> - נועדו לעזור לנו לדייק. בסוף כל פרק תמצא מקום להוסיף את ההערות שלך, לענות על השאלות, לתקן ולהשלים. כל מילה שלך חשובה.</p>
  </div>

__ARTICLES__

</main>

<footer>
  מבוסס על שיחות עם סבא יוסי ועל זיכרונות שכתב · פגישה ראשונה: 9 ביולי 2026 · מתעדכן
</footer>

<script>
(function () {
  var links = document.querySelectorAll('nav.toc a');
  var map = {};
  links.forEach(function (a) {
    var id = a.getAttribute('href').slice(1);
    map[id] = a;
  });
  var current = null;
  function setActive(id) {
    if (current === id) return;
    current = id;
    links.forEach(function (a) { a.classList.remove('active'); });
    var link = map[id];
    if (link) {
      link.classList.add('active');
      var nav = link.closest('nav');
      var lt = link.offsetTop, nh = nav.clientHeight;
      if (lt < nav.scrollTop + 20 || lt > nav.scrollTop + nh - 40) {
        nav.scrollTo({ top: lt - nh / 2, behavior: 'smooth' });
      }
    }
  }
  var articles = Array.prototype.slice.call(document.querySelectorAll('article.chapter'));
  function onScroll() {
    var probe = window.scrollY + window.innerHeight * 0.3;
    var active = articles[0] && articles[0].id;
    for (var i = 0; i < articles.length; i++) {
      if (articles[i].offsetTop <= probe) active = articles[i].id;
    }
    if (active) setActive(active);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // הערות השוליים "רוחפות" לאורך הפרק בזמן גלילה, ונעצרות בתחילתו/בסופו
  var noteGroups = Array.prototype.slice.call(document.querySelectorAll('.margin-notes'));
  var BASE_OFFSET = 51; // 3.2rem
  var BOTTOM_GAP = 40;
  function updateNotes() {
    if (window.innerWidth < 1361) return;
    noteGroups.forEach(function (aside) {
      var article = aside.closest('article.chapter');
      if (!article) return;
      var artRect = article.getBoundingClientRect();
      var asideH = aside.offsetHeight;
      var maxTranslate = Math.max(BASE_OFFSET, artRect.height - asideH - BOTTOM_GAP);
      var wanted = BASE_OFFSET - artRect.top;
      var translate = Math.min(Math.max(wanted, BASE_OFFSET), maxTranslate);
      aside.style.transform = 'translateY(' + Math.round(translate) + 'px)';
    });
  }
  window.addEventListener('scroll', updateNotes, { passive: true });
  window.addEventListener('resize', updateNotes);
  updateNotes();

  // "המקום שלך, סבא" - שמירה בלי שום התחברות: גם קריאה וגם כתיבה עוברות
  // דרך אותה פונקציה עננית קטנה (worker/ בתיקיית הפרויקט) שמחזיקה את מפתח
  // הגישה בעצמה (GET לקריאה, POST לכתיבה) -
  // כך שלעולם לא פוגעים במגבלת הבקשות הציבורית של GitHub (60 לשעה לכל כתובת IP,
  // שכל בני המשפחה שגולשים מאותה רשת ביתית חולקים ביניהם) ולא בעיכוב המטמון
  // של raw.githubusercontent.com אחרי שמירה טרייה.
  var WORKER_URL = 'https://saba-notes-proxy.bursteinori.workers.dev';

  function setStatus(el, kind, text) {
    if (!el) return;
    el.textContent = text;
    var base = el.className.replace(/\s*(saving|saved|error)\\b/g, '').trim();
    el.className = base + (kind ? ' ' + kind : '');
  }

  function saveNote(chapterId, text, statusEl) {
    setStatus(statusEl, 'saving', 'שומר...');
    fetch(WORKER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chapterId: chapterId, text: text })
    }).then(function (res) {
      if (!res.ok) throw new Error('http-' + res.status);
      setStatus(statusEl, 'saved', '✓ נשמר באתר');
    }).catch(function () {
      setStatus(statusEl, 'error', 'השמירה נכשלה - ננסה שוב אוטומטית בפעם הבאה שתכתבו');
    });
  }

  function loadAllNotes() {
    fetch(WORKER_URL).then(function (res) {
      if (!res.ok) throw new Error('http-' + res.status);
      return res.json();
    }).then(function (data) {
      var fullText = data.content;
      document.querySelectorAll('.grandpa-note-box').forEach(function (box) {
        var id = box.getAttribute('data-note-id');
        var marker = '<!-- note:' + id + ' -->';
        var idx = fullText.indexOf(marker);
        if (idx === -1) return;
        var after = idx + marker.length;
        var nextIdx = fullText.indexOf('<!-- note:', after);
        if (nextIdx === -1) nextIdx = fullText.length;
        var section = fullText.slice(after, nextIdx);
        var body = section.replace(/^\s*\\n##[^\\n]*\\n/, '').trim();
        if (body && !box.textContent.trim()) box.textContent = body;
      });
    }).catch(function () { /* טעינה שקטה - לא קריטי אם נכשלת */ });
  }

  document.querySelectorAll('.grandpa-note-box').forEach(function (box) {
    var id = box.getAttribute('data-note-id');
    var statusEl = box.closest('.grandpa-note').querySelector('.grandpa-note-status');
    var timer = null;
    box.addEventListener('input', function () {
      clearTimeout(timer);
      setStatus(statusEl, '', '');
      timer = setTimeout(function () { saveNote(id, box.textContent, statusEl); }, 1500);
    });
  });
  loadAllNotes();

  // עריכה ישירה על גבי הטקסט - כל פסקה/ציטוט ניתנים לעריכה במקום, בלי כפתור
  // ובלי מצב נפרד. שמירה אוטומטית (debounce) דרך אותה פונקציה עננית: קוראים
  // את הקובץ המלא הנוכחי, מחליפים רק את בלוקי הגוף (שומרים כותרת/תקופה/הערות
  // כפי שהיו), וכותבים בחזרה.
  document.querySelectorAll('.chapter-rendered').forEach(function (rendered) {
    var cid = rendered.getAttribute('data-rendered-for');
    var sourceFile = rendered.getAttribute('data-source-file');
    var statusEl = document.querySelector('[data-inline-status="' + cid + '"]');
    var timer = null;

    function serializeEditable(el) {
      var out = '';
      el.childNodes.forEach(function (node) {
        if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains('needs-rework')) {
          out += '{{' + node.textContent + '}}';
        } else {
          out += node.textContent;
        }
      });
      return out.trim();
    }

    function collectBodyBlocks() {
      var blocks = [];
      rendered.querySelectorAll(':scope > p, :scope > blockquote').forEach(function (el) {
        blocks.push({ type: el.tagName === 'BLOCKQUOTE' ? 'quote' : 'p', text: serializeEditable(el) });
      });
      return blocks;
    }

    function spliceChapterFile(rawFullText, bodyBlocks) {
      var lines = rawFullText.replace(/^\s+/, '').split('\\n');
      var headEnd = 1;
      if (lines[1] && /^_.*_$/.test(lines[1].trim())) headEnd = 2;
      var tailStart = -1;
      for (var i = headEnd; i < lines.length; i++) {
        if (/^\*\*(הערת רקע היסטורי|שאלות פתוחות)/.test(lines[i].trim())) { tailStart = i; break; }
      }
      var head = lines.slice(0, headEnd).join('\\n');
      var tail = tailStart === -1 ? '' : lines.slice(tailStart).join('\\n');
      var body = bodyBlocks.map(function (b) {
        return b.type === 'quote' ? '> ' + b.text : b.text;
      }).join('\\n\\n');
      var result = head + '\\n\\n' + body;
      if (tail) result += '\\n\\n' + tail;
      return result.trim() + '\\n';
    }

    function save() {
      setStatus(statusEl, 'saving', 'שומר...');
      fetch(WORKER_URL + '?file=' + encodeURIComponent(sourceFile)).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        return res.json();
      }).then(function (data) {
        var updated = spliceChapterFile(data.content, collectBodyBlocks());
        return fetch(WORKER_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind: 'chapter', file: sourceFile, content: updated })
        });
      }).then(function (res) {
        if (!res.ok) throw new Error('http-' + res.status);
        setStatus(statusEl, 'saved', '✓ נשמר');
      }).catch(function () {
        setStatus(statusEl, 'error', 'השמירה נכשלה - לחצו כאן לנסות שוב');
      });
    }

    rendered.addEventListener('input', function () {
      clearTimeout(timer);
      setStatus(statusEl, '', '');
      timer = setTimeout(save, 1800);
    });
    if (statusEl) {
      statusEl.addEventListener('click', function () {
        if (statusEl.classList.contains('error')) save();
      });
    }
  });

  // סימון "טעון שיפור": בוחרים טקסט בתוך פסקה, מופיע כפתור אדום, לוחצים
  // ומקבלים קו תחתון אדום. לחיצה על טקסט מסומן (בלי בחירה) מסירה את הסימון.
  var markBtn = document.createElement('button');
  markBtn.type = 'button';
  markBtn.className = 'mark-rework-btn';
  markBtn.textContent = 'סמן לשיפור';
  markBtn.hidden = true;
  document.body.appendChild(markBtn);
  var pendingRange = null;

  document.addEventListener('mouseup', function () {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) { markBtn.hidden = true; return; }
    var range = sel.getRangeAt(0);
    var node = range.commonAncestorContainer;
    var el = node.nodeType === 1 ? node : node.parentElement;
    var host = el && el.closest && el.closest('.chapter-rendered p, .chapter-rendered blockquote');
    if (!host) { markBtn.hidden = true; return; }
    var rect = range.getBoundingClientRect();
    markBtn.hidden = false;
    markBtn.style.top = (window.scrollY + rect.top - 38) + 'px';
    markBtn.style.left = (window.scrollX + rect.left) + 'px';
    pendingRange = range.cloneRange();
  });
  markBtn.addEventListener('mousedown', function (e) { e.preventDefault(); });
  markBtn.addEventListener('click', function () {
    if (!pendingRange) return;
    try {
      var span = document.createElement('span');
      span.className = 'needs-rework';
      pendingRange.surroundContents(span);
      span.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (e) { /* בחירה שחוצה כמה אלמנטים - מדלגים */ }
    markBtn.hidden = true;
    window.getSelection().removeAllRanges();
  });
  document.addEventListener('click', function (e) {
    var mark = e.target.closest('.needs-rework');
    if (mark && window.getSelection().isCollapsed) {
      var parent = mark.parentNode;
      while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
      parent.removeChild(mark);
      parent.normalize();
      parent.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });
})();
</script>

</body>
</html>
"""

page = page.replace("__TOC__", toc_html).replace("__ARTICLES__", articles_html).replace("__KICKER__", html.escape(KICKER_TEXT))
page = page.replace("—", "-")  # Replace em-dashes with hyphens
open(OUT, "w", encoding="utf-8").write(page)
print("chapters:", len(chapters))
for f in chapter_files:
    print(" -", os.path.basename(f))
print("timeline items:", len(tl_items),
      "| characters:", sum(len(v) for v in cards_by.values()),
      "| places:", len(place_rows))
print("written:", OUT, len(page), "chars")
