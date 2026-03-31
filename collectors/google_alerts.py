import imaplib
import email
import re
import json
import os
from email.header import decode_header
from datetime import datetime, timedelta
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
            print(f"✅ Подключено к IMAP {self.imap_server}")
            return mail
        except Exception as e:
            print(f"❌ Ошибка IMAP: {e}")
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

    def _extract_keyword(self, subject: str) -> str:
        """
        Извлекает ключевое слово из темы письма Google Alert.
        Поддерживает русские темы: "Оповещение Google – логистика"
        и английские: "Google Alert – logistics".
        """
        # Ищем разделитель " – " (пробел, длинное тире, пробел)
        if " – " in subject:
            keyword = subject.split(" – ", 1)[1].strip()
            keyword = keyword.strip('"')
            return keyword
        # Если разделитель не найден, возвращаем всё, что после "Google Alert" или "Оповещение Google"
        for prefix in ["Google Alert – ", "Оповещение Google – "]:
            if subject.startswith(prefix):
                return subject.replace(prefix, "").strip()
        return "unknown"

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

    def fetch(self, since_days=7):
        """
        Загружает письма Google Alerts за последние since_days дней.
        """
        result = {"alerts": []}
        mail = self._connect()
        if not mail:
            print("❌ Не удалось подключиться к почте")
            return result

        date_since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        # Ищем письма, где в теме есть "Google Alert" ИЛИ "Оповещение Google"
        search_criteria = f'(SINCE "{date_since}" OR SUBJECT "Google Alert" SUBJECT "Оповещение Google")'
        print(f"🔍 Поиск писем: {search_criteria}")

        typ, data = mail.search(None, search_criteria)
        if typ != "OK":
            print("❌ Ошибка поиска писем")
            mail.logout()
            return result

        email_ids = data[0].split()
        print(f"📧 Найдено писем: {len(email_ids)}")

        for num in email_ids:
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = self._decode_mime(msg.get("Subject", ""))
                    keyword = self._extract_keyword(subject)
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
                    if links:
                        print(f"   Из письма '{subject[:50]}...' извлечено ссылок: {len(links)} (тема: {keyword})")
                    for link in links:
                        result["alerts"].append({
                            "link": link,
                            "source": "Google Alert",
                            "subject": subject,
                            "keyword": keyword,
                            "date": datetime.now().isoformat()
                        })
        mail.logout()
        print(f"✅ Всего собрано ссылок: {len(result['alerts'])}")
        return result
