import imaplib
import email
import re
import json
import os
import urllib.parse
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Dict
from bs4 import BeautifulSoup

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
        if " – " in subject:
            keyword = subject.split(" – ", 1)[1].strip()
            keyword = keyword.strip('"')
            return keyword
        for prefix in ["Google Alert – ", "Оповещение Google – "]:
            if subject.startswith(prefix):
                return subject.replace(prefix, "").strip()
        return "unknown"

    def _extract_links(self, body):
        """
        Извлекает URL из текста или HTML.
        """
        links = []
        # Парсим HTML
        soup = BeautifulSoup(body, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http'):
                links.append(href)
        # Если ссылок не нашли, пробуем искать URL в тексте
        if not links:
            url_pattern = r'(?:<)?(https?://[^\s<>]+)(?:>)?'
            raw_urls = re.findall(url_pattern, body)
            for link in raw_urls:
                link = link.rstrip('.,:;!?)]')
                if link.startswith('http'):
                    links.append(link)
        # Обрабатываем ссылки Google и очищаем
        clean = []
        for link in links:
            if "google.com/url?" in link:
                q_match = re.search(r'[?&]q=([^&]+)', link)
                if q_match:
                    link = q_match.group(1)
                    try:
                        link = urllib.parse.unquote(link)
                    except:
                        pass
            if link.startswith("http") and not link.startswith("https://www.google.com"):
                clean.append(link)
        return clean

    def fetch(self, since_days=7):
        result = {"alerts": []}
        mail = self._connect()
        if not mail:
            return result

        date_since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{date_since}")'
        print(f"🔍 Поиск писем: {search_criteria}")

        typ, data = mail.search(None, search_criteria)
        if typ != "OK":
            print("❌ Ошибка поиска писем")
            mail.logout()
            return result

        email_ids = data[0].split()
        print(f"📧 Найдено писем: {len(email_ids)}")

        processed = 0
        for num in email_ids:
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = self._decode_mime(msg.get("Subject", ""))
                    if "Google Alert" not in subject and "Оповещение Google" not in subject:
                        continue
                    keyword = self._extract_keyword(subject)
                    body_text = ""
                    body_html = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                payload = part.get_payload(decode=True)
                                body_text += payload.decode("utf-8", errors="ignore")
                            elif content_type == "text/html":
                                payload = part.get_payload(decode=True)
                                body_html += payload.decode("utf-8", errors="ignore")
                    else:
                        payload = msg.get_payload(decode=True)
                        body_text = payload.decode("utf-8", errors="ignore")

                    # Ищем ссылки сначала в text/plain, потом в text/html
                    links = self._extract_links(body_text)
                    if not links and body_html:
                        links = self._extract_links(body_html)

                    if links:
                        print(f"   Из письма '{subject[:50]}...' извлечено ссылок: {len(links)} (тема: {keyword})")
                    else:
                        body_preview = (body_text or body_html)[:300].replace('\n', ' ')
                        print(f"   ⚠️  В письме '{subject[:50]}...' не найдено ссылок. Фрагмент: {body_preview}")
                    for link in links:
                        result["alerts"].append({
                            "link": link,
                            "source": "Google Alert",
                            "subject": subject,
                            "keyword": keyword,
                            "date": datetime.now().isoformat()
                        })
                    processed += 1
                    if processed >= 5:
                        break
        mail.logout()
        print(f"✅ Всего собрано ссылок: {len(result['alerts'])}")
        return result
