// פרוקסי קטן: מקבל הערת קורא מהאתר הציבורי (בלי שום התחברות מהקורא),
// ושומר אותה ישירות ב-06-הערות-קוראים.md בעזרת מפתח GitHub שמור בענן (סוד),
// שלעולם לא נחשף לדפדפן של הקורא.

const OWNER = "bursteinori-bot";
const REPO = "saba-story-archive";
const NOTES_PATH = "06-הערות-קוראים.md";
const BRANCH = "main";
const ALLOWED_ORIGIN = "https://bursteinori-bot.github.io";
const MAX_TEXT_LENGTH = 4000;

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(data, status) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() },
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
  const res = await fetch("https://api.github.com/repos/" + OWNER + "/" + REPO + path, {
    ...init,
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "User-Agent": "saba-notes-proxy",
      ...(init && init.headers),
    },
  });
  return res;
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
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

    const chapterId = String(body.chapterId || "");
    const text = String(body.text || "");

    if (!/^chapter-\d{1,3}$/.test(chapterId)) {
      return json({ error: "invalid chapterId" }, 400);
    }
    if (text.length > MAX_TEXT_LENGTH) {
      return json({ error: "note too long" }, 400);
    }

    try {
      const getRes = await ghFetch("/contents/" + encodeURIComponent(NOTES_PATH) + "?ref=" + BRANCH, env.GH_TOKEN);
      if (!getRes.ok) {
        return json({ error: "could not read notes file (" + getRes.status + ")" }, 502);
      }
      const fileData = await getRes.json();
      const currentContent = b64DecodeUnicode(fileData.content.replace(/\n/g, ""));
      const updated = replaceNoteSection(currentContent, chapterId, text);

      const putRes = await ghFetch("/contents/" + encodeURIComponent(NOTES_PATH), env.GH_TOKEN, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "הערת קורא: " + chapterId,
          content: b64EncodeUnicode(updated),
          sha: fileData.sha,
          branch: BRANCH,
        }),
      });
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
