# Writes components/<Comp>/preview.html + README.md, the cover and the index for the Daily Edge style book.
import os, json, datetime
D = os.path.dirname(os.path.abspath(__file__)) + '/project'
sn = open(os.path.dirname(os.path.abspath(__file__)) + '/snips.txt', encoding='utf-8').read().split('\n')
SPARK, MSP, RNG, DOTS = sn[0], sn[1], sn[2], sn[3]

def doc(group, height, body, subtitle='', width=None):
    w = f' width={width}' if width else ''
    sub = f' subtitle="{subtitle}"' if subtitle else ''
    return f'''<!-- @dsCard group="{group}" height={height}{w}{sub} -->
<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="../bundle.css"></head>
<body><div class="de" style="padding:12px">{body}</div></body></html>'''

C = {}

C['Panel'] = ('לוח', 150, '''<section class="pan" style="width:520px"><div class="ph"><h2>התדרוך · <span class="n">06:01</span></h2><a href="#" class="go">התדרוך המלא</a></div>
<div><div class="li"><span class="n">1</span><span>המימוש ב-AI החריף: מדד השבבים איבד 3.4%, בעוד רוב מניות S&amp;P 500 עלו.</span></div>
<div class="li"><span class="n">2</span><span>וולר מהפד אותת שהריבית עשויה לעלות שוב השנה — לא בהכרח בישיבות רצופות.</span></div></div></section>''',
'''# Panel
המכולה היחידה של הלוח: רקע `surface-panel`, קו-שיער `line-hair`, `radius-md`, בלי צל.
- **כותרת** (`.ph`): `h2` ב-`panel-title` (13px/600, `ink-2`) בקצה הימני; טקסט-משנה ב-`ink-muted` לידה (תאריך, "שעון ישראל"); **קישור אחד** (`.go`) בקצה השמאלי — ראו PanelLink. גובה 44px.
- **גוף**: או `.pb` (ריפוד `space-4`, `gap: space-3`) או רשימה של שורות מופרדות בקו-שיער (`.li`, `.crl`, `.wr`) בלי ריפוד חיצוני.
- מה הצרכן מספק: כותרת (מה + מתי), 3–6 שורות תוכן, יעד הקישור.
- ✅ פאנל אחד = שאלה אחת. ❌ פאנל בתוך פאנל; כותרת גדולה מ-13px; צל.''')

C['PanelLink'] = ('לוח', 100, '''<div style="display:flex;flex-direction:column;gap:8px;width:420px">
<section class="pan"><div class="ph"><h2>מצב השוק · סגירת חמישי <span class="n">8.10</span></h2><a href="#" class="go">הניתוח המלא</a></div></section>
<section class="pan"><div class="ph"><h2>הנבחרות · מהדורת <span class="n">8.10</span></h2><span class="pill state">השוק זהיר · עד <span class="n">4</span></span><a href="#" class="go">כל <span class="n">13</span> הנבחרות והיומן</a></div></section></div>''',
'''# PanelLink
תבנית אחת לכל "עוד": **שם היעד בלבד**, `link-text`, 13px/500, בלי חץ ובלי "←" (החץ היה בשש גרסאות שונות בגרסה הקודמת).
הנוסחים: "הניתוח המלא" · "היומן המלא" · "כל 13 הנבחרות והיומן" · "התדרוך המלא" · "כל הבזקים" · "השוק" · "העולם" · "כל ההימורים". בטלפון מותר לקצר ("הניתוח", "המלא", "הכל").
`padding: 12px 0` כדי שהמטרה תהיה 44px בלי לשבור את יישור הכותרת. ריחוף = קו תחתון.''')

C['Tabs'] = ('ניווט', 130, '''<div style="width:900px"><header class="top"><div class="logo"><i></i>The Daily Edge</div>
<nav class="tabs" aria-label="ניווט ראשי"><a href="#" aria-current="page">בית</a><a href="#">השוק</a><a href="#">היומן</a><a href="#">מניות</a><a href="#">חדשות</a><a href="#">העולם</a></nav></header>
<nav class="subtabs" aria-label="לשוניות"><a href="#" aria-current="page">הנבחרות</a><a href="#">מועמדים</a><a href="#">מומנטום</a><a href="#">הצעות לטרייד</a><a href="#">Insider</a></nav></div>''',
'''# Tabs
**שישה טאבים עליונים**: בית · השוק · היומן · מניות · חדשות · העולם. בכותרת האתר (56px), `ink-2` 500; פעיל = `link-text` 600 + קו תחתון 2px `link-text` + `aria-current="page"`. ריחוף = `ink-1`. בטלפון: רצועה נגללת 48px, מתחילה מימין ("בית").
**לשוניות-משנה** (`.subtabs`): פילים 36px עם מתאר `line-hair`; פעיל = `link-bg`+`link-text`. יושבות מעל הפאנל בתוך הטאב.
הלשונית היא יחידת המדידה: ה-hash וה-GoatCounter נשארים בשמות הקיימים (`home`, `indices`, `sectors`, `momentum`, `candidates`, `trades`, `picks`, `insider`, `briefing`, `morning`, `weekcal`, `prep`, `reports`, `world`); לטאב עליון חדש מדידה בשם חדש.
❌ ענבר לטאב פעיל (ענבר = מצב); אייקונים בטאבים; יותר מרמה אחת של לשוניות.''')

C['Number'] = ('מספרים', 90, '''<div style="display:flex;gap:24px;align-items:baseline;font-size:15px">
<span class="n up">+1.44%</span><span class="n dn">−0.47%</span><span class="n flat">0.00%</span><span class="n">7,765.36</span><span class="n">182.75</span><span class="n mute">19:15</span>
<span>הירידה של <span class="n dn">−0.47%</span> היא השנייה ברצף</span></div>''',
'''# Number
כל מספר באתר עטוף ב-`.n`: `font-mono`, `direction:ltr`, `unicode-bidi:isolate`, `tabular-nums`. כך הסימן נשאר במקומו בתוך משפט עברי.
- `.up` / `.dn` / `.flat` לפי הסימן — **תמיד יחד עם הסימן** (+ / − U+2212). צבע בלי סימן אסור.
- מחיר: שתי ספרות ומפריד אלפים (`7,765.36`). אחוז: שתי ספרות. ציון המד: שלם. שעה: `15:30`. תאריך: `8.10` (בלי שנה, בלי אפס מוביל).
- `ink-muted` לשעות ולמספור; `ink-1` למחיר; בלי צבע לערך שאינו שינוי (VIX 15.41 הוא `ink-1`, השינוי שלו −3.18% הוא `.dn`).''')

C['KPI'] = ('מספרים', 120, '''<div class="kpis" style="width:760px">
<div><div class="l">S&amp;P 500</div><div class="v dn">−0.47%</div><div class="s"><span class="n">7,765.36</span></div></div>
<div><div class="l">שוויוני (המניה הממוצעת)</div><div class="v up">+0.60%</div><div class="s">מול S&amp;P ב-20 יום: <span class="n dn">−2.53%</span></div></div>
<div><div class="l">עלו / ירדו</div><div class="v">345/156</div><div class="ad" role="img" aria-label="69% עלו"><i style="width:69%;background:var(--signal-up)"></i><i style="width:31%;background:var(--signal-down)"></i></div></div>
<div><div class="l">VIX</div><div class="v">15.41</div><div class="s"><span class="lamp"></span>רמזור ירוק · מתחת לממוצע 50</div></div></div>''',
'''# KPI
אריח ערך-גדול: תווית `caption` ב-`ink-muted` **מעל**, ערך `kpi` (24px מונו, 17px בטלפון), שורת משנה `caption` ב-`ink-2`. ארבעה בשורה (שלושה בטלפון) בתוך מסגרת אחת, מופרדים בקו-שיער — בלי רקע נפרד לכל אריח.
- הערך נצבע רק אם הוא שינוי (±). רמה (VIX, מחיר) נשארת `ink-1`.
- פס עלו/ירדו (`.ad`): LTR, ירוק משמאל, `gap:2px`, `role="img"` עם האחוז.
- מה הצרכן מספק: 3–4 זוגות תווית/ערך מאותו יום מסחר. ❌ לערבב סגירה עם ציטוט חי באותה שורה (הסתירה שנמצאה ב-4א).''')

C['Meter'] = ('מספרים', 300, f'''<section class="pan" style="width:380px"><div class="ph"><h2>The Edge Meter</h2><span class="mute" style="font-weight:400">סגירת חמישי · <span class="n">8.10.26</span></span></div>
<div class="pb">
<div class="score"><span class="big">60</span><span class="st" style="font-size:20px;font-weight:700">זהיר</span><span class="mute" style="margin-inline-start:auto;font-size:13px">אתמול: <span class="n">55</span></span></div>
<div class="seg" role="img" aria-label="ציון 60 מתוך 100, אזור זהיר"><i style="background:var(--signal-down)"></i><i style="background:var(--state-fill)"></i><i style="background:var(--signal-up)"></i><b style="left:calc(60% - 1px)"></b></div>
<div class="segl"><span>הגנתי · עד 44</span><span>זהיר · 45–65</span><span>חיובי · מ-66</span></div>
<div class="cm"><span class="mute">טכני</span><div class="bar"><i style="width:90%"></i></div><span class="n">90</span></div>
<div class="cm"><span class="mute">רוחב</span><div class="bar"><i style="width:32%"></i></div><span class="n">32</span></div>
<div class="cm"><span class="mute">אופציות</span><div class="bar"><i style="width:97%"></i></div><span class="n">97</span></div>
{MSP}
<div class="kv"><span>ימי מכירה רחבה</span><span><span class="n">4</span> מתוך <span class="n">25</span> ימים · הסף <span class="n">4</span></span></div>
</div></section>''',
'''# Meter
הפאנל של "מה מצב השוק". מלמעלה למטה: ציון (`score`, 56px מונו) + המילה בצבע המצב + "אתמול: N"; פס שלושה מצבים (LTR: `signal-down` | `state-fill` | `signal-up`, 45/21/34, סמן 2px `ink-1`); מקרא 12px; שלושת הרכיבים כפסים על `graphic-track` במילוי `ink-2`; ספארקליין 30 יום על `surface-panel-2` (אזורי חיובי/הגנתי ב-10% שקיפות, קו `ink-2`, נקודה אחרונה `state-fill`); שורת ימי מכירה.
- המילה והספים זהים ל-`meterWord` באתר: עד 44 הגנתי (`signal-down`), 45–65 זהיר (`state-text`), מ-66 חיובי (`signal-up`).
- בטלפון: ציון 44px + שלושת הפסים בשורה אחת; הפס, המקרא והספארקליין יורדים.
- `role="img"` + `aria-label` על הפס ועל הספארקליין. ❌ ציר-Y כפול; צבע לפסי הרכיבים.''')

C['Table'] = ('נתונים', 230, f'''<section class="pan" style="width:1100px"><table><caption style="position:absolute;clip:rect(0 0 0 0)">הנבחרות</caption>
<thead><tr><th scope="col">מניה</th><th scope="col">מחיר</th><th scope="col">יום</th><th scope="col">60 יום</th><th scope="col">סטופ / תמיכה</th><th scope="col">מיקום בטווח</th><th scope="col">יעד / התנגדות</th><th scope="col">מקור</th><th scope="col">רקורד</th></tr></thead>
<tbody><tr><td><a href="#" class="tsym"><span class="rank">1</span>BDX</a><div class="mute" style="font-size:12px">Becton Dickinson</div></td>
<td><span class="n">182.75</span></td><td><span class="n up">+1.44%</span></td><td>{SPARK}</td>
<td><span class="n dn">176.59</span><div class="mute" style="font-size:12px">סטופ</div></td><td>{RNG}</td>
<td><span class="n up">191.99</span><div class="mute" style="font-size:12px">יעד</div></td>
<td><span class="tag" style="margin-inline-end:4px">מועמד</span><span class="tag">מומנטום</span></td>
<td>{DOTS}<div class="mute" style="font-size:12px"><span class="n">2</span> מתוך <span class="n">5</span> עלו</div></td></tr></tbody></table>
<div class="led"><div><span class="mute">מהדורת <span class="n">29.9</span> · 5 ימים</span><span><span class="n up">+1.31%</span> <span class="mute">מול S&amp;P</span></span></div><div><span class="mute">מהדורת <span class="n">30.9</span> · 5 ימים</span><span><span class="n up">+0.18%</span> <span class="mute">מול S&amp;P</span></span></div><div><span class="mute">מהדורת <span class="n">1.10</span> · 5 ימים</span><span><span class="n up">+1.03%</span> <span class="mute">מול S&amp;P</span></span></div><div><span class="mute">מהדורת <span class="n">7.10</span> · יום <span class="n">1</span></span><span><span class="n up">+2.04%</span> <span class="mute">מול S&amp;P</span></span></div></div></section>''',
'''# Table
טבלת נתונים (הנבחרות בבית, לוח הדיווחים, היומן): כותרות `caption` 12px/500 ב-`ink-muted` מיושרות ימינה; תאים 14px, `padding: 8px 10px`, `white-space: nowrap`; קו-שיער בין שורות, בלי זברה ובלי מסגרת לתא.
- עמודת המניה: טיקר (`ticker`, קישור לניתוח הטכני) עם הדירוג (`.rank`) לפניו, ושם החברה 12px מתחת. אין עמודת "#".
- ערך+תווית בתא אחד: המספר למעלה, "סטופ"/"יעד" 12px מתחת.
- רצועת סיכום (`.led`) מתחת לטבלה: תא לכל מהדורה, "מהדורת 29.9 · 5 ימים: +1.31% מול S&P".
- `caption` מוסתר ו-`scope="col"`; הספארקליין ומיקום-בטווח עם `aria-label`.
- רספונסיבי: <1100px יורדות "60 יום" ו"מיקום בטווח"; <700px הטבלה הופכת ל-StockRow.''')

C['StockRow'] = ('נתונים', 150, f'''<section class="pan" style="width:366px">
<a href="#" class="crow"><div><span class="tsym">BDX</span><div><span class="n up">+1.44%</span></div></div>{SPARK}<div class="lv2"><span><small>סטופ</small><span class="n dn">176.59</span></span><span><small>יעד</small><span class="n up">191.99</span></span></div></a>
<a href="#" class="crow"><div><span class="tsym">STGW</span><div><span class="n up">+1.27%</span></div></div>{SPARK}<div class="lv2"><span><small>סטופ</small><span class="n dn">8.35</span></span><span><small>יעד</small><span class="n up">9.38</span></span></div></a>
</section>''',
'''# StockRow
שורת מניה בטלפון (וגם בטבלה מתחת ל-700px): שלוש עמודות — טיקר + שינוי יומי | ספארקליין 60 יום ברוחב מלא | סטופ ויעד **עם תווית** 12px מעל כל מספר. כל השורה היא `<a>` אחד (56px) שפותח את הניתוח הטכני; אין קישור נפרד בתוכה.
מה הצרכן מספק: sym, chg, 60 סגירות, lo/hi + התוויות שלהם (סטופ/תמיכה, יעד/התנגדות).
❌ מספרים אדום/ירוק בלי תווית (הממצא מ-4א); שלוש שורות טקסט בעמודה השמאלית.''')

C['Tag'] = ('תגים', 90, '''<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
<span class="tag">מועמד</span><span class="tag">מומנטום</span><span class="tag macro">מאקרו</span><span class="tag earn">דוחות</span><span class="tag earn">לפני הפתיחה</span>
<span style="width:1px;height:24px;background:var(--line-hair)"></span>
<span class="pill">טרום מסחר</span><span class="pill">לפני פתיחה</span><span class="pill state">השוק זהיר · עד <span class="n">4</span> פוזיציות · שני שליש גודל</span></div>''',
'''# Tag
**תג** (`.tag`, 12px, `radius-xs`): ברירת מחדל = מתאר `line-hair` על `surface-panel`, `ink-2` — מקור המניה ("מועמד", "מומנטום"), טיקר ברשימה. `.macro` = `state-bg`+`state-text` 600 לאירוע מאקרו (CPI, PPI, פד). `.earn` = `link-bg`+`link-text` 600 לדיווחים ("דוחות", "לפני הפתיחה", "היום" ביומן הטלפון).
**פיל** (`.pill`, 12px/600): **סשן** ("טרום מסחר", "לפני פתיחה", "השוק פתוח") = מתאר נייטרלי; **שער הנבחרות** ("השוק זהיר · עד 4 פוזיציות") = `.state` בצבע המצב — ביום חיובי רקע ירוק-בהיר/טקסט `signal-up`, ביום הגנתי אדום.
שני סוגי פיל בשני סגנונות בכוונה: זמן ≠ מצב. ❌ תג עם אייקון; יותר משלושה תגים בשורה.''')

C['Calendar'] = ('לוח', 420, '''<div style="display:flex;flex-direction:column;gap:12px;width:1100px">
<section class="pan"><div class="ph"><h2>היומן</h2><span class="mute" style="font-weight:400">שעון ישראל</span><a href="#" class="go">היומן המלא</a></div>
<div class="cal">
<div><span class="d"><b>היום · שישי <span class="n">9.10</span></b></span><span class="e"><span class="tag earn">דוחות</span> <b class="ltr">DAL</b> לפני הפתיחה · <b class="ltr">PGR</b></span><span class="mute" style="font-size:13px">אין נתוני מאקרו מתוזמנים</span></div>
<div><span class="d">שני <span class="n">13.10</span> · לפני הפתיחה</span><span class="e"><span class="tag earn">עונת הדוחות נפתחת</span> הבנקים</span><span class="mute ltr" style="font-size:13px;text-align:right">JPM · WFC · C · GS · UNH · JNJ</span></div>
<div><span class="d">שלישי <span class="n">14.10</span> · <span class="n">15:30</span></span><span class="e"><span class="tag macro">מאקרו</span> CPI ליבה חודשי</span><span class="mute" style="font-size:13px">צפי <span class="n">0.2%</span> · קודם <span class="n">0.3%</span></span></div>
<div><span class="d">רביעי <span class="n">15.10</span> · <span class="n">15:30</span></span><span class="e"><span class="tag macro">מאקרו</span> PPI חודשי</span><span class="mute" style="font-size:13px">צפי <span class="n">0.3%</span> · קודם <span class="n">0.2%</span></span></div>
</div></section>
<section class="pan" style="border-color:var(--state-fill)"><div class="ph"><h2>היום · שני <span class="n">13.10</span> · יום אירוע</h2><span class="tag earn">עונת הדוחות נפתחת</span><span class="tag macro">מחר <span class="n">15:30</span> CPI</span><a href="#" class="go">היומן המלא</a></div>
<div class="ev"><div><h3><span class="tag earn">לפני הפתיחה</span>הבנקים פותחים את העונה</h3>
<div style="display:flex;gap:6px;flex-wrap:wrap"><span class="tag">JPM</span><span class="tag">WFC</span><span class="tag">C</span><span class="tag">GS</span><span class="tag">UNH</span><span class="tag">JNJ</span></div>
<div class="prep"><div class="h"><b class="ltr" style="font-family:var(--font-mono);font-size:15px;color:var(--ink-1)">JPM</b><span>לקראת הדוח · צפי רווח <span class="n">$5.93</span> למניה · האופציות מתמחרות <span class="n">±3.5%</span></span></div><p>הרבעון הקודם היה שיא. הפעם בודקים כמה מהעוצמה נשארת כשהמסחר וההנפקות חוזרים לקצב רגיל.</p><a href="#" style="font-size:13px">ההכנה המלאה ל-JPM</a></div></div>
<div><h3><span class="tag macro">מחר · <span class="n">15:30</span></span>אינפלציה — ספטמבר</h3>
<div><div class="mrow" style="color:var(--ink-muted);font-size:12px"><span>נתון</span><span class="n">צפי</span><span class="n">קודם</span></div><div class="mrow"><span>CPI ליבה חודשי</span><span class="n">0.2%</span><span class="n">0.3%</span></div><div class="mrow"><span>CPI שנתי</span><span class="n">3.6%</span><span class="n">3.4%</span></div></div>
<div style="font-size:13px;color:var(--ink-2);border-top:1px solid var(--line-hair);padding-top:8px">השווקים מהמרים (קאלשי): <span class="n">88%</span> שהאינפלציה השנתית תישאר מעל <span class="n">3.5%</span>.</div></div></div></section></div>''',
'''# Calendar
בלוק היומן בבית, בשני מצבים.
**רגיל** (`.cal`): ארבעה תאים — היום + שלושת המועדים הבאים. בכל תא: שורת תאריך 12px (`ink-muted`; "היום" ב-`ink-1` 600), הפריט 15px/500 עם **תג סוג לפניו** (`.macro` ענבר / `.earn` כחול), ושורת משנה 13px (צפי/קודם, רשימת טיקרים). ההדגשה לפי סוג האירוע, לא לפי היום — CPI בשלישי בולט גם כשהיום שישי.
**יום אירוע** (`.ev`, מופעל כשיש מאקרו מתוזמן או דיווח של חברה עם ניתוח באתר): הפאנל עולה לשורה הראשונה במקום "מצב השוק", מסגרת `state-fill`, כותרת "היום · … · יום אירוע" עם תגי האירועים; שתי עמודות — דוחות (רשימת טיקרים כתגים + כרטיס `.prep` "לקראת הדוח" על `surface-panel-2`: תזה, צפי, תמחור האופציות, קישור) | מאקרו (טבלת נתון/צפי/קודם ב-`.mrow`, שורת ההימור, "אחר כך השבוע").
בטלפון: רשימת שורות `.crl` (48px) עם התג בתחילת השורה.
❌ להדגיש את "היום" כשאין בו אירוע; לצבוע תאריכים; יותר מארבעה תאים.''')

C['Quotes'] = ('נתונים', 90, '''<div class="quotes" style="width:1100px;border:1px solid var(--line-hair)">
<div><span class="l">חוזה S&amp;P</span><span class="v"><span class="n">7,850</span><span class="n up">+0.44%</span></span></div>
<div><span class="l">חוזה נאסד"ק</span><span class="v"><span class="n">31,088</span><span class="n up">+0.38%</span></span></div>
<div><span class="l">ראסל (IWM)</span><span class="v"><span class="n">278.66</span><span class="n up">+0.39%</span></span></div>
<div><span class="l">VIX</span><span class="v"><span class="n">14.92</span><span class="n dn">−3.18%</span></span></div>
<div><span class="l">אג"ח 10Y</span><span class="v"><span class="n">5.26%</span><span class="n up">+0.50%</span></span></div>
<div><span class="l">דולר/שקל</span><span class="v"><span class="n">3.063</span><span class="n up">+0.10%</span></span></div>
<div><span class="l">DXY</span><span class="v"><span class="n">102.3</span><span class="n up">+0.17%</span></span></div>
<div><span class="l">ביטקוין</span><span class="v"><span class="n">121,900</span><span class="n up">+1.52%</span></span></div></div>''',
'''# Quotes
רצועת הציטוטים מתחת לכותרת האתר: שמונה תאים שווים (שלושה בטלפון), מופרדים בקו-שיער, על `surface-panel`. בכל תא: תווית 12px `ink-muted` מעל, ואז מחיר (`quote` מונו, `ink-1`) + אחוז (צבע האות) באותה שורה.
לפני הפתיחה: חוזים; אחרי הפתיחה: SPY→"S&P 500" וכו' (אותם תאים, שמות אחרים). מתעדכן כל דקה; מחיר ואחוז בלבד — בלי ספארקליין ברצועה.
מה הצרכן מספק: [תווית, מחיר מעוצב, שינוי]. תא בלי מחיר שובר את התבנית — תמיד שניהם.''')

C['Sparkline'] = ('נתונים', 90, f'''<div style="display:flex;gap:32px;align-items:center"><div>{SPARK}<div class="mute" style="font-size:12px">60 יום · קו סטופ אדום, קו יעד ירוק</div></div><div style="width:300px">{MSP}<div class="mute" style="font-size:12px">המד · 30 יום · אזורים + נקודה אחרונה</div></div><div>{RNG}<div class="mute" style="font-size:12px">מיקום בטווח · LTR</div></div></div>''',
'''# Sparkline
שלוש הגרפיקות הקטנות של הלוח, כולן **LTR** (ישן→חדש, נמוך→גבוה משמאל לימין) בלי טקסט בתוך ה-SVG.
- **60 יום** (`.sp`, 130×30): קו `ink-1` 1.3px, מילוי `ink-2` ב-7%, קווים מקווקווים `signal-down` (סטופ/תמיכה) ו-`signal-up` (יעד/התנגדות) באותו קנה מידה. `preserveAspectRatio="none"`.
- **המד 30 יום** (`.msp`): רקע `surface-panel-2`, רצועות חיובי/הגנתי ב-10% שקיפות, קו `ink-2` 1.6px, נקודה אחרונה `state-fill`.
- **מיקום בטווח** (`.rng`, 110×6): מסלול `graphic-track`, סמן 3×12 `ink-1`, `left:` לפי אחוז.
כל אחת `role="img"` + `aria-label` עם המספרים (טיקר, סטופ, יעד). ❌ צבע הקו לפי הכיוון (זה כבר באחוז); ציר-Y כפול; תווית עברית ב-`<text>`.''')

for name, (group, h, body, readme) in C.items():
    os.makedirs(f'{D}/components/{name}', exist_ok=True)
    open(f'{D}/components/{name}/preview.html', 'w', encoding='utf-8').write(doc(group, h, body))
    open(f'{D}/components/{name}/README.md', 'w', encoding='utf-8').write(readme + '\n')

# ---- Cover ----
# blocks: brand-mark/state-fill (amber, identity) 232×144 · ink-1 slab 120×288 · signal-up 112×64 · signal-down 112×64 · link-bg tint 232×80
# arrangement: a flush modular grid right of x=480 — panels on a 12-col board, hairlines between
# pattern: "precise, technical, mono, a grid" → a plus grid at space-6 (24px) in line-hair over the tint block; the board's own grid
# scales: sides are multiples of space-2/space-6; corners radius-md (6) on blocks, radius-xs on the small ones
cover = '''<!-- @dsCard height=300 -->
<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>
body{margin:0;background:var(--surface-page);font-family:var(--font-sans)}
.cv{position:relative;width:960px;height:300px;overflow:hidden}
.name{position:absolute;left:40px;bottom:52px;width:440px;font-size:72px;line-height:.95;font-weight:700;color:var(--ink-1);margin:0;letter-spacing:-.01em}
.tag{position:absolute;left:40px;bottom:24px;width:440px;font-size:13px;color:var(--ink-muted);margin:0}
.brand{fill:var(--state-fill)}.ink{fill:var(--ink-1)}.up{fill:var(--signal-up)}.dn{fill:var(--signal-down)}.tint{fill:var(--link-bg)}.pan{fill:var(--surface-panel)}
.hair{stroke:var(--line-hair);stroke-width:1;fill:none}.plus{stroke:var(--link-text);stroke-width:1.5;opacity:.55}
.r6{rx:6}.r3{rx:3}
</style></head><body><div class="cv">
<svg width="960" height="300" viewBox="0 0 960 300" aria-hidden="true">
<!-- derivation:
 blocks: state-fill 232x144 (identity amber) · ink-1 120x288 slab · signal-up 112x64 · signal-down 112x64 · link-bg 232x80 · surface-panel 232x64
 arrangement: a flush modular grid from x=480, 8px gutters (space-2), like the 12-column board; the ink slab bleeds off the right edge
 pattern: "precise, technical, mono, a grid" row → a plus grid at space-6 (24px) pitch in link-text over the tint block; chosen because the product IS a grid of panels and numbers
 scales: sides = space-2 multiples; corners radius-md (6px) on blocks, radius-xs (3px) on the two signal blocks -->
<rect class="brand r6" x="488" y="8" width="232" height="144"></rect>
<rect class="tint r6" x="488" y="160" width="232" height="80"></rect>
<g class="plus">
<path d="M512 176v8M508 180h8 M536 176v8M532 180h8 M560 176v8M556 180h8 M584 176v8M580 180h8 M608 176v8M604 180h8 M632 176v8M628 180h8 M656 176v8M652 180h8 M680 176v8M676 180h8 M704 176v8M700 180h8"></path>
<path d="M512 200v8M508 204h8 M536 200v8M532 204h8 M560 200v8M556 204h8 M584 200v8M580 204h8 M608 200v8M604 204h8 M632 200v8M628 204h8 M656 200v8M652 204h8 M680 200v8M676 204h8 M704 200v8M700 204h8"></path>
<path d="M512 224v8M508 228h8 M536 224v8M532 228h8 M560 224v8M556 228h8 M584 224v8M580 228h8 M608 224v8M604 228h8 M632 224v8M628 228h8 M656 224v8M652 228h8 M680 224v8M676 228h8 M704 224v8M700 228h8"></path>
</g>
<rect class="pan r6" x="488" y="248" width="232" height="44"></rect>
<line class="hair" x1="488" y1="270" x2="720" y2="270"></line>
<rect class="up r3" x="728" y="8" width="112" height="64"></rect>
<rect class="dn r3" x="728" y="80" width="112" height="64"></rect>
<rect class="pan r6" x="728" y="152" width="112" height="140"></rect>
<line class="hair" x1="728" y1="199" x2="840" y2="199"></line>
<line class="hair" x1="728" y1="246" x2="840" y2="246"></line>
<rect class="ink r6" x="848" y="8" width="120" height="284"></rect>
</svg>
<h1 class="name">The Daily Edge</h1>
<p class="tag">לוח המסחר של איציק נידם — מצב השוק, היומן, הנבחרות</p>
</div></body></html>
'''
os.makedirs(f'{D}/components/Cover', exist_ok=True)
open(f'{D}/components/Cover/preview.html', 'w', encoding='utf-8').write(cover)

now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
idx = {"v": 3, "layout": "files", "createdOnFiles": {"v": 1, "at": now}, "title": "The Daily Edge · ספר הסגנון", "namespace": "DailyEdge",
       "libraries": [], "sections": {}, "groups": [], "assetGroups": {}, "blobs": {}, "docs": {"readme": "project/README.md", "sections": []},
       "lastChange": {"by": "איציק נידם", "at": now, "via": "Claude Code", "note": "שלב 4ב — ספר הסגנון של כיוון ב (לוח המסחר)"}}
json.dump(idx, open(f'{D}/design-system.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
files = sorted(os.path.relpath(os.path.join(r, f), os.path.dirname(D)) for r, _, fs in os.walk(D) for f in fs)
print(json.dumps({f: f for f in files if f != 'project/design-system.json'}, ensure_ascii=False))
