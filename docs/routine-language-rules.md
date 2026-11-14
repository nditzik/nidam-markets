# כללי הניסוח ברוטינות — מה להדביק (14.11.2026)

מ-14.11.2026 האתר מנוסח כמערכת מידע, מחקר ולימוד: נתון · פרשנות של המודל · מגבלות · תנאים למעקב.
הכללים המלאים: `scripts/prompts/_language.md`.

## רוטינות שכבר מעודכנות (קוראות את גוף ההוראות מהריפו — אין מה להדביק)

- `nidam-daily-market-analysis` + `-retry` → `scripts/prompts/daily_analysis.md` (וכל תתי-הפרומפטים: לקראת הדוח, אחרי הדוח, ארבעת העמודים, משפטי החברות)
- `nidam-event-update-1545` → `scripts/prompts/event_update_1550.md`
- `nidam-weekly-narrative` → `scripts/prompts/weekly_narrative.md`
- `nidam-rotation-weekly` → `scripts/prompts/rotation_weekly.md`
- `nidam-preview-sun-mon` → `scripts/prompts/week_forecast.md` (החלק של הצפי)

## רוטינות שהפרומפט שלהן יושב בממשק — להדביק שורה אחת בראש הפרומפט

`nidam-event-update-1700` · `nidam-midday-1900` · `nidam-preopen-1535` · `nidam-preview-sun-mon`

בכל אחת: לפתוח את הרוטינה ב-claude.ai/code/routines → Edit → להדביק את הפסקה הבאה **כשורה הראשונה** של הפרומפט (בלי לגעת בשאר, ובלי לגעת בפקודת הדחיפה) → Save.

```
כלל ניסוח מחייב (גובר על כל הוראה אחרת בפרומפט הזה): לפני הכתיבה קרא את scripts/prompts/_language.md ופעל לפיו. האתר מתאר נתונים, פרשנות ותנאים למעקב. אין לכתוב הוראות פעולה (לקנות / למכור / להחזיק / להוסיף / להדק סטופים / להמתין), גודל פוזיציה, או כניסה / סטופ / יעד. השדה action אינו "שורת פעולה": כתוב בו למה לשים לב עכשיו — רמה, נתון או אירוע למעקב.
```

## איך יודעים שזה עובד

`scripts/lint_advice.py` רץ בכל עדכון של האתר ומסמן ניסוחים חשודים. בתחתית האתר, במחוון "מצב מקורות", הצ'יפ **"בדיקת ניסוח"** ירוק כשאין ממצאים וצהוב כשיש (ריחוף מציג מה נמצא). הפירוט: `data/advice_lint.json`.
