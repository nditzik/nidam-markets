#!/usr/bin/env python3
"""
macro_he.py — מתרגם לעברית את שורות נתוני המאקרו שמגיעות בבזק מהרשת (4.11.2026, איציק:
"ההתראה באנגלית ללא הסבר").

FinancialJuice ודומיו מפרסמים נתון בפורמט קבוע:
    "‼ BREAKING: US ISM SERVICES PMI ACTUAL 54.5 (FORECAST 54.8, PREVIOUS 54.9) $MACRO"
parse_macro() מפרק אותו לשם/בפועל/צפי/קודם, ו-translate() נותן שם בעברית, הסבר במשפט
אחד וקריאה ("חזק מהצפי" / "פחות לחץ אינפלציוני"…) — בכללים קבועים, בלי LLM.
נתון שלא במילון: השם המקורי + "בפועל מול צפי" בעברית.

topics_he() — לכותרות שאינן מאקרו (באנגלית): מילות מפתח → נושא בעברית
("הבחירות בארה"ב", "הפד והריבית"…), כדי שההתראה תגיד במה מדובר בלי לתרגם משפטים.

משמש את detect_flash.py (flash.json + טלגרם). בדיקה: python3 scripts/macro_he.py
"""
import re

# ── מדינות (קידומת השם) ─────────────────────────────────────────────
COUNTRY = [
    ("SOUTH AFRICAN", "דרום אפריקה"), ("S. KOREAN", "קוריאה"), ("NEW ZEALAND", "ניו זילנד"),
    ("US", ""), ("EIA", ""), ("API", ""), ("USA", ""),
    ("GERMAN", "גרמניה"), ("GERMANY", "גרמניה"), ("FRENCH", "צרפת"), ("FRANCE", "צרפת"),
    ("ITALIAN", "איטליה"), ("ITALY", "איטליה"), ("SPANISH", "ספרד"), ("SPAIN", "ספרד"),
    ("UK", "בריטניה"), ("BRITISH", "בריטניה"), ("EUROZONE", "גוש היורו"), ("EZ", "גוש היורו"),
    ("EU", "האיחוד האירופי"), ("CHINESE", "סין"), ("CHINA", "סין"), ("JAPANESE", "יפן"),
    ("JAPAN", "יפן"), ("SWISS", "שווייץ"), ("SWEDISH", "שוודיה"), ("NORWEGIAN", "נורווגיה"),
    ("DANISH", "דנמרק"), ("DUTCH", "הולנד"), ("IRISH", "אירלנד"), ("CANADIAN", "קנדה"),
    ("CANADA", "קנדה"), ("AUSTRALIAN", "אוסטרליה"), ("AUSTRALIA", "אוסטרליה"), ("NZ", "ניו זילנד"),
    ("INDIAN", "הודו"), ("INDIA", "הודו"), ("KOREAN", "קוריאה"), ("SOUTH KOREAN", "קוריאה"),
    ("BRAZILIAN", "ברזיל"), ("MEXICAN", "מקסיקו"), ("TURKISH", "טורקיה"), ("ISRAELI", "ישראל"),
    ("RUSSIAN", "רוסיה"), ("POLISH", "פולין"), ("SINGAPORE", "סינגפור"), ("HONG KONG", "הונג קונג"),
]
COUNTRY.sort(key=lambda c: -len(c[0]))

# ── המילון: (תבנית על השם בלי המדינה, שם בעברית, הסבר, סוג) ──────────
# סוג: growth = גבוה מהצפי = כלכלה חזקה · infl = גבוה = יותר לחץ מחירים ·
# lowgood = גבוה = חולשה (אבטלה/תביעות) · stock = מלאי (גבוה = יותר היצע) · neutral
# הסדר חשוב: תבנית ספציפית לפני הכללית (רכיבי ISM לפני ISM עצמו).
PMI_NOTE = "סקר חודשי בין מנהלי רכש; מעל 50 = צמיחה"
DICT = [
    # ISM — שירותים
    (r"ISM (?:SERVICES|NON-?MANUFACTURING) PRICES(?: PAID)?", "רכיב המחירים במדד השירותים (ISM)",
     "כמה החברות משלמות על תשומות — סימן מוקדם לאינפלציה", "infl", "ism_s"),
    (r"ISM (?:SERVICES|NON-?MANUFACTURING) EMPLOYMENT", "רכיב התעסוקה במדד השירותים (ISM)",
     "מעל 50 = החברות מגייסות עובדים", "growth", "ism_s"),
    (r"ISM (?:SERVICES|NON-?MANUFACTURING) NEW ORDERS", "רכיב ההזמנות החדשות במדד השירותים (ISM)",
     "סימן מוקדם לפעילות בחודשים הבאים", "growth", "ism_s"),
    (r"ISM (?:SERVICES|NON-?MANUFACTURING)(?: PMI)?", "מדד מנהלי הרכש בשירותים (ISM)",
     "סקר חודשי בחברות שירותים, כשני שלישים מהכלכלה האמריקאית; מעל 50 = צמיחה", "growth", "ism_s"),
    # ISM — תעשייה
    (r"ISM MANUFACTURING PRICES(?: PAID)?", "רכיב המחירים במדד התעשייה (ISM)",
     "כמה המפעלים משלמים על חומרי גלם — סימן מוקדם לאינפלציה", "infl", "ism_m"),
    (r"ISM MANUFACTURING EMPLOYMENT", "רכיב התעסוקה במדד התעשייה (ISM)",
     "מעל 50 = המפעלים מגייסים עובדים", "growth", "ism_m"),
    (r"ISM MANUFACTURING NEW ORDERS", "רכיב ההזמנות החדשות במדד התעשייה (ISM)",
     "סימן מוקדם לייצור בחודשים הבאים", "growth", "ism_m"),
    (r"ISM MANUFACTURING(?: PMI)?", "מדד מנהלי הרכש בתעשייה (ISM)",
     "סקר חודשי במפעלים; מעל 50 = צמיחה", "growth", "ism_m"),
    # שוק העבודה
    (r"NON-?FARM PAYROLLS|NFP", "תוספת המשרות (NFP)",
     "כמה משרות נוספו במשק בחודש — הנתון החשוב בשוק העבודה", "growth", "nfp"),
    (r"PRIVATE PAYROLLS", "תוספת המשרות במגזר הפרטי", "חלק מדוח התעסוקה החודשי", "growth", "nfp"),
    (r"UNEMPLOYMENT RATE", "שיעור האבטלה", "", "lowgood", "nfp"),
    (r"AVERAGE HOURLY EARNINGS", "השכר הממוצע לשעה",
     "עליית שכר מהירה = לחץ אינפלציוני", "infl", "nfp"),
    (r"INITIAL (?:JOBLESS )?CLAIMS", "תביעות אבטלה חדשות",
     "נתון שבועי — כמה אנשים הגישו לראשונה תביעת אבטלה", "lowgood", "claims"),
    (r"CONTINUING (?:JOBLESS )?CLAIMS", "תביעות אבטלה נמשכות",
     "כמה ממשיכים לקבל דמי אבטלה", "lowgood", "claims"),
    (r"ADP (?:WKLY |WEEKLY )?(?:NATIONAL )?EMPLOYMENT(?: CHANGE)?", "תוספת המשרות במגזר הפרטי (ADP)",
     "הערכה של חברת השכר ADP, לפני דוח התעסוקה הרשמי", "growth", "adp"),
    (r"JOLTS(?: JOB OPENINGS)?", "המשרות הפנויות (JOLTS)",
     "כמה משרות פתוחות במשק — מדד לביקוש לעובדים", "growth", "jolts"),
    (r"CHALLENGER JOB CUTS", "תוכניות פיטורים (Challenger)", "", "lowgood", "chal"),
    # אינפלציה
    (r"CORE CPI|CPI CORE", "מדד המחירים לצרכן — ליבה (CPI)",
     "האינפלציה בלי מזון ואנרגיה — הנתון שהפד מסתכל עליו", "infl", "cpi"),
    (r"CPI|INFLATION RATE", "מדד המחירים לצרכן (CPI)", "קצב האינפלציה", "infl", "cpi"),
    (r"CORE PPI|PPI CORE", "מדד המחירים ליצרן — ליבה (PPI)",
     "מחירי היצרנים — סימן מוקדם למחירים לצרכן", "infl", "ppi"),
    (r"PPI", "מדד המחירים ליצרן (PPI)", "מחירי היצרנים — סימן מוקדם למחירים לצרכן", "infl", "ppi"),
    (r"CORE PCE(?: PRICE INDEX)?", "מדד ה-PCE — ליבה",
     "מדד האינפלציה המועדף על הפד", "infl", "pce"),
    (r"PCE(?: PRICE INDEX)?", "מדד ה-PCE", "מדד אינפלציה של הפד", "infl", "pce"),
    (r"(?:UOM|UNIVERSITY (?:OF )?MICHIGAN|MICHIGAN)[A-Z ]*INFLATION EXPECTATIONS?", "ציפיות האינפלציה של הצרכנים (מישיגן)",
     "כמה אינפלציה הצרכנים מצפים לה", "infl", "uom"),
    (r"(?:UOM|UNIVERSITY (?:OF )?MICHIGAN|MICHIGAN)[A-Z ]*(?:SENTIMENT|CONSUMER)?[A-Z ]*", "סנטימנט הצרכנים (מישיגן)",
     "סקר חודשי על מצב הרוח של הצרכנים", "growth", "uom"),
    # צמיחה וצריכה
    (r"GDP(?: GROWTH)?(?: RATE)?(?: PRICE INDEX)?", "צמיחת התמ\"ג", "קצב הצמיחה של כל הכלכלה", "growth", "gdp"),
    (r"RETAIL SALES CONTROL GROUP", "המכירות הקמעונאיות — קבוצת הבקרה",
     "הצריכה בלי רכב, דלק וחומרי בניין", "growth", "retail"),
    (r"RETAIL SALES[A-Z ]*", "המכירות הקמעונאיות", "כמה הצרכנים קונים בחנויות ובאונליין", "growth", "retail"),
    (r"DURABLE GOODS(?: ORDERS)?[A-Z ]*", "הזמנות מוצרים בני-קיימא",
     "הזמנות של מוצרים יקרים (מכונות, מטוסים) — סימן להשקעות", "growth", "durable"),
    (r"FACTORY ORDERS", "הזמנות המפעלים", "", "growth", "factory"),
    (r"INDUSTRIAL PRODUCTION", "הייצור התעשייתי", "", "growth", "ip"),
    (r"PERSONAL SPENDING", "הוצאות הצרכנים", "", "growth", "pce"),
    (r"PERSONAL INCOME", "הכנסות משקי הבית", "", "growth", "pce"),
    (r"(?:CB |CONFERENCE BOARD )?CONSUMER CONFIDENCE", "אמון הצרכנים", "סקר חודשי על מצב הרוח של הצרכנים", "growth", "cc"),
    (r"BUSINESS CONFIDENCE|IFO BUSINESS CLIMATE|IFO", "אמון העסקים", "", "growth", "bc"),
    (r"ZEW[A-Z ]*", "מדד הציפיות הכלכליות (ZEW)", "", "growth", "zew"),
    (r"(?:NY )?EMPIRE STATE[A-Z ]*", "מדד הייצור של ניו יורק (אמפייר סטייט)",
     "סקר מפעלים חודשי; מעל 0 = התרחבות", "growth", "empire"),
    (r"PHILLY FED[A-Z ]*|PHILADELPHIA FED[A-Z ]*", "מדד הייצור של פילדלפיה",
     "סקר מפעלים חודשי; מעל 0 = התרחבות", "growth", "philly"),
    (r"CHICAGO PMI", "מדד מנהלי הרכש של שיקגו", PMI_NOTE, "growth", "chi"),
    # מדדי מנהלי רכש כלליים (S&P Global, מדינות אחרות)
    (r"(?:S&P GLOBAL )?(?:NBS )?NON-?MANUFACTURING PMI", "מדד מנהלי הרכש מחוץ לתעשייה", PMI_NOTE, "growth", "pmi"),
    (r"(?:S&P GLOBAL |HCOB |CAIXIN |AU JIBUN BANK |NBS )?MANUFACTURING PMI", "מדד מנהלי הרכש בתעשייה", PMI_NOTE, "growth", "pmi"),
    (r"(?:S&P GLOBAL |HCOB |CAIXIN |AU JIBUN BANK )?SERVICES? PMI", "מדד מנהלי הרכש בשירותים", PMI_NOTE, "growth", "pmi"),
    (r"(?:S&P GLOBAL |HCOB |CAIXIN |AU JIBUN BANK )?COMPOSITE PMI", "מדד מנהלי הרכש המשולב", PMI_NOTE, "growth", "pmi"),
    # נדל"ן
    (r"HOUSING STARTS", "התחלות הבנייה", "", "growth", "house"),
    (r"BUILDING PERMITS", "היתרי הבנייה", "", "growth", "house"),
    (r"EXISTING HOME SALES", "מכירות הדירות היד-שנייה", "", "growth", "house"),
    (r"NEW HOME SALES", "מכירות הדירות החדשות", "", "growth", "house"),
    (r"PENDING HOME SALES", "עסקאות דירות בהמתנה", "", "growth", "house"),
    # אנרגיה
    (r"(?:CRUDE (?:OIL )?(?:STOCKS|INVENTORIES)|CRUDE OIL)(?: CHANGE)?", "מלאי הנפט הגולמי (שבועי)",
     "יותר מלאי = יותר היצע, לחץ על מחיר הנפט", "stock", "oil"),
    (r"CRUDE CUSHING(?: INVENTORIES)?|CUSHING[A-Z ]*", "מלאי הנפט בקושינג (שבועי)",
     "מרכז האחסון שקובע את מחיר הנפט האמריקאי", "stock", "oil"),
    (r"GASOLINE (?:STOCKS|INVENTORIES)[A-Z ]*", "מלאי הבנזין (שבועי)", "", "stock", "oil"),
    (r"DISTILLATE[A-Z ]*", "מלאי הסולר (שבועי)", "", "stock", "oil"),
    (r"NATURAL GAS[A-Z ]*", "מלאי הגז הטבעי (שבועי)", "", "stock", "gas"),
    # אנרגיה — API (נתון לא רשמי, יום לפני EIA) ומספר אסדות
    (r"(?:API )?CRUDE (?:OIL )?STOCK(?:S)?(?: CHANGE)?", "מלאי הנפט הגולמי (שבועי)",
     "יותר מלאי = יותר היצע, לחץ על מחיר הנפט", "stock", "oil"),
    (r"(?:API )?CUSHING STOCK(?:S)?(?: CHANGE)?", "מלאי הנפט בקושינג (שבועי)", "", "stock", "oil"),
    (r"(?:API )?GASOLINE STOCK(?:S)?(?: CHANGE)?", "מלאי הבנזין (שבועי)", "", "stock", "oil"),
    (r"(?:API )?DISTILLATE STOCK(?:S)?(?: CHANGE)?", "מלאי הסולר (שבועי)", "", "stock", "oil"),
    (r"BAKER HUGHES (?:OIL )?RIG COUNT", "מספר אסדות הקידוח לנפט (Baker Hughes)",
     "כמה אסדות פעילות — סימן לייצור הנפט העתידי", "neutral", "rigs"),
    (r"BAKER HUGHES TOTAL RIG COUNT", "מספר אסדות הקידוח הכולל (Baker Hughes)", "", "neutral", "rigs"),
    # משכנתאות, סיטונאות, סקרי פד אזוריים
    (r"MBA 30-?YR MORTGAGE RATE", "ריבית המשכנתא ל-30 שנה (MBA)", "", "neutral", "mba"),
    (r"MBA MORTGAGE APPLICATIONS", "בקשות למשכנתא (MBA)", "", "growth", "mba"),
    (r"WHOLESALE INVENTORIES", "המלאים בסיטונאות", "", "neutral", "whole"),
    (r"WHOLESALE SALES", "המכירות בסיטונאות", "", "growth", "whole"),
    (r"CORE DURABLE GOODS(?: ORDERS)?", "הזמנות מוצרים בני-קיימא — ליבה", "בלי כלי תחבורה", "growth", "durable"),
    (r"CHALLENGER LAYOFFS", "תוכניות פיטורים (Challenger)", "", "lowgood", "chal"),
    (r"DALLAS FED[A-Z .]*", "מדד הייצור של דאלאס", "סקר מפעלים חודשי; מעל 0 = התרחבות", "growth", "dallas"),
    (r"KANSAS CITY FED[A-Z .]*", "מדד הייצור של קנזס סיטי", "סקר מפעלים חודשי; מעל 0 = התרחבות", "growth", "kc"),
    (r"RICHMOND FED[A-Z .]*", "מדד הייצור של ריצ'מונד", "סקר מפעלים חודשי; מעל 0 = התרחבות", "growth", "rich"),
    (r"(\d+)-?WEEK BILL HIGH YIELD", "תשואה במכרז אג\"ח קצר ל-{n} שבועות", "", "neutral", "auction"),
    (r"(\d+)-?WEEK BILL BID[- ]TO[- ]COVER", "הביקוש במכרז אג\"ח קצר ל-{n} שבועות (יחס כיסוי)", "", "growth", "auction"),
    # כלליים — בעיקר מדינות אחרות
    (r"CONSTRUCTION PMI", "מדד מנהלי הרכש בבנייה", PMI_NOTE, "growth", "pmi"),
    (r"MORTGAGE APPROVALS", "אישורי משכנתא", "", "growth", "house"),
    (r"IVEY PMI", "מדד מנהלי הרכש (Ivey)", PMI_NOTE, "growth", "pmi"),
    (r"SENTIX[A-Z ]*", "אמון המשקיעים (Sentix)", "", "growth", "bc"),
    (r"BUSINESS CLIMATE[A-Z ]*|MANUFACTURING BUSINESS CONFIDENCE", "אמון העסקים", "", "growth", "bc"),
    (r"CONSUMER CONFIDENCE[A-Z ]*", "אמון הצרכנים", "", "growth", "cc"),
    (r"CONSUMER SPENDING", "הוצאות הצרכנים", "", "growth", "cons"),
    (r"CURRENT ACCOUNT[A-Z ]*", "החשבון השוטף", "יצוא ויבוא של סחורות, שירותים והכנסות", "neutral", "trade"),
    (r"BUDGET BALANCE", "מאזן התקציב", "", "neutral", "budget"),
    (r"IMPORTS? PRICES?", "מחירי היבוא", "", "infl", "ppi"),
    (r"EXPORT PRICES?", "מחירי היצוא", "", "infl", "ppi"),
    (r"EXPORTS", "היצוא", "", "growth", "trade"),
    (r"IMPORTS", "היבוא", "", "neutral", "trade"),
    (r"LABOR COSTS", "עלות העבודה", "", "infl", "wage"),
    (r"CONSTRUCTION SPENDING", "הוצאות הבנייה", "", "growth", "house"),
    (r"CONSTRUCTION OUTPUT", "תפוקת הבנייה", "", "growth", "house"),
    (r"HOUSE STARTS", "התחלות הבנייה", "", "growth", "house"),
    (r"BUILDING CONSENTS", "היתרי הבנייה", "", "growth", "house"),
    (r"CAPACITY UTILIZATION", "ניצולת הייצור", "", "growth", "ip"),
    (r"INDUSTRIAL SALES|MANUFACTURING SALES", "מכירות התעשייה", "", "growth", "ip"),
    (r"(?:CHAIN STORE|LARGE SCALE RETAIL) SALES", "המכירות ברשתות הקמעונאות", "", "growth", "retail"),
    (r"BANK LENDING", "האשראי הבנקאי", "", "growth", "credit"),
    (r"MONETARY BASE", "הבסיס המוניטרי", "", "neutral", "credit"),
    (r"BUSINESS INVENTORIES", "מלאי העסקים", "", "neutral", "whole"),
    (r"GROSS COMPANY PROFITS", "רווחי החברות", "", "growth", "profits"),
    (r"FOREIGN (?:STOCK INVESTMENT|INVESTMENT [A-Z ]*STOCKS)", "השקעות זרות במניות", "", "neutral", "flows"),
    (r"FOREIGN (?:BOND INVESTMENT|INVESTMENT [A-Z ]*BONDS)", "השקעות זרות באג\"ח", "", "neutral", "flows"),
    # אג"ח, ריבית וסחר
    (r"(\d+)[ -]?(?:YR|YEAR)[A-Z \-]*(?:AUCTION )?(?:HIGH )?YIELD", "תשואה במכרז אג\"ח ל-{n} שנים", "", "neutral", "auction"),
    (r"(\d+)[ -]?(?:YR|YEAR)[A-Z \-]*BID[- ]TO[- ]COVER", "הביקוש במכרז אג\"ח ל-{n} שנים (יחס כיסוי)",
     "כמה הצעות הוגשו על כל אג\"ח — גבוה = ביקוש חזק", "growth", "auction"),
    (r"(?:FED |FOMC )?INTEREST RATE DECISION|RATE DECISION", "החלטת הריבית", "", "neutral", "rate"),
    (r"TRADE BALANCE[A-Z ]*|INTERNATIONAL TRADE BALANCE[A-Z ]*", "מאזן הסחר", "יצוא פחות יבוא", "neutral", "trade"),
    (r"LEADING INDICATORS?[A-Z ]*", "המדד המוביל", "", "growth", "lead"),
]
DICT_RE = [(re.compile(r"^(?:" + p + r")$"), he, ex, kind, fam) for p, he, ex, kind, fam in DICT]

# ── מגדירים בסוף השם ────────────────────────────────────────────────
MODS = [
    (r"\bFLASH\b|\bPRELIM(?:INARY)?\b|\bADVANCE\b|\bESTIMATED\b|\bEST\b", "ראשוני"),
    (r"\bFINAL\b", "סופי"),
    (r"\bREVISED\b", "מעודכן"),
    (r"\bYOY\b|\bY/Y\b", "שנתי"),
    (r"\bMOM\b|\bM/M\b", "חודשי"),
    (r"\bQOQ\b|\bQ/Q\b", "רבעוני"),
    (r"\bANNUALIZED\b", "בקצב שנתי"),
]
MODS_RE = [(re.compile(p), he) for p, he in MODS]

MACRO_RE = re.compile(
    r"^\W*(?:BREAKING:\s*)?(?P<name>.+?)\s+ACTUAL\s+(?P<act>[^\s(]+)\s*"
    r"(?:\((?:FORECAST\s+(?P<fc>[^,)]+))?\s*,?\s*(?:PREVIOUS\s+(?P<prev>[^)]+))?\))?", re.I)


def num(s):
    if s is None:
        return None
    t = str(s).strip().upper().replace(",", "")
    if t in ("", "-", "N/A", "NA"):
        return None
    m = re.match(r"^([+\-]?\d+(?:\.\d+)?)\s*([KMBT%]?)", t)
    if not m:
        return None
    v = float(m.group(1))
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(m.group(2), 1)
    return v * mult


def clean(s):
    s = (s or "").strip()
    return None if s in ("", "-") else s


def parse_macro(text):
    """שורת "X ACTUAL a (FORECAST b, PREVIOUS c)" → dict, אחרת None."""
    t = re.sub(r"\$[A-Z]+\b", "", str(text or "")).strip()
    m = MACRO_RE.match(t)
    if not m:
        return None
    name = re.sub(r"^[^A-Z0-9]+", "", m.group("name").upper()).strip()
    return {"name": name, "actual": clean(m.group("act")), "forecast": clean(m.group("fc")),
            "previous": clean(m.group("prev"))}


def split_country(name):
    m = re.match(r"^FOREIGN INVESTMENT (JAPANESE|CHINESE|GERMAN) (BONDS|STOCKS)$", name)
    if m:
        return {"JAPANESE": "יפן", "CHINESE": "סין", "GERMAN": "גרמניה"}[m.group(1)], "FOREIGN INVESTMENT " + m.group(2), m.group(1)
    for en, he in COUNTRY:
        if name == en or name.startswith(en + " "):
            return he, name[len(en):].strip(), en
    return None, name, None


def verdict(kind, act, fc):
    a, f = num(act), num(fc)
    if a is None or f is None:
        return "", 0
    if abs(a - f) < 1e-9:
        return "כצפוי", 0
    up = a > f
    if kind == "growth":
        return ("חזק מהצפי", 1) if up else ("חלש מהצפי", -1)
    if kind == "infl":
        return ("גבוה מהצפי, יותר לחץ מחירים", -1) if up else ("נמוך מהצפי, פחות לחץ אינפלציוני", 1)
    if kind == "lowgood":
        return ("גבוה מהצפי, חולשה בשוק העבודה", -1) if up else ("נמוך מהצפי, שוק עבודה חזק", 1)
    if kind == "stock":
        return ("יותר מהצפי", 0) if up else ("פחות מהצפי", 0)
    return ("מעל הצפי", 0) if up else ("מתחת לצפי", 0)


def translate(text):
    """שורת מאקרו → {he, explain, kind, fam, us, country, actual, forecast, previous, verdict, tone, known}."""
    p = parse_macro(text)
    if not p:
        return None
    country, rest, en = split_country(p["name"])
    mods = []
    base = rest
    for rx, he in MODS_RE:
        if rx.search(base):
            mods.append(he)
            base = rx.sub("", base)
    base = re.sub(r"\bMFG\.?\b", "MANUFACTURING", base)
    base = re.sub(r"\bCOMP\b", "COMPOSITE", base)
    base = re.sub(r"\bHICP\b", "CPI", base)
    base = re.sub(r"\bBAL\.", "BALANCE", base)
    base = re.sub(r"\bLABOUR\b", "LABOR", base)
    base = re.sub(r"\b(?:NSA|SA|ADJUSTED|S\.A\.)\b|,", " ", base)
    base = re.sub(r"\b(FLASH|PRELIM|FINAL)\s+(PMI)\b", r"\2", base)
    base = re.sub(r"^(?:EIA|API)\s+", "", base.strip())
    base = re.sub(r"\s+", " ", base).strip(" -")
    hit = None
    for rx, he, ex, kind, fam in DICT_RE:
        m = rx.match(base)
        if m:
            n = m.group(1) if m.groups() else None
            hit = (he.replace("{n}", n or ""), ex, kind, fam)
            break
    us = en in ("US", "USA", "EIA", "API") or (country is None and en is None)
    if hit:
        he, ex, kind, fam = hit
        name = he
        if mods:
            name += " (" + ", ".join(dict.fromkeys(mods)) + ")"
        if country:
            name += " · " + country
    else:
        kind, fam, ex = "neutral", "other", ""
        name = p["name"].title()
    v, tone = verdict(kind, p["actual"], p["forecast"])
    return {"he": name, "explain": ex, "kind": kind, "fam": fam, "us": bool(us) and bool(hit or en),
            "country": country or "", "actual": p["actual"], "forecast": p["forecast"],
            "previous": p["previous"], "verdict": v, "tone": tone, "known": bool(hit), "src": p["name"]}


def line_he(t, with_explain=True):
    """נתון מתורגם → משפט עברי אחד (לטלגרם ולגיבוי)."""
    s = t["he"] + ": " + str(t["actual"])
    if t.get("forecast"):
        s += " מול צפי " + str(t["forecast"])
    if t.get("verdict"):
        s += " — " + t["verdict"]
    if with_explain and t.get("explain"):
        s += " (" + t["explain"] + ")"
    return s


# ── נושאים לכותרות שאינן מאקרו ──────────────────────────────────────
TOPICS = [
    (r"\bmidterm|\belection|\bcongress|\bsenate\b|\bhouse majorit|\bdemocrat|\brepublican|\bgop\b", "הבחירות בארה\"ב"),
    (r"\bfed\b|\bfomc\b|\bpowell\b|\brate cut|\brate hike|\bcentral bank", "הפד והריבית"),
    (r"\binflation|\bcpi\b|\bppi\b|\bwholesale prices|\bconsumer prices|\bproducer prices", "אינפלציה"),
    (r"\btariff|\btrade war|\btrade deal|\bduties\b", "מכסים וסחר"),
    (r"\biran|\bisrael|\bhormuz|\bmissile|\bwar\b|\bukraine|\brussia|\bgaza|\bhezbollah|\bstrike on", "גיאופוליטיקה"),
    (r"\boil\b|\bopec|\bcrude|\bbrent\b|\bwti\b", "נפט"),
    (r"\btreasur|\byield|\bbond", "אג\"ח ותשואות"),
    (r"\btrump\b|\bwhite house", "הבית הלבן"),
    (r"\bchina\b|\bchinese\b|\bbeijing|\bxi\b", "סין"),
    (r"\bnvidia|\bopenai|\banthropic|\bai\b|\bchip|\bsemiconductor", "AI ושבבים"),
    (r"\bearnings|\bguidance|\bquarterly results|\brevenue\b|\beps\b", "דוחות חברות"),
    (r"\bshutdown|\bdebt ceiling|\bdeficit|\bspending bill", "תקציב הממשל"),
    (r"\bdollar\b|\byen\b|\beuro\b|\bdxy\b", "מטבעות"),
    (r"\bbitcoin|\bcrypto", "קריפטו"),
]
TOPICS_RE = [(re.compile(p, re.I), he) for p, he in TOPICS]
HEB = re.compile(r"[֐-׿]")


def is_hebrew(text):
    return bool(HEB.search(str(text or "")))


def topics_he(texts, limit=3):
    out = []
    for t in texts:
        for rx, he in TOPICS_RE:
            if rx.search(str(t or "")) and he not in out:
                out.append(he)
    return out[:limit]


if __name__ == "__main__":
    for s in [
        "‼ BREAKING: US ISM SERVICES PMI ACTUAL 54.5 (FORECAST 54.8, PREVIOUS 54.9) $MACRO",
        "US ISM SERVICES EMPLOYMENT ACTUAL 51.4 (FORECAST 50, PREVIOUS 50.1) $MACRO",
        "US ISM SERVICES PRICES PAID ACTUAL 73 (FORECAST 74.6, PREVIOUS 74.0) $MACRO",
        "GERMAN 15 YR BUND YIELD ACTUAL 3.57% (FORECAST -, PREVIOUS 3.5%) $MACRO",
        "GERMAN 15 YR BID-TO-COVER ACTUAL 1.3 (FORECAST -, PREVIOUS 2) $MACRO",
        "❗ GERMAN SERVICE PMI FLASH ACTUAL 51.2 (FORECAST 50.9, PREVIOUS 51.5) $MACRO",
        "EIA NATURAL GAS CHANGE BCF ACTUAL 77B (FORECAST 78B, PREVIOUS 67B) $MACRO",
        "US INITIAL JOBLESS CLAIMS ACTUAL 231K (FORECAST 225K, PREVIOUS 219K) $MACRO",
        "US ADP WKLY EMPLOYMENT CHANGE ACTUAL 14.5K (FORECAST -, PREVIOUS 11K) $MACRO",
        "SPANISH ESTIMATED GDP QOQ ACTUAL 0.6% (FORECAST 0.5%, PREVIOUS 0.7%) $MACRO",
        "JAPANESE FOREIGN STOCK INVESTMENT ACTUAL ¥-1.2T (FORECAST -, PREVIOUS ¥0.4T) $MACRO",
    ]:
        t = translate(s)
        print(("✓ " if t["known"] else "? ") + line_he(t))
    print(topics_he(["BREAKING: US markets post massive gains across the board in their initial reaction to the US Midterm Election results",
                     "10-year Treasury yield slips after Democrats win House and Senate majorities"]))
