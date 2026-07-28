# שוק ההון של איציק נידם

אתר סטטי (GitHub Pages) המרכז את הדשבורדים והתדריכים בטאבים, עם עדכון אוטומטי פעמיים ביום.

## מבנה
- `index.html` — דף בית (סקירת שוק) + טאבים
- `assets/style.css`, `assets/app.js` — עיצוב ולוגיקה (ונילה, ללא פריימוורק)
- `data/*.json` — כל הנתונים; ה-HTML רק מרנדר
- `scripts/fetch_dashboards.py` — מושך מדדים מ-indexes-status → `data/indices.json`
- `.github/workflows/update.yml` — Action פעמיים ביום + הרצה ידנית

## סטטוס טאבים
| טאב | מצב | מקור |
|---|---|---|
| בית / מדדים | ✅ חי | `indexes-status` |
| מומנטום | ✅ חי | `stocks-momentum` |
| סקירת בוקר | ✅ חי | Barchart Pre-Market Bulletin (ג'ימייל) |
| תדרוך משקיעים | ✅ חי | הבריפים העצמיים (ג'ימייל) |
| מועמדים (IBKR) | ✅ חי | מייל `[IBKR-CANDIDATES]` מ-`ibkr-swing-system` |

**דרוש להפעלה מלאה:** GitHub Pages (main/root) + Secrets `GMAIL_USER` + `GMAIL_APP_PASSWORD`.
צד השליחה של IBKR: `ibkr-swing-system/export_candidates.py` — הרץ אחרי כל סריקה.

## הרצה מקומית
```bash
python scripts/fetch_dashboards.py   # מרענן את data/indices.json
python -m http.server 8000           # פתח http://localhost:8000
```

## פריסה
GitHub Pages מוגדר להגיש מענף `main` (שורש). ה-Action עושה commit רק כשיש שינוי בנתונים.

---
התוכן אינו מהווה ייעוץ השקעות.
