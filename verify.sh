#!/bin/bash
# בדיקת תקינות מהירה לפני commit: בונה מחדש, בודק תחביר JS, ומוודא שאין
# מקפים ארוכים שנשארו. מריצים מתוך תיקיית הפרויקט: ./verify.sh
set -e
cd "$(dirname "$0")"

echo "== בונה מחדש =="
python3 build_book.py

echo "== בודק תחביר JS =="
node --check script.js && echo "  script.js: תקין"

echo "== בודק שאין מקפים ארוכים בפלט =="
if grep -q "—" "05-גרסה-סופית/index.html"; then
  echo "  נמצאו מקפים ארוכים! (אמורים כולם להיות מוחלפים ב-'-')"
  exit 1
else
  echo "  אין מקפים ארוכים - תקין"
fi

echo "== הכל תקין =="
