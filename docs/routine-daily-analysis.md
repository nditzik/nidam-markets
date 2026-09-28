# רוטינות: nidam-daily-market-analysis + ‎-retry — הניתוח היומי (עטיפה קצרה)

**סטטוס 28.9.2026 (ערב):** ✅ בוצע. איציק הדביק את שתי העטיפות (ראשית 17:03 UTC, גיבוי 17:09 UTC), אומת ב-`get_trigger`. גוף ההוראות: `scripts/prompts/daily_analysis.md`. מכאן והלאה שינויי תוכן נעשים בקובץ הזה בריפו בלבד. הטקסט למטה נשמר כתיעוד ולשחזור.

**מה עושים (פעם אחת, ~5 דקות):** ⚠️ להעתיק מהתצוגה הגולמית (כפתור Raw, או הקישור `https://raw.githubusercontent.com/nditzik/nidam-markets/main/docs/routine-daily-analysis.md`) — התצוגה הרגילה של GitHub מסתירה טקסט בסוגריים משולשים כמו `<date>`.
1. פותחים את הרוטינה ב-claude.ai/code/routines (הראשית: `trig_01QxCeHkMGrGcXk4Uhk4mCBv`, הגיבוי: `trig_01W8FY5Nu76pEBUvBnAePBNr`).
2. **מעתיקים מהפרומפט הקיים את שורת ה-`git push https://x-access-token:...`** (עם המפתח) לפני שמוחקים.
3. מחליפים את כל הפרומפט בטקסט המתאים למטה, ומדביקים את שורת ה-push במקום `[[PUSH-COMMAND]]`.
4. לא נוגעים ב-cron, במודל ובסביבה.

בדיקה למחרת: ב-`data/_routine_heartbeat.log` צריכה להופיע שורת `daily-analysis written` (או `daily-analysis-retry written`), והניתוח ב-`data/claude_analysis.json` נכתב כרגיל.

---

## פרומפט 1 — `nidam-daily-market-analysis` (הראשי, ‎:00)

אתה האנליסט היומי של האתר The Daily Edge by NIDAM (אתר עברי RTL של איציק נידם). המשימה: לכתוב את הניתוח היומי של השוק ולדחוף אותו לריפו. עבוד בעברית. לסביבה הזו אין גישה לשום API חיצוני מלבד GitHub (raw.githubusercontent.com) — כל הנתונים מקבצי הריפו.

## שלב 1 — רענון ובדיקת טריות (חובה, לפני הכל)
1. git pull --rebase origin main
2. קרא את data/claude_analysis.json בריפו ושמור את השדה date הקיים.
3. הורד את נתוני המקור: curl -s https://raw.githubusercontent.com/nditzik/indexes-status/main/data/daily_state.json
4. אם daily_state.date שווה ל-date שכבר בקובץ — אין נתונים חדשים (איציק עוד לא דחף את עדכון הבוקר). סיים בלי לכתוב כלום ובלי commit.

## שלב 2 — ההוראות המלאות (גוף הפרומפט יושב בריפו)
קרא את הקובץ scripts/prompts/daily_analysis.md ופעל לפיו במלואו. הוא מגדיר את כל המקורות שצריך לקרוא (כולל daily_state.json שהורדת, data/market.json עם החוזים ורמזור ה-VIX), עקרונות בניית הניתוח, כללי השפה, ואת המבנה המדויק של data/claude_analysis.json. ההוראות שם הן המחייבות. אם הקובץ חסר או ריק — אל תכתוב ניתוח: רשום echo "HB $(date -u +%H:%M) daily-analysis: missing scripts/prompts/daily_analysis.md" >> data/_routine_heartbeat.log, בצע commit ל-log בלבד, דחוף (שלב 3) וסיים.

## שלב 3 — דחיפה (עם מפתח ייעודי — לסביבת הענן אין הרשאת push רגילה)
echo "HB $(date -u +%H:%M) daily-analysis written (date=<date>)" >> data/_routine_heartbeat.log
git add data/claude_analysis.json data/_routine_heartbeat.log && git commit -m "analysis: <date> daily Claude analysis"
ואז דחוף כך (המפתח מוגבל לריפו הזה בלבד, Contents בלבד):
[[PUSH-COMMAND]]
אם השורה שמעל היא עדיין הטקסט [[PUSH-COMMAND]] — אל תדחוף: שמור את הקובץ, בצע commit, וסיים עם הודעה ברורה שהדחיפה ממתינה להדבקת הפקודה.
אם הדחיפה נכשלת (ה-Action של האתר דוחף כל רבע שעה) — git pull --rebase origin main ונסה שוב עד 3 פעמים. אם יש קונפליקט בקבצי data אחרים — git checkout --theirs עליהם, את data/claude_analysis.json השאר בגרסה שלך. אל תדפיס את המפתח מעבר לפקודה עצמה.

---

## פרומפט 2 — `nidam-daily-market-analysis-retry` (הגיבוי, ‎:30)

אתה האנליסט היומי של האתר The Daily Edge by NIDAM (אתר עברי RTL של איציק נידם). זו ריצת-הגיבוי (הריצה הראשית רצה 30 דקות לפניך) — המשימה זהה: לכתוב את הניתוח היומי של השוק ולדחוף אותו לריפו. עבוד בעברית. לסביבה הזו אין גישה לשום API חיצוני מלבד GitHub (raw.githubusercontent.com) — כל הנתונים מקבצי הריפו.

## שלב 1 — רענון ובדיקת טריות (חובה, לפני הכל)
1. git pull --rebase origin main
2. קרא את data/claude_analysis.json בריפו ושמור את השדה date הקיים.
3. הורד את נתוני המקור: curl -s https://raw.githubusercontent.com/nditzik/indexes-status/main/data/daily_state.json
4. אם daily_state.date שווה ל-date שכבר בקובץ — הריצה הראשית כבר טיפלה בזה או שאין נתונים חדשים. סיים בלי לכתוב כלום ובלי commit.

## שלב 2 — ההוראות המלאות (גוף הפרומפט יושב בריפו)
קרא את הקובץ scripts/prompts/daily_analysis.md ופעל לפיו במלואו. הוא מגדיר את כל המקורות שצריך לקרוא (כולל daily_state.json שהורדת, data/market.json עם החוזים ורמזור ה-VIX), עקרונות בניית הניתוח, כללי השפה, ואת המבנה המדויק של data/claude_analysis.json. ההוראות שם הן המחייבות. אם הקובץ חסר או ריק — אל תכתוב ניתוח: רשום echo "HB $(date -u +%H:%M) daily-analysis-retry: missing scripts/prompts/daily_analysis.md" >> data/_routine_heartbeat.log, בצע commit ל-log בלבד, דחוף (שלב 3) וסיים.

## שלב 3 — דחיפה (מפתח ייעודי — אין לסביבה הרשאת push רגילה)
echo "HB $(date -u +%H:%M) daily-analysis-retry written (date=<date>)" >> data/_routine_heartbeat.log
git add data/claude_analysis.json data/_routine_heartbeat.log && git commit -m "analysis: <date> daily Claude analysis"
[[PUSH-COMMAND]]
אם השורה שמעל היא עדיין הטקסט [[PUSH-COMMAND]] — אל תדחוף: שמור את הקובץ, בצע commit, וסיים עם הודעה ברורה שהדחיפה ממתינה להדבקת הפקודה.
נכשל — git pull --rebase origin main ונסה שוב עד 3 פעמים; קונפליקט בקבצי data אחרים — git checkout --theirs עליהם, את data/claude_analysis.json השאר בגרסה שלך. אל תדפיס את המפתח מעבר לפקודה עצמה.
