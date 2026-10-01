"""gh_api.py — כותרות לבקשות ל-GitHub (1.10.2026).

בלי טוקן ה-API של GitHub מוגבל ל-60 קריאות בשעה לכתובת IP — וה-runners של Actions חולקים כתובות,
כך שבבוקר שבו ריצות נערמו כל רשימות הקבצים נכשלו ב-403. ב-Action מוגדר GITHUB_TOKEN (הטוקן
המובנה, ראו update.yml); הוא נשלח רק ל-api.github.com, לא ל-raw או לשירותים אחרים.
"""
import os

UA = "nidam-markets-bot"


def gh_headers(url):
    h = {"User-Agent": UA}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and url.startswith("https://api.github.com/"):
        h["Authorization"] = "Bearer " + tok
    return h
