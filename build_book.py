# -*- coding: utf-8 -*-
"""Builds the biography index.html from chapter .md files (liquid-glass design)."""
import glob, html, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
CHAPTERS_DIR = os.path.join(BASE, "03-פרקים")
TIMELINE_MD = os.path.join(BASE, "ציר-זמן.md")
OUT = os.path.join(BASE, "05-גרסה-סופית", "index.html")
KICKER_TEXT = "ביוגרפיה משפחתית · חלק ראשון: 1922–1969"

# ה-CSS וה-JS חיים בקבצים נפרדים (לא כמחרוזת פייתון) בכוונה: מחרוזת
# פייתון לא-raw מפרשת \n, \t, \b וכו' כתווי בקרה אמיתיים לפני שהטקסט בכלל
# מגיע לדפדפן - מלכודת שגרמה לשני באגים שקטים (regex עם \b שהתפוצץ לתו
# backspace בלתי-נראה, וכן הלאה). קריאת קובץ .js/.css חיצוני עוקפת את זה
# לגמרי: הבייטים מגיעים בדיוק כפי שנכתבו.
CSS = open(os.path.join(BASE, "styles.css"), encoding="utf-8").read().rstrip("\n")
SCRIPT = open(os.path.join(BASE, "script.js"), encoding="utf-8").read().rstrip("\n")

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
    """ממיר טקסט גולמי (שעשוי להכיל סימוני {{טקסט}} או {{טקסט::הערה} ל'טעון
    שיפור') ל-HTML, עם escaping תקין, ועוטף כל סימון בתג span אדום-קו-תחתי.
    הערה אופציונלית (אחרי ::) הופכת ל-title שמוצג כ-tooltip."""
    parts = re.split(r"\{\{(.+?)\}\}", text, flags=re.S)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            marked, sep, note = part.partition("::")
            title_attr = f' title="{html.escape(note.strip())}"' if sep else ""
            out.append(f'<span class="needs-rework"{title_attr}>{html.escape(marked)}</span>')
        else:
            out.append(html.escape(part))
    return "".join(out)

def render_block(b):
    """Returns (kind, html) where kind is 'body' or 'note'."""
    if b.startswith(">"):
        quote = " ".join(ln.lstrip("> ").strip() for ln in b.split("\n"))
        return "body", f"    <blockquote>{render_marks(quote)}</blockquote>"
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
    return "body", f"    <p>{render_marks(para)}</p>"

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
    <div class="chapter-rendered">
      <h2>{html.escape(title)}</h2>
      <div class="chapter-body" contenteditable="true" data-source-file="{source_file}">
{body_html}
      </div>{notes_html}
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
__CSS__
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
__SCRIPT__
</script>

</body>
</html>
"""

page = page.replace("__TOC__", toc_html).replace("__ARTICLES__", articles_html).replace("__KICKER__", html.escape(KICKER_TEXT))
page = page.replace("__CSS__", CSS).replace("__SCRIPT__", SCRIPT)
page = page.replace("—", "-")  # Replace em-dashes with hyphens
open(OUT, "w", encoding="utf-8").write(page)
print("chapters:", len(chapters))
for f in chapter_files:
    print(" -", os.path.basename(f))
print("timeline items:", len(tl_items),
      "| characters:", sum(len(v) for v in cards_by.values()),
      "| places:", len(place_rows))
print("written:", OUT, len(page), "chars")
