# שוק ההון של איציק נידם

אתר סטטי (GitHub Pages) המרכז את הדשבורדים והתדריכים בטאבים, עם עדכון אוטומטי פעמיים ביום.

## מבנה
- `index.html` — דף בית (סקירת שוק) + טאבים
- `assets/style.css`, `assets/app.js` — עיצוב ולוגיקה (ונילה, ללא פריימוורק)
- `data/*.json` — כל הנתונים; ה-HTML רק מרנדר
- `scripts/fetch_dashboards.py` — מושך מדדים מ-indexes-status → `data/indices.json`
- `.github/workflows/update.yml` — Action פעמיים ביום + הרצה ידנית

## סטטוס טאבים (שלב 1)
| טאב | מצב |
|---|---|
| בית / מדדים | ✅ חי (מ-`indexes-status`) |
| מומנטום | ⏳ ממתין למקור |
| מועמדים (IBKR) | ⏳ שלב ד' |
| סקירת בוקר / תדרוך משקיעים | ⏳ שלב ג' (ג'ימייל) |

## הרצה מקומית
```bash
python scripts/fetch_dashboards.py   # מרענן את data/indices.json
python -m http.server 8000           # פתח http://localhost:8000
```

## פריסה
GitHub Pages מוגדר להגיש מענף `main` (שורש). ה-Action עושה commit רק כשיש שינוי בנתונים.

---
התוכן אינו מהווה ייעוץ השקעות.
