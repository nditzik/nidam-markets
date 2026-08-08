# CLAUDE.md — The Daily Edge by NIDAM

אתר עברי (RTL) סטטי ב-GitHub Pages: `nditzik.github.io/nidam-markets`. מרכז את תוכן השוק של איציק נידם ומתעדכן אוטומטית כל ~15 דקות. אין framework — HTML + CSS + JS ונילה, ופייתון stdlib בלבד בצד האיסוף.

## ארכיטקטורה

**הפרדת נתונים/תצוגה מוחלטת:** סקריפTM ב-`scripts/` כותבים `data/*.json`; הדפדפן רק מרנדר (`index.html`, `assets/app.js`, `assets/style.css`). כל סקריפט עמיד — כשל משיכה משאיר את הקובץ הקיים, ולכן שום מקור לא מפיל את האתר.

**עדכון אוטומטי:** `.github/workflows/update.yml` מופעל כל 15 דק' ע"י cron-job.org (ה-cron של GitHub לא אמין; ה-schedule הפנימי נשאר כגיבוי). כל צעד `continue-on-error`. הקומיט בסוף עמיד-מרוצים (rebase+retry×5).

**רענון בדפדפן:** `loadDaily()` + `loadLiveContent()` כל 5 דק' עם שומרי-שינוי (`contentSig` — האש בלי `_meta`; רינדור רק כשתוכן באמת השתנה), `visibilitychange` מרענן בחזרה-לטאב (נייד), וציטוטים חיים כל דקה ישירות מהסורק של TradingView.

## עיצוב "מהדורת עיתון" (2026-08-08)

הבית בנוי כעיתון: כותרת 3 שורות (לוגו+ניווט / שעון מסחר / שתי שורות טיקר רזות) → ידיעה מובילה (H1 סריף Frank Ruhl Libre) + רייל The Edge Meter → שלוש עמודות (תדרוך | מדווחות היום והשבוע | בזק מהרשת) → מאקרו צפי-מול-בפועל → מניות במוקד → בולטות. סגנון: קווי-שיער (`--paper-hair`) במקום צללים, שכבת NEWSPAPER SKIN בסוף `style.css` דורסת את סגנון-אפל הישן בקסקדה. דארק מלא דרך אותם טוקנים.

## הניתוח היומי של Claude

- `data/claude_analysis.json` — נכתב ע"י **routine בענן** (claude.ai/code/routines): ראשי 06:30 + גיבוי 08:00, ג'–שבת (cron UTC ‎`30 3 * * 2-6`‎ + ‎`0 5 * * 2-6`‎; ⚠️ חורף: להזיז שעה). שער-טריות: כותב רק כש-`daily_state.date` חדש.
- הבית מציג headline+tldr+bottomline; טאב מדדים את הניתוח המלא (`claudeCardHtml`). הגנת-תאריך + נפילה למנוע-הכללים (`aiSummary` בתוך indices.json).

## צינורות (scripts/)

| סקריפט | פלט | מקור |
|---|---|---|
| fetch_dashboards | indices.json (+aiSummary) | indexes-status repo |
| fetch_momentum | momentum.json | stocks-momentum repo |
| fetch_ibkr | candidates.json | nidam-candidates repo |
| fetch_gmail / fetch_barchart | briefing.json / morning.json + ארכיון 30 יום (`briefing_archive.py`) | Gmail IMAP (מיילים עצמיים) |
| fetch_market | market.json (+spark) | Yahoo v8 chart |
| fetch_econ | econ.json (צפי/בפועל) | TradingView economic calendar |
| fetch_earnings | earnings.json (+todayBig) | earnings.csv ב-nidam-reports |
| fetch_news / fetch_pulse | news.json / pulse.json | RSS פרימיום / שיקופי טלגרם+Nitter |
| fetch_movers | movers.json (סשן-מודע) | TradingView scanner |
| fetch_sectors / fetch_trades | sectors.json / trades.json (+method PDF) | nidam-reports (תיקיות sectors/, trades/) |
| archive_scores / archive_focus | history.json / focus_history.json | "המוקד במבחן" — צילום לפני פתיחה, הקפאה למחרת |
| notify_telegram / notify_digest / notify_alerts / notify_earnings_age | — | ערוץ טלגרם (תקציר בוקר ג'–שבת, התראות חריגים, סיכום דוחות 23:30) |

## תהליכי עבודה של איציק (קבצים → אתר)

שומרים ל-`C:\challenge\reports\...‎` — משימה מתוזמנת דוחפת ל-nidam-reports כל 5 דק', האתר מושך תוך 15 דק':
- `sectors/` ו-`trades/` — דוחות HTML; **שם עברי חופשי + תאריך `D.M.YYYY` או ISO בשם**. חדש עולה ראשון, קודמים הופכים לצ'יפי-ארכיון אוטומטית. PDF ב-trades/ = מסמך השיטה (קטגוריה קבועה, קישור raw — לא מועתק).
- שורש — ניתוחי דוחות `TICKER__YYYY-MM-DD.html` + `earnings.csv` שבועי.

## מלכודות שנלמדו בדם

1. **סדר push:** commit קודם, ואז `git pull --rebase`, ואז push. לעולם לא autostash לפני commit — קונפליקט נכתב לתוך data/*.json ומתקמט. קונפליקטים ב-data: ‎`git checkout --theirs`‎ (הכל רגנרטיבי).
2. **iframe בנייד (iOS):** מידות מבחוץ לא נאכפות — הכיווץ נעשה בתוך המסמך (`__fitFrame`: zoom על html + ביטול font-boosting עם `text-size-adjust:100%` + מדידת ילדים/נכדים כי מעטפות ממורכזות מסתירות גלישה מ-scrollWidth).
3. **צילומי-מסך headless ברוחב נייד:** ל-Chrome יש רוחב-חלון מינימלי (~489) — "גלישה" בצילום 390 היא ארטיפקט. לבדוק scrollWidth אמיתי לפני שמתקנים.
4. **CORS של הסורק TradingView:** עובד מהאתר רק כ-simple request — body כ-text/plain, בלי content-type.
5. **פרסר המיילים נשבר כשהמבנה משתנה** — לעגן בכותרות עברית + הטבלה/רשימה הקרובה, לא במבנה. `<b[^>]*>` תופס גם `<br>`.
6. **שעון חורף (~סוף אוקטובר):** להזיז את כל ה-crons — update.yml, cron-job.org, ושתי ה-routines של הניתוח.
7. עריכת קבצים עם אימוג'י — Write tool + כתיבה אטומית, לא heredoc עם escapes.

## החלטות מוצר מרכזיות

- מניות במוקד = מומנטום ∩ מועמדים בלבד (בלי בולטות — מתחלפות כל רבע שעה); הארכיון (`archive_focus.py`) חייב להישאר זהה ל-`passesBase` ב-app.js.
- טיקר: מחיר + אחוז בלבד (בלי גרפים-מיני — משוב קוראים). המדדים למעלה, חוזים+דולר/שקל בשורה התחתונה.
- חדשות באנגלית (תרגום-מכונה אכזב); בזק מהרשת עדיף כי עדכני יותר.
- GoatCounter (`nidam.goatcounter.com`) — אנליטיקס; מעברי-טאב נספרים כצפיות.
