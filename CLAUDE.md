# CLAUDE.md — The Daily Edge by NIDAM

אתר עברי (RTL) סטטי ב-GitHub Pages: `nditzik.github.io/nidam-markets`. מרכז את תוכן השוק של איציק נידם ומתעדכן אוטומטית כל ~15 דקות. אין framework — HTML + CSS + JS ונילה, ופייתון stdlib בלבד בצד האיסוף.

## ארכיטקטורה

**הפרדת נתונים/תצוגה מוחלטת:** סקריפטים ב-`scripts/` כותבים `data/*.json`; הדפדפן רק מרנדר (`index.html`, `assets/app.js`, `assets/style.css`). כל סקריפט עמיד — כשל משיכה משאיר את הקובץ הקיים, ולכן שום מקור לא מפיל את האתר.

**עדכון אוטומטי:** `.github/workflows/update.yml` מופעל כל 15 דק' ע"י cron-job.org (ה-cron של GitHub לא אמין; ה-schedule הפנימי נשאר כגיבוי). כל צעד `continue-on-error`. הקומיט בסוף עמיד-מרוצים (rebase+retry×5).

**רענון בדפדפן:** `loadDaily()` + `loadLiveContent()` כל 5 דק' עם שומרי-שינוי (`contentSig`), `visibilitychange` מרענן בחזרה-לטאב, ציטוטים חיים כל דקה מהסורק של TradingView (טיקר + מפת חום סקטוריאלית).

**Cache-bust:** כל שינוי ב-app.js/style.css מחייב הקפצת `v=npN` ב-index.html (שתי שורות). נכון לעכשיו: np35.

## עיצוב "מהדורת עיתון" (2026-08-08)

הבית כעיתון: כותרת (לוגו+ניווט / חיפוש+שעון+חג-קרוב / שתי שורות טיקר + מפת חום סקטוריאלית) → ידיעה מובילה (תאריך היום → קיקר "יום המסחר" → H1 סריף) + רייל The Edge Meter (ציונים, "הכסף הגדול", שיאים/שפלים) → שלוש עמודות (תדרוך | מדווחות | בזק מהרשת) → מאקרו צפי-מול-בפועל → 🎲 מה השווקים מהמרים → מניות במוקד → בולטות. קווי-שיער במקום צללים; NEWSPAPER SKIN בסוף style.css דורס בקסקדה; דארק דרך טוקנים.

**פיצ'רים חיים בבית:** חיפוש כלל-אתרי (`initSearch` — כרטיס-טיקר עם ציטוט חי + טקסט חופשי, הכל על נתונים שבזיכרון, `/` פותח) · פס מבזק ⚡ (data/flash.json, כל הטאבים, TTL 3 שעות) · מפת חום 11 סקטורים (עדכון דקה, session-aware) · צ'יפי הסכמת-תחומים (aiSummary.domains) · שורת חג NYSE (לוח סטטי 2026-27 ב-app.js — מחווט גם לשעון: חגים ומסחר מקוצר 20:00; ⏰ לרענן ל-2028 בסוף 2027).

## רוטינות הענן (claude.ai/code/routines) — קרא לפני שנוגעים!

| רוטינה | trigger id | cron (UTC, קיץ) | תפקיד |
|---|---|---|---|
| nidam-daily-market-analysis | trig_01QxCeHkMGrGcXk4Uhk4mCBv | 30 3 * * 2-6 | ניתוח יומי 06:30 → claude_analysis.json. קורא גם data/market.json (חוזים ברגע הכתיבה) + data/earnings.json.week (דיווחי יום-יומיים אחרונים) כדי לתפוס תזוזת-סנטימנט לילית (27.8.2026: NVDA/CRWD/CRM) שהסגירה ב-daily_state עוד לא משקפת |
| ...-retry | trig_01W8FY5Nu76pEBUvBnAePBNr | 0 5 * * 2-6 | גיבוי 08:00 (no-op אם הראשי הצליח) |
| nidam-event-update-1545 | trig_01BZNrS3UZbLQMEeQh2pUDVT | 50 12 * * 1-5 | עדכון-אירוע 15:50 אחרי מאקרו 15:30 |
| nidam-event-update-1700 | trig_018imBgiWmzyXYKppZvnKWyA | 5 14 * * 1-5 | גרסת שוק-פתוח 17:05 |
| nidam-midday-1900 | trig_012hxPwq27eeJyr6ForerGjf | 0 16 * * 1-5 | מהדורת אמצע-יום 19:00 → eventUpdate עם kind:"midday" (קיקר כחול 🕑; אדום שמור למאקרו). כלל ההימורים: השוואה רק כש-key+sub זהים |
| nidam-preview-sun-mon | trig_01Ktgp3bjzo8rhp2eNNbuwvR | 45 4 * * 0,1 | "לקראת המסחר" ראשון+שני 07:45 → eventUpdate kind:"preview" (🗓, TTL 26ש'). משלב תדרוך+סקירת בוקר; ראשון=מבט שבוע, שני=מבט יום; מודע לחגי שני של NYSE. ⚠️ run_once_at ב-update מוחק את ה-cron — להחזיר אחרי |
| nidam-preopen-1535 | trig_015awmuLYu5owGgAp7DhNx7d | 35 12 * * 1-5 | "לקראת פתיחת המסחר" שני-שישי 15:35 → eventUpdate kind:"preopen" (🔔). מבוסס תדרוך הצהריים + בלוק "תמונת מצב" מה-HTML הגולמי שלו. שער: מדלגת בשקט אם יש נתון מאקרו מתוזמן היום (econ.json, גם אם actual עדיין null) — אז השרשרת 15:50/17:05 לוקחת; גם מסרבת לכתוב אם רצה מאוחר מדי (שוק כבר פתוח) |

**חוקי ברזל (נלמדו בדם, 11-13.8):**
1. **אין רשת:** ה-proxy של סביבת הענן חוסם כל API חיצוני (Yahoo/Polymarket/TradingView) ב-403 — מותר רק GitHub. כל פרומפט חייב לעבוד **מקבצי הריפו בלבד** (ה-Action מרענן אותם כל רבע שעה). "לפני" היסטורי — `git rev-list -1 --before=<ts> origin/main` + `git show SHA:file`.
2. **דחיפה עם PAT ייעודי** (`nidam-routine-push`, \u200FContents בלבד לריפו הזה, בתוך הפרומפטים): `git push https://x-access-token:<PAT>@github.com/nditzik/nidam-markets.git HEAD:main`. ⏰ תוקף עד ~08/2027. לאפליקציית GitHub אין הרשאה — אל תנסה push רגיל.
3. **הרצה ידנית (`action: run`) מתה בשקט** — באג פלטפורמה. להרצה מחדש: לעדכן `run_once_at` לעוד כמה דקות.
4. **ג'יטר מתזמן:** ריצות נורות 2–7 דק' אחרי ה-cron. ריצת 15:50 נוחתת בכותרת ~15:57–16:05 — לא לבהל לפני +10 דק'.
5. **אבחון:** אין גישה ליומני הענן מכאן — הטלמטריה היא `data/_routine_heartbeat.log` (הרוטינות רושמות שורת HB); במקרה חירום — פרומפט run_once שדוחף HEARTBEAT בכל שלב.
6. **כללי סגנון בפרומפטים:** בלי ז'רגון ("קצה היצרן" אסור, וכן אסור להשתמש במילים 'דלתא'/Delta או 'Flow' כפי שהן — לתרגם ל"הכסף הגדול הפך שורי/דובי" ו"עוצמת הפעילות באופציות"; כרגע מיושם רק ב-nidam-daily-market-analysis + retry, עוד לא הופץ ל-5 הרוטינות האחרות), מונח נחוץ מוסבר בקצרה; מדד ייחוס אחד — לפני פתיחה חוזה S&P, אחרי פתיחה "S&P 500" (לא "SPY"); מספרים מקבצים בלבד. **היקף "הכסף הגדול" (22.8.2026):** ה"דלתא"/הימור נטו של האופציות מבוסס על עסקאות בולטות/גדולות בלבד (data/spx-options-flow-*.csv ב-indexes-status, ~358 שורות), לא כל נפח המסחר היומי — לכן שונה בסדר גודל ממדדי "Delta Imbalance" כלל-שוקיים כמו Barchart (אלפים מול מיליונים). זו לא באג בנוסחה (אומתה ידנית + מול נתונים אמיתיים) אלא הבדל אוכלוסייה. הוחלט להשאיר את המדד כפי שהוא ולהוסיף הבהרה בלבד: tooltip ה-"הכסף הגדול" ב-app.js (`bigMoneyRow`), פסקת ה-stamp בכרטיס האופציות (`flowQuadHtml`), ופרומפט הניתוח היומי + retry.

**מולטי-לג ב"הכסף הגדול" (25.8.2026):** גילינו שרוב מוחלט (94% מהשורות, 99.8% מהפרמיה הכיוונית) בקובץ ה-CSV הן עסקאות מולטי-לג (קודי OPRA‏ CBMO/MFSL/MLET/MLFT — רגל אחת מתוך ספרד/קולר/קונדור וכו', לא הימור נאקד). אין ב-CSV מזהה הזמנה לשייך רגליים — רגל עלולה להיספר כהימור מלא גם אם היא רק חצי מעסקה מאוזנת. סימולציה על נתוני 24.8 האמיתיים: single-leg-בלבד (16 שורות בלבד) הפך את deltaLabel משורי לדובי — הוכחה שהכיוון של אותו יום *כן* יכול היה להיות שונה, אבל המדגם הזעיר (`$0-2M` מול מאות מיליונים) לא אמין כאלטרנטיבה בעצמו. **נבחר לא לסנן, אלא להוסיף שכבת ביטחון סימטרית** (`indexes-status` commit `34f125c`): `send_report.py` מחשב `legMultiPct`/`legTier`/`legNote` (מראה קיים של `midPct`/`confidence_tier`, אך עצמאי ומדבר על deltaTilt/deltaLabel ולא על ציון ה-Flow), משוקלל על אותה אוכלוסיית פרמיה-כיוונית שמזינה את `delta_net`; מסונף דרך `build_daily_state.py`. בצד nidam-markets (`bigMoneyRow`, np35): badge קטן (`.er-badge`, ⚠/⛔) ליד המילה שורי/דובי/מאוזן כש-legTier ∈ {low,limited,mid} — **מכוון-סימטרי בעיצוב** (תלוי רק ב-% לא בכיוון ה-label), אומת ויזואלית עבור שלושת הכיוונים + לייט/דארק. שדות חדשים = fallback חינני (אין badge) בדאטה ישן ללא השדות. **פוטנציאל להרחבה שלא בוצע:** הזרמת ה-caveat גם לתוך פרומפט ניתוח היום (narrative) כשה-legTier נמוך — לא התבקש במפורש, לשקול אם עולה שוב.
7. עריכת פרומפט: RemoteTrigger update עם job_config מלא (החלפה שלמה). כל שינוי מהותי — לעדכן גם כאן.

**מחזור הכותרת:** ניתוח 06:30 (date=סשן אתמול) ← eventUpdate נכתב באירועי מאקרו (15:50/17:05, TTL רנדרר 18ש') ← הניתוח של מחר כותב את הקובץ בלי eventUpdate = איפוס אוטומטי. הרנדרר קורא eventUpdate מ-CA הגולמי (לא מוגן-תאריך) בכוונה.

## צינורות (scripts/)

| סקריפט | פלט | מקור |
|---|---|---|
| fetch_dashboards | indices.json (+aiSummary+domains) | indexes-status repo |
| fetch_momentum / fetch_ibkr | momentum.json / candidates.json | ריפו-אחים |
| fetch_gmail / fetch_barchart | briefing.json / morning.json (+notice סופ"ש) + ארכיון 30 יום | Gmail IMAP |
| fetch_market | market.json (+spark) | Yahoo v8 chart |
| fetch_econ | econ.json (צפי/בפועל) | TradingView economic calendar |
| fetch_bets | bets.json (פד, מיתון, יעד SPY; CPI כשיש נזילות) | Polymarket Gamma + Kalshi (ציבוריים, בלי מפתח) |
| fetch_earnings / fetch_news / fetch_pulse / fetch_movers | earnings/news/pulse/movers | csv / RSS / טלגרם+Nitter (11 מקורות; xcancel מת) / TV scanner |
| fetch_sectors / fetch_trades | sectors.json / trades.json | nidam-reports |
| detect_flash | flash.json + טלגרם | ספייק 0.5%+/30 דק' (Yahoo 1m) + ראיות econ/pulse/news |
| archive_scores / archive_focus | history / focus_history | "המוקד במבחן" · archive_scores רץ תמיד *בתוך* fetch_dashboards.py (2.9.2026, כדי ש-history.json לא ייפרד מ-indices.json) — לא עוד שלב נפרד ב-update.yml |
| notify_* | טלגרם | תדרוך, תקציר, חריגים, דוחות-לילה 23:30 |

## תהליכי עבודה של איציק

שומרים ל-`C:\challenge\reports\...` — משימה מתוזמנת דוחפת כל 5 דק', האתר מושך תוך 15 דק': `sectors/`+`trades/` (HTML בשם עברי חופשי + תאריך), שורש — `TICKER__YYYY-MM-DD.html` + `earnings.csv`. בבוקר: דחיפת נתוני מדדים+מומנטום לפני 06:30.

## מלכודות שנלמדו בדם

1. **סדר push:** commit → `git pull --rebase` → push. קונפליקט ב-data: `git checkout --theirs` (הכל רגנרטיבי). מסר-קומיט עם גרשיים ב-PowerShell נשבר — `git commit -F msgfile`.
2. **iframe דוחות בנייד:** הכיווץ ב-`__fitFrame` הוא **transform:scale על מעטפת `#np-fit-scaler`** — לא zoom! (zoom ב-WebKit משנה layout ולא מתכנס; היה חיתוך+ריצוד). origin לפי כיוון המסמך (RTL ימין / LTR שמאל); html/body מקובעים לגודל הוויזואלי; refit בפתיחת טאב (iframe שנטען בפאנל מוסתר נמדד על clientWidth=0).
3. **WebKit + גריד:** `1fr` = minmax(auto,1fr), ו-WebKit מחשב min-content של flex בלי shrink — תוכן nowrap ארוך מנפח עמודות ושובר מובייל. תרופה: `min-width:0` על פריטי גריד. כרום מסתיר את זה — בדיקות מובייל רק ב-Playwright WebKit (viewport 390; chrome headless לא יורד מ-~500 רוחב — "גלישה" בצילום 390 היא ארטיפקט).
4. **CORS של סורק TradingView:** simple request בלבד — body כ-text/plain בלי content-type.
5. **פרסרי מיילים נשברים כשהמבנה משתנה** (קורה כל כמה ימים): לעגן בכותרות עברית; פורמט 2026-08-12 = div שטוחים עם `<br>`+בולטים; סנטימנט לוכד מעבר לתגיות פנימיות (`<span class="ltr">`) ושומר לטינית/ספרות.
6. **שעון חורף (~סוף אוקטובר):** להזיז את כל ה-crons — update.yml, cron-job.org, ו-7 רוטינות הענן.
7. עריכת קבצים עם אימוג'י/עברית — Write tool, לא heredoc.
8. **שינוי ויזואלי = צילום-עין לפני push** (Playwright screenshot) — לא רק בדיקה טכנית.

## החלטות מוצר מרכזיות

- מניות במוקד = מומנטום ∩ מועמדים בלבד; הארכיון חייב להישאר זהה ל-passesBase.
- טיקר: מחיר+אחוז בלבד. חדשות באנגלית. בזק מהרשת עדיף (עדכני).
- הימורים: הסתברות + שינוי יומי בנקודות; התפלגות מלאה לפד-ספטמבר; אירועי-סיכון נקודתיים נדחו במכוון.
- מבזק ⚡: מציג "מה שהתפרסם באותן דקות" — לא טוען סיבתיות. סף 0.5%/30 דק' (בניסיון כיול).
- GoatCounter — אנליטיקס; מעברי-טאב נספרים כצפיות.
