#!/usr/bin/env python3
"""
notify_telegram_image.py — שולח תמונה בודדת לערוץ הטלגרם (sendPhoto, multipart).

מיועד לשליחות חד-פעמיות/תקופתיות של גרפיקה (למשל לוח הדיווחים השבועי) דרך
workflow_dispatch — לא רץ אוטומטית בכל ריצת Action. הקובץ חייב להיות כבר
מחויב (commit) בריפו כשמריצים, כי ה-Action קורא אותו מה-checkout המקומי.

קלט: משתני סביבה BROADCAST_IMAGE (נתיב יחסי לריפו) + BROADCAST_CAPTION (אופציונלי).
סודות: TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL (אותם סודות של שאר ההתראות).
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def send_photo(token, chat, file_path, caption):
    url = "https://api.telegram.org/bot%s/sendPhoto" % token
    boundary = "----nidamBoundary7f3a9c"
    with open(file_path, "rb") as f:
        file_data = f.read()
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    ctype = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "application/octet-stream"

    def field(name, value):
        return ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                % (boundary, name, value)).encode("utf-8")

    parts = [field("chat_id", chat)]
    if caption:
        parts.append(field("caption", caption))
    parts.append(('--%s\r\nContent-Disposition: form-data; name="photo"; filename="%s"\r\n'
                  'Content-Type: %s\r\n\r\n' % (boundary, filename, ctype)).encode("utf-8"))
    parts.append(file_data)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % boundary,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL")
    image = (os.environ.get("BROADCAST_IMAGE") or "").strip()
    caption = (os.environ.get("BROADCAST_CAPTION") or "").strip()

    if not token or not chat:
        print("[skip] אין TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL — דילוג.")
        return 0
    if not image:
        print("[skip] BROADCAST_IMAGE ריק — לא התבקשה שליחת תמונה.")
        return 0

    path = os.path.join(ROOT, image)
    if not os.path.exists(path):
        print("[fail] הקובץ לא נמצא בריפו: %s" % image)
        return 1

    try:
        resp = send_photo(token, chat, path, caption)
        if resp.get("ok"):
            print("[ok] התמונה (%s) נשלחה לערוץ." % image)
            return 0
        print("[fail] טלגרם החזיר שגיאה: %s" % resp)
        return 1
    except Exception as e:
        print("[fail] שליחה נכשלה: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
