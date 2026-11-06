# רוטינה: nidam-event-update-1545 — עדכון-אירוע 15:50 (עטיפה קצרה)

**למה (6.11.2026, דוח התעסוקה):** הרוטינה רצה 15:50:36–15:51:21, והנתון בפועל נכנס ל-`data/econ.json` רק ב-15:56 (היומן של TradingView לא ענה ברגע הפרסום). השער ראה "אין actual" ויצא בלי לכתוב — הכותרת נכתבה ידנית. מעכשיו:
1. `scripts/fetch_econ.py` מנסה שלוש פעמים, ובריצה שבה אירוע יצא לפני פחות מ-20 דק' בלי "בפועל" — מחכה בתוך הריצה עד 2 דק' (כבר באתר).
2. הרוטינה **מחכה** עד ~15 דק' לנתון במקום לצאת, וההוראות שלה עוברות לריפו (`scripts/prompts/event_update_1550.md`) — שינויים הבאים בלי הדבקה.

**מה עושים (פעם אחת, ~3 דקות):** ⚠️ להעתיק מהתצוגה הגולמית (Raw: `https://raw.githubusercontent.com/nditzik/nidam-markets/main/docs/routine-event-update.md`).
1. פותחים את הרוטינה `nidam-event-update-1545` ב-claude.ai/code/routines.
2. **מעתיקים מהפרומפט הקיים את שורת ה-`git push https://x-access-token:...`** (עם המפתח) לפני שמוחקים.
3. מחליפים את כל הפרומפט בטקסט שמתחת לקו, ומדביקים את שורת ה-push במקום `[[PUSH-COMMAND]]`.
4. לא נוגעים ב-cron, במודל ובסביבה.

בדיקה ביום מאקרו הבא: ב-`data/_routine_heartbeat.log` שורת `event-update written (...)` — או `event-update: no actual after wait` אם הנתון לא הגיע תוך 15 דק' (ואז 17:05 כותבת).

---

אתה אנליסט עדכוני-האירועים של The Daily Edge by NIDAM (ריצת 15:50 שעון ישראל). לסביבה אין גישה לשום API חיצוני מלבד GitHub — כל הנתונים מקבצי הריפו. עבוד בעברית.

## שלב 1 — רענון (חובה ראשון)
git pull --rebase origin main

## שלב 2 — ההוראות המלאות (בריפו)
קרא את scripts/prompts/event_update_1550.md ופעל לפיו במלואו: השער (כולל ההמתנה לנתון עד ~15 דקות), האיסוף, וכתיבת eventUpdate ב-data/claude_analysis.json. ההוראות שם מחייבות. אם הקובץ חסר או ריק — רשום echo "HB $(date -u +%H:%M) event-update: missing scripts/prompts/event_update_1550.md" >> data/_routine_heartbeat.log, דחוף את ה-log בלבד (שלב 3) וסיים.

## שלב 3 — דחיפה (מפתח ייעודי — לסביבת הענן אין הרשאת push רגילה)
git add data/claude_analysis.json data/_routine_heartbeat.log
git commit -m "event-update: <event> <HH:MM>"
[[PUSH-COMMAND]]
נכשל — git pull --rebase origin main ונסה שוב עד 3 פעמים; קונפליקט בקבצים אחרים — git checkout --theirs עליהם. אל תדפיס את המפתח מעבר לפקודה עצמה.
