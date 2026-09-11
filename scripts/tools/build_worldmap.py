#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_worldmap.py — כלי חד-פעמי: TopoJSON של world-atlas (110m) → assets/worldmap.json
עם path-ים של SVG בהיטל שטוח (equirectangular), לטאב "שווקים בינלאומיים" (11.9.2026).

למה לא ספרייה בזמן ריצה: המפה סטטית — הגבולות לא משתנים — ולכן היא נבנית פעם אחת
ומוגשת כקובץ קטן (~45KB). בזמן ריצה app.js רק צובע מדינות לפי world.json ומצייר
נקודות בורסה וקו יום/לילה.

שימוש:
    curl -sL -o /tmp/countries-110m.json https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json
    python scripts/tools/build_worldmap.py /tmp/countries-110m.json

פלט: {"w":1000,"h":440,"lat0":-56,"countries":{"<iso-numeric>":"M…Z", …}}
אנטארקטיקה מושמטת, והקנבס נחתך בקו רוחב 56- (מתחתיו אין בורסות ורק ים).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "worldmap.json")
W, H = 1000.0, 440.0
LAT_TOP, LAT_BOTTOM = 84.0, -56.0        # קו הרוחב העליון/תחתון של הקנבס
SKIP_IDS = {"010"}                       # אנטארקטיקה


def decode_arcs(topo):
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        out.append(pts)
    return out


def ring_points(ring, arcs):
    pts = []
    for idx in ring:
        a = arcs[~idx][::-1] if idx < 0 else arcs[idx]
        if pts:
            a = a[1:]
        pts.extend(a)
    return pts


def project(lon, lat):
    x = (lon + 180.0) / 360.0 * W
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * H
    return x, y


def ring_path(pts):
    # דיוק של פיקסל שלם על קנבס 1000×440 — מספיק לעין, וחוסך ~40% מהקובץ.
    # איים זעירים (תיבה < 2px) מושמטים: הם רעש ויזואלי במפה בגודל הזה.
    xy = [tuple(map(round, project(lon, lat))) for lon, lat in pts]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    if max(xs) - min(xs) < 2 and max(ys) - min(ys) < 2:
        return ""
    # טבעות שחוצות את קו התאריך (קיריבטי, פיג'י, רוסיה): קפיצה של >180° אורך בין
    # שתי נקודות עוקבות מציירת קו לרוחב כל המפה. שוברים שם לתת-מסלול חדש.
    d, last, lastlon, sub = [], None, None, 0
    for (x, y), (lon, _) in zip(xy, pts):
        if (x, y) == last:
            continue
        jump = lastlon is not None and abs(lon - lastlon) > 180
        if jump:
            if sub > 2:
                d.append("Z")
            sub = 0
        d.append(("M" if sub == 0 else "L") + f"{x},{y}")
        sub += 1
        last, lastlon = (x, y), lon
    return "".join(d) + "Z" if sub > 2 else ""


def geometry_path(geom, arcs):
    polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
    parts = []
    for poly in polys:
        for ring in poly:
            p = ring_path(ring_points(ring, arcs))
            if p:
                parts.append(p)
    return "".join(parts)


def main(src):
    topo = json.load(open(src, encoding="utf-8"))
    arcs = decode_arcs(topo)
    countries = {}
    for g in topo["objects"]["countries"]["geometries"]:
        gid = str(g.get("id") or "")
        if not gid or gid in SKIP_IDS:
            continue
        countries[gid] = geometry_path(g, arcs)
    payload = {"w": W, "h": H, "latTop": LAT_TOP, "latBottom": LAT_BOTTOM, "countries": countries}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"[done] {OUT}: {len(countries)} מדינות, {os.path.getsize(OUT) // 1024}KB")


if __name__ == "__main__":
    main(sys.argv[1])
