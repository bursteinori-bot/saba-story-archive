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
    var base = el.className.replace(/\s*(saving|saved|error)\b/g, '').trim();
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
        var body = section.replace(/^\s*\n##[^\n]*\n/, '').trim();
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

  // עריכה ישירה על גבי הטקסט - כל הפרק הוא שטח עריכה רציף אחד: אפשר למחוק
  // ציטוט לגמרי, להוסיף פסקה חדשה (Enter), למזג פסקאות (Backspace בתחילת
  // שורה). שמירה אוטומטית (debounce) דרך אותה פונקציה עננית: קוראים את
  // הקובץ המלא הנוכחי, מחליפים רק את בלוקי הגוף (שומרים כותרת/תקופה/הערות
  // כפי שהיו), וכותבים בחזרה.
  document.querySelectorAll('.chapter-body').forEach(function (body) {
    var cid = body.closest('article.chapter').id;
    var sourceFile = body.getAttribute('data-source-file');
    var statusEl = document.querySelector('[data-inline-status="' + cid + '"]');
    var timer = null;

    function serializeEditable(el) {
      var out = '';
      el.childNodes.forEach(function (node) {
        if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains('needs-rework')) {
          var note = node.getAttribute('title');
          out += '{{' + node.textContent + (note ? '::' + note : '') + '}}';
        } else {
          out += node.textContent;
        }
      });
      return out.trim();
    }

    function collectBodyBlocks() {
      var blocks = [];
      body.childNodes.forEach(function (el) {
        if (el.nodeType !== Node.ELEMENT_NODE) return;
        var text = serializeEditable(el);
        if (!text) return; // בלוק ריק (למשל ציטוט שנמחק) - פשוט לא נכלל
        blocks.push({ type: el.tagName === 'BLOCKQUOTE' ? 'quote' : 'p', text: text });
      });
      return blocks;
    }

    function spliceChapterFile(rawFullText, bodyBlocks) {
      var lines = rawFullText.replace(/^\s+/, '').split('\n');
      var headEnd = 1;
      if (lines[1] && /^_.*_$/.test(lines[1].trim())) headEnd = 2;
      var tailStart = -1;
      for (var i = headEnd; i < lines.length; i++) {
        if (/^\*\*(הערת רקע היסטורי|שאלות פתוחות)/.test(lines[i].trim())) { tailStart = i; break; }
      }
      var head = lines.slice(0, headEnd).join('\n');
      var tail = tailStart === -1 ? '' : lines.slice(tailStart).join('\n');
      var bodyText = bodyBlocks.map(function (b) {
        return b.type === 'quote' ? '> ' + b.text : b.text;
      }).join('\n\n');
      var result = head + '\n\n' + bodyText;
      if (tail) result += '\n\n' + tail;
      return result.trim() + '\n';
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
        setStatus(statusEl, 'saved', '✓ נשמר - יופיע באתר תוך כדקה');
      }).catch(function () {
        setStatus(statusEl, 'error', 'השמירה נכשלה - לחצו כאן לנסות שוב');
      });
    }

    // Enter פותח פסקה/ציטוט חדשים במקום שבירת שורה סתמית בתוך הפסקה הנוכחית
    body.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' || e.shiftKey) return;
      var sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      e.preventDefault();
      var range = sel.getRangeAt(0);
      range.deleteContents();
      var container = range.startContainer;
      var block = (container.nodeType === 1 ? container : container.parentElement).closest('p, blockquote');
      if (!block || block.parentElement !== body) {
        var p = document.createElement('p');
        p.appendChild(document.createTextNode('\u200b'));
        body.appendChild(p);
        placeCaret(p, 0);
        return;
      }
      var afterRange = range.cloneRange();
      afterRange.selectNodeContents(block);
      afterRange.setStart(range.endContainer, range.endOffset);
      var afterFragment = afterRange.extractContents();
      var newBlock = document.createElement(block.tagName === 'BLOCKQUOTE' ? 'blockquote' : 'p');
      newBlock.appendChild(afterFragment);
      if (!newBlock.textContent) newBlock.appendChild(document.createTextNode('\u200b'));
      block.parentElement.insertBefore(newBlock, block.nextSibling);
      placeCaret(newBlock, 0);
      body.dispatchEvent(new Event('input', { bubbles: true }));
    });
    function placeCaret(el, offset) {
      var r = document.createRange();
      var node = el.firstChild || el;
      r.setStart(node, Math.min(offset, node.textContent ? node.textContent.length : 0));
      r.collapse(true);
      var s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
    }

    body.addEventListener('input', function () {
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

  // סימון "טעון שיפור": מרחפים מעל פסקה, מופיע דגל קטן בפינה שלה, לחיצה
  // עליו מסמנת את כל הפסקה (לא דורש גרירה מדויקת לבחירת טקסט - קשה מדי
  // לבצע בדיוק). נפתח פופאובר אדום עם אפשרות להוסיף הערה קצרה (לא חובה).
  // לחיצה על פסקה שכבר מסומנת פותחת את אותו פופאובר לעריכת ההערה או
  // הסרת הסימון.
  var markPopover = document.createElement('div');
  markPopover.className = 'mark-rework-popover';
  markPopover.hidden = true;
  markPopover.innerHTML =
    '<input type="text" class="mark-rework-input" placeholder="מה צריך לשפר כאן? (לא חובה)">' +
    '<div class="mark-rework-actions">' +
    '<button type="button" class="mark-rework-confirm">סמן</button>' +
    '<button type="button" class="mark-rework-remove" hidden>הסר סימון</button>' +
    '</div>';
  document.body.appendChild(markPopover);
  var markInput = markPopover.querySelector('.mark-rework-input');
  var markConfirmBtn = markPopover.querySelector('.mark-rework-confirm');
  var markRemoveBtn = markPopover.querySelector('.mark-rework-remove');
  var pendingRange = null;
  var pendingMark = null;

  function openPopoverAt(rect, existingNote) {
    markPopover.hidden = false;
    markPopover.style.top = (window.scrollY + rect.top - 74) + 'px';
    markPopover.style.left = (window.scrollX + rect.left) + 'px';
    markInput.value = existingNote || '';
    markRemoveBtn.hidden = existingNote === undefined;
    setTimeout(function () { markInput.focus(); }, 0);
  }
  function closePopover() {
    markPopover.hidden = true;
    pendingRange = null;
    pendingMark = null;
  }

  var justOpenedPopover = false;

  // דגל צף אחד שעוקב אחרי הפסקה שהעכבר מרחף מעליה כרגע - נמנעים מלהזריק
  // כפתור לכל פסקה בנפרד כדי לא להסתבך עם פיצול/מיזוג פסקאות בעריכה.
  var flagBtn = document.createElement('button');
  flagBtn.type = 'button';
  flagBtn.className = 'para-flag-btn';
  flagBtn.title = 'סמן פסקה זו לשיפור';
  flagBtn.textContent = '🚩';
  flagBtn.hidden = true;
  document.body.appendChild(flagBtn);
  var flagTargetBlock = null;

  function wholeParagraphMark(block) {
    var marks = block.querySelectorAll(':scope > .needs-rework');
    if (marks.length !== 1) return null;
    return marks[0].textContent.trim() === block.textContent.trim() ? marks[0] : null;
  }
  function positionFlagBtn(block) {
    var rect = block.getBoundingClientRect();
    flagTargetBlock = block;
    flagBtn.hidden = false;
    flagBtn.style.top = (window.scrollY + rect.top - 6) + 'px';
    flagBtn.style.left = (window.scrollX + rect.right - 26) + 'px';
  }
  document.querySelectorAll('.chapter-body').forEach(function (cb) {
    cb.addEventListener('mouseover', function (e) {
      var block = e.target.closest('p, blockquote');
      if (block && block.parentElement === cb) positionFlagBtn(block);
    });
    cb.addEventListener('mouseleave', function () {
      setTimeout(function () { if (!flagBtn.matches(':hover')) flagBtn.hidden = true; }, 60);
    });
  });
  flagBtn.addEventListener('mouseleave', function () { flagBtn.hidden = true; });
  flagBtn.addEventListener('click', function () {
    if (!flagTargetBlock) return;
    var existing = wholeParagraphMark(flagTargetBlock);
    if (existing) {
      pendingMark = existing;
      pendingRange = null;
      openPopoverAt(existing.getBoundingClientRect(), existing.getAttribute('title') || '');
    } else {
      var range = document.createRange();
      range.selectNodeContents(flagTargetBlock);
      pendingRange = range;
      pendingMark = null;
      openPopoverAt(flagTargetBlock.getBoundingClientRect());
    }
    justOpenedPopover = true;
    flagBtn.hidden = true;
  });

  markConfirmBtn.addEventListener('click', function () {
    var note = markInput.value.trim();
    if (pendingMark) {
      if (note) pendingMark.title = note; else pendingMark.removeAttribute('title');
      pendingMark.dispatchEvent(new Event('input', { bubbles: true }));
    } else if (pendingRange) {
      try {
        var span = document.createElement('span');
        span.className = 'needs-rework';
        if (note) span.title = note;
        pendingRange.surroundContents(span);
        span.dispatchEvent(new Event('input', { bubbles: true }));
      } catch (e) { /* בחירה שחוצה כמה אלמנטים - מדלגים */ }
    }
    window.getSelection().removeAllRanges();
    closePopover();
  });
  markRemoveBtn.addEventListener('click', function () {
    if (pendingMark) {
      var parent = pendingMark.parentNode;
      while (pendingMark.firstChild) parent.insertBefore(pendingMark.firstChild, pendingMark);
      parent.removeChild(pendingMark);
      parent.normalize();
      parent.dispatchEvent(new Event('input', { bubbles: true }));
    }
    closePopover();
  });
  markInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); markConfirmBtn.click(); }
    else if (e.key === 'Escape') { closePopover(); }
  });
  document.addEventListener('click', function (e) {
    if (justOpenedPopover) { justOpenedPopover = false; return; }
    var mark = e.target.closest('.needs-rework');
    if (mark && window.getSelection().isCollapsed) {
      pendingMark = mark;
      pendingRange = null;
      openPopoverAt(mark.getBoundingClientRect(), mark.getAttribute('title') || '');
      return;
    }
    if (!markPopover.hidden && !markPopover.contains(e.target) && !e.target.closest('.needs-rework')) {
      closePopover();
    }
  });
})();
