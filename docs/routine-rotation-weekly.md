# רוטינה: nidam-rotation-weekly — דוח הרוטציה הסקטוריאלית מקובצי הדרייב

**סטטוס 10.10.2026:** ⏳ **איציק ליצור את הרוטינה ב-claude.ai/code/routines** (ניסיון ליצור אותה מהסשן נכשל: הפלטפורמה לא מעבירה מחברים לרוטינה שנוצרת מכאן — "connectors parameter is not available for this organization"; רוטינה בלי המחבר לא יכולה לקרוא את הדרייב). הגדרות: שם `nidam-rotation-weekly` · הפרומפט שלמטה (להעתיק מ-Raw) · cron `CRON_TZ=Asia/Jerusalem 0 7-12 * * 6` או בשעון UTC `0 4-9 * * 6` (קיץ; בחורף `0 5-10 * * 6`) · סביבה `env_01HuUSRgi26Njgf7bJ391qw9` · מודל `claude-sonnet-5` · **מחבר Google Drive מסומן**. אחרי היצירה — לרשום כאן את ה-trig id. גוף ההוראות ב-`scripts/prompts/rotation_weekly.md`; המספרים ב-`scripts/build_rotation.py`; המתודולוגיה ב-`docs/rotation/METHOD.md`.

**הדחיפה — בלי מפתח בפרומפט:** הפקודה קוראת את משתנה הסביבה `NIDAM_PUSH_PAT` (Fine-grained PAT, הרשאת Contents לריפו הזה בלבד). ⏳ **איציק להוסיף את המשתנה בהגדרות הסביבה** (תפריט סביבת הענן בכותרת הסשן ← Edit ← משתני סביבה; שם: `NIDAM_PUSH_PAT`, ערך: מפתח חדש מ-GitHub). עד אז הרוטינה כותבת, מבצעת commit ומדווחת שהדחיפה ממתינה — בלי לדחוף.

**הזרימה בשבת:** גרוק מעלה `Rotation/YYYY-MM-DD` (~06:00) → הרוטינה (07:00, ואז כל שעה עד 12:00 אם התיקייה עוד לא שם) מורידה 20 קבצים דרך המחבר → `build_rotation.py check/compute` → כותבת `narrative.json` → `render` → דוחפת `data/sectors/sectors-D.html` + `data/sector_history.json` + הקבצים. ה-Action של האתר (15 דק') מציג את הדוח בטאב סקטורים (דוח מקומי גובר על העותק מ-nidam-reports, `fetch_sectors.local_reports`), `build_weekly` קורא ממנו את "בחמישה משפטים" ואת "הכסף יצא/נכנס", ורוטינת הסיכום השבועי כותבת את הסיכום מחדש פעם אחת (`sectorsDate`).

**בדיקה בשבת (17.10):** ב-`data/_routine_heartbeat.log` שורת `rotation written 2026-10-17 week=12`; `data/sectors/sectors-2026-10-17.html` באתר; ב-`data/sector_history.json` 12 שבועות. אם הרוטינה רשמה `no drive folder` כל הבוקר — גרוק לא העלה.

**הרצה ידנית:** `python3 scripts/build_rotation.py compute 2026-10-10` על התיקייה בריפו מדפיס את התקציר; `render` מרכיב מחדש מ-`narrative.json`. לבדיקת פרומפט בלי לחכות לשבת — `update_trigger` עם `run_once_at` (ואז להחזיר את ה-cron).

---

## הפרומפט — `nidam-rotation-weekly`

אתה כותב את דוח הרוטציה הסקטוריאלית השבועי "לאן זרם הכסף השבוע?" ל-The Daily Edge by NIDAM (אתר עברי RTL של איציק נידם). ריצה שעתית בשבת בבוקר. הנתונים: תיקיית CSV שגרוק מעלה לדרייב (Rotation/YYYY-MM-DD) — אתה מוריד אותה דרך מחבר Google Drive, סקריפט בריפו מחשב את כל המספרים, ואתה כותב את המילים. עבוד בעברית. לסביבה הזו אין גישה לשום API חיצוני מלבד GitHub והמחבר — כל השאר מקבצי הריפו.

## שלב 1 — רענון
git pull --rebase origin main
git fetch --unshallow origin 2>/dev/null || true

## שלב 2 — ההוראות המלאות (גוף הפרומפט יושב בריפו)
קרא את הקובץ scripts/prompts/rotation_weekly.md ופעל לפיו במלואו: הוא מגדיר את השער (מתי רצים ומתי יוצאים), את ההורדה מהדרייב, את הפקודות (check / decode / compute / render של scripts/build_rotation.py), את מבנה narrative.json ואת כללי הכתיבה. ההוראות שם הן המחייבות. אם השער אומר לצאת — צא כפי שהוא מורה (שורת HB בלבד). אם הקובץ חסר או ריק — אל תכתוב דוח: רשום echo "HB $(date -u +%H:%M) rotation: missing scripts/prompts/rotation_weekly.md" >> data/_routine_heartbeat.log, בצע commit ל-log בלבד, דחוף (שלב 3) וסיים.

## שלב 3 — דחיפה (מפתח ייעודי במשתנה סביבה — לסביבת הענן אין הרשאת push רגילה)
אחרי ה-commit שההוראות מגדירות:
if [ -z "$NIDAM_PUSH_PAT" ]; then echo "push pending: NIDAM_PUSH_PAT not set"; else git push "https://x-access-token:${NIDAM_PUSH_PAT}@github.com/nditzik/nidam-markets.git" HEAD:main; fi
אם המשתנה חסר — אל תדחוף: השאר את ה-commit מקומי וסיים עם הודעה ברורה שהדחיפה ממתינה למשתנה הסביבה NIDAM_PUSH_PAT. אם הדחיפה נכשלת (ה-Action של האתר דוחף כל רבע שעה) — git pull --rebase origin main ונסה שוב עד 3 פעמים. קונפליקט בקבצי data אחרים — git checkout --theirs עליהם; בקבצים שכתבת (data/sectors/sectors-<D>.html, data/sector_history.json, data/rotation/) — שמור את הגרסה שלך. אל תדפיס את ערך המשתנה לעולם.

---

## היסטוריה
- **10.10.2026 — גרסה 1.** עד היום הדוח נכתב ידנית בשיחת claude.ai מצילומי מסך (סקיל `sector-rotation-weekly`, ההיסטוריה כקובץ שאיציק מעלה כל שבוע). מ-10.10 גרוק מוריד CSV לדרייב, המספרים עברו לסקריפט, וההיסטוריה (`data/sector_history.json`, 11 שבועות מ-1.8.2026) יושבת בריפו. הדוח הראשון מהצינור הזה (שבוע 11, 10.10) נבנה בסשן והוחלף במקום דוח הבוקר הידני.
