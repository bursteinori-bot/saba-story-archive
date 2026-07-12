// פרוקסי קטן: מקבל שינויים מהאתר הציבורי (בלי שום התחברות מהצד השני),
// ושומר אותם ישירות בריפו בעזרת מפתח GitHub שמור בענן (סוד),
// שלעולם לא נחשף לדפדפן של הקורא.
//
// שתי יכולות:
//  - הערות קוראים (קובץ יחיד, 06-הערות-קוראים.md) - כתיבה ממוקדת לפי מזהה פרק.
//  - עריכת הסיפור עצמו - קריאה/כתיבה של קובצי הפרקים ב-03-פרקים/,
//    מוגבלת לרשימה סגורה של קבצים (whitelist) כדי שאי אפשר יהיה לכתוב
//    לשום קובץ אחר בריפו (כמו workflow או את ה-worker עצמו).

const OWNER = "bursteinori-bot";
const REPO = "saba-story-archive";
const NOTES_PATH = "06-הערות-קוראים.md";
const BRANCH = "main";
const ALLOWED_ORIGIN = "https://bursteinori-bot.github.io";
const MAX_NOTE_LENGTH = 4000;
const MAX_CHAPTER_LENGTH = 40000;

// כל קובץ שמותר לערוך מהאתר - שום דבר אחר לא יתקבל, גם אם יתבקש.
const EDITABLE_CHAPTER_FILES = new Set([
  "03-פרקים/פרק-01-שורשים.md",
  "03-פרקים/פרק-02-המלחמה.md",
  "03-פרקים/פרק-03-ירושלים.md",
  "03-פרקים/פרק-04-ילד-של-משפחות-אחרות.md",
  "03-פרקים/פרק-05-הילד-עם-הציורים.md",
  "03-פרקים/פרק-06-הארמון.md",
  "03-פרקים/פרק-07-אחת-בחודש-באוטובוס.md",
  "03-פרקים/פרק-08-פוטו.md",
  "03-פרקים/פרק-09-לבנות-את-עצמי-לבד.md",
  "03-פרקים/פרק-10-לאיזה-כוכב-הגעתי.md",
]);

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(data, status, extraHeaders) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders(), ...(extraHeaders || {}) },
  });
}

function b64EncodeUnicode(str) {
  return btoa(String.fromCharCode(...new TextEncoder().encode(str)));
}
function b64DecodeUnicode(str) {
  return new TextDecoder().decode(Uint8Array.from(atob(str), (c) => c.charCodeAt(0)));
}

function replaceNoteSection(fullText, chapterId, newBody) {
  const marker = "<!-- note:" + chapterId + " -->";
  const idx = fullText.indexOf(marker);
  if (idx === -1) {
    return fullText.replace(/\s*$/, "") + "\n\n" + marker + "\n## " + chapterId + "\n" + newBody.trim() + "\n";
  }
  const afterMarker = idx + marker.length;
  let nextIdx = fullText.indexOf("<!-- note:", afterMarker);
  if (nextIdx === -1) nextIdx = fullText.length;
  const section = fullText.slice(afterMarker, nextIdx);
  const headingMatch = section.match(/^\s*\n##[^\n]*\n/);
  const headingPart = headingMatch ? headingMatch[0] : "\n## \n";
  const newSection = headingPart + newBody.trim() + "\n\n";
  return fullText.slice(0, afterMarker) + newSection + fullText.slice(nextIdx);
}

async function ghFetch(path, token, init) {
  return fetch("https://api.github.com/repos/" + OWNER + "/" + REPO + path, {
    ...init,
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "User-Agent": "saba-notes-proxy",
      ...(init && init.headers),
    },
  });
}

async function readFile(path, token) {
  const res = await ghFetch("/contents/" + encodeURIComponent(path) + "?ref=" + BRANCH, token);
  if (!res.ok) return null;
  const data = await res.json();
  return { sha: data.sha, content: b64DecodeUnicode(data.content.replace(/\n/g, "")) };
}

async function writeFile(path, token, content, sha, message) {
  return ghFetch("/contents/" + encodeURIComponent(path), token, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, content: b64EncodeUnicode(content), sha, branch: BRANCH }),
  });
}

async function handleGet(request, env) {
  const url = new URL(request.url);
  const fileParam = url.searchParams.get("file");

  if (fileParam) {
    if (!EDITABLE_CHAPTER_FILES.has(fileParam)) {
      return json({ error: "unknown file" }, 400);
    }
    const file = await readFile(fileParam, env.GH_TOKEN);
    if (!file) return json({ error: "could not read chapter file" }, 502);
    return json({ content: file.content });
  }

  const file = await readFile(NOTES_PATH, env.GH_TOKEN);
  if (!file) return json({ error: "could not read notes file" }, 502);
  // מטמון קצר בקצה הרשת של Cloudflare - מספיק כדי לא להכביד על ה-API
  // של GitHub בזמן שכמה בני משפחה גולשים בו-זמנית, בלי לגרום לעיכוב מורגש.
  return json({ content: file.content }, 200, { "Cache-Control": "public, max-age=15" });
}

async function handleSaveNote(body) {
  const chapterId = String(body.chapterId || "");
  const text = String(body.text || "");
  if (!/^chapter-\d{1,3}$/.test(chapterId)) return json({ error: "invalid chapterId" }, 400);
  if (text.length > MAX_NOTE_LENGTH) return json({ error: "note too long" }, 400);
  return { path: NOTES_PATH, message: "הערת קורא: " + chapterId, buildContent: (current) => replaceNoteSection(current, chapterId, text) };
}

async function handleSaveChapter(body) {
  const file = String(body.file || "");
  const content = String(body.content || "");
  if (!EDITABLE_CHAPTER_FILES.has(file)) return json({ error: "unknown file" }, 400);
  if (content.length > MAX_CHAPTER_LENGTH || content.trim().length === 0) return json({ error: "invalid chapter content" }, 400);
  return { path: file, message: "עריכת קורא: " + file, buildContent: () => content };
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method === "GET") {
      try {
        return await handleGet(request, env);
      } catch (e) {
        return json({ error: "unexpected error: " + e.message }, 500);
      }
    }
    if (request.method !== "POST") {
      return json({ error: "method not allowed" }, 405);
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return json({ error: "invalid JSON" }, 400);
    }

    try {
      const kind = String(body.kind || "note");
      const plan = kind === "chapter" ? await handleSaveChapter(body) : await handleSaveNote(body);
      if (plan instanceof Response) return plan; // ולידציה נכשלה

      const current = await readFile(plan.path, env.GH_TOKEN);
      if (!current) return json({ error: "could not read target file" }, 502);
      const updated = plan.buildContent(current.content);

      const putRes = await writeFile(plan.path, env.GH_TOKEN, updated, current.sha, plan.message);
      if (!putRes.ok) {
        const errBody = await putRes.text();
        return json({ error: "save failed (" + putRes.status + ")", detail: errBody.slice(0, 200) }, 502);
      }
      return json({ ok: true });
    } catch (e) {
      return json({ error: "unexpected error: " + e.message }, 500);
    }
  },
};
