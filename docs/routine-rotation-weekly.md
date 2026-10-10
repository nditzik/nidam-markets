# רוטינה: nidam-rotation-weekly — דוח הרוטציה הסקטוריאלית מקובצי הדרייב

**סטטוס 10.10.2026 (ערב):** ✅ **נוצרה ע"י איציק ב-UI** — `trig_01PBFS69zLJY5iv6rBgkxz6p`, cron `0 6 * * 6` (UTC; שבת 09:00 שעון ישראל בקיץ, 08:00 בחורף — ה-UI מאפשר שעה אחת בלבד; נוסה להרחיב ל-`CRON_TZ=Asia/Jerusalem 0 7-12 * * 6` מהסשן — ראו למטה), מחבר Google Drive מסומן, מודל ברירת מחדל. ניסיון ליצור אותה מהסשן נכשל (הפלטפורמה לא מעבירה מחברים לרוטינה שנוצרת מכאן — "connectors parameter is not available for this organization"). גוף ההוראות ב-`scripts/prompts/rotation_weekly.md`; המספרים ב-`scripts/build_rotation.py`; המתודולוגיה ב-`docs/rotation/METHOD.md`.

**הדחיפה:** בפועל המפתח יושב **בתוך הפרומפט** כמו ב-7 הרוטינות האחרות — מפתח חדש `nidam-routine-push-2` (Fine-grained, Contents לריפו הזה, נוצר 10.10.2026, ⏰ תוקף ~10/2027). התכנון המקורי (משתנה סביבה `NIDAM_PUSH_PAT`) לא יצא לפועל: איציק לא מצא את מסך עריכת הסביבה ב-UI (Settings → Claude Code אין בו Environments), ולרוטינה ב-UI אין שדה משתני סביבה. העטיפה למטה נשארת בגרסת המשתנה לעתיד; בהדבקה מחליפים את שורת ה-`if` בפקודת push עם המפתח. ⏳ עדיין פתוח: למצוא את מסך הסביבה, להעביר את 8 הרוטינות למשתנה ולמחוק את שני המפתחות הגלויים.

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
