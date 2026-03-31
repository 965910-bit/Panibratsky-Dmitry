import imaplib
import email
import re
import json
import os
from email.header import decode_header
from datetime import datetime
from typing import List, Dict

class GoogleAlertsCollector:
    def __init__(self, email_user, email_password, imap_server="imap.gmail.com"):
        self.email_user = email_user
        self.email_password = email_password
        self.imap_server = imap_server

    def _connect(self):
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_password)
            mail.select("INBOX")
            return mail
        except Exception as e:
            print(f"IMAP error: {e}")
            return None

    def _decode_mime(self, value):
        if value is None:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    if encoding:
                        result.append(part.decode(encoding))
                    else:
                        result.append(part.decode("utf-8", errors="replace"))
                except:
                    result.append(part.decode("utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)

    def _extract_links(self, body):
        links = re.findall(r'href=["\'](https?://[^"\']+)["\']', body)
        clean = []
        for link in links:
            if "google.com/url?q=" in link:
                m = re.search(r'q=([^&]+)', link)
                if m:
                    link = m.group(1)
            if link.startswith("http") and not link.startswith("https://www.google.com"):
                clean.append(link)
        return clean

    def fetch(self, since_days=1):
        result = {"alerts": []}
        mail = self._connect()
        if not mail:
            return result

        from datetime import timedelta
        date_since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        typ, data = mail.search(None, f'(SINCE "{date_since}" SUBJECT "Google Alert")')
        if typ != "OK":
            mail.logout()
            return result

        for num in data[0].split():
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = self._decode_mime(msg.get("Subject", ""))
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                body += payload.decode("utf-8", errors="ignore")
                    else:
                        payload = msg.get_payload(decode=True)
                        body = payload.decode("utf-8", errors="ignore")

                    links = self._extract_links(body)
                    for link in links:
                        result["alerts"].append({
                            "link": link,
                            "source": "Google Alert",
                            "subject": subject,
                            "date": datetime.now().isoformat()
                        })
        mail.logout()
        return result
