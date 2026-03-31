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

def is_valid_link(link: str) -> bool:
    """Проверка, что ссылка ведёт на реальную статью, а не на изображение, CSS, JS и т.д."""
    link_lower = link.lower()
    
    # Исключаем служебные ссылки
    banned_terms = [
        'google.com/alerts',
        'google.com/support',
        'schema.org',
        'mail.google.com',
        'accounts.google.com',
        'gstatic.com',          # изображения, шрифты Google
        'googleapis.com',       # API, стили
        'fonts.googleapis.com',
        'fonts.gstatic.com',
        'yandex.net',
        'yandex.st',
        'mc.yandex.ru',         # метрика
        'google-analytics.com',
        'googletagmanager.com'
    ]
    for banned in banned_terms:
        if banned in link_lower:
            return False
    
    # Исключаем ссылки, заканчивающиеся на расширения статических файлов
    static_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', 
                         '.css', '.js', '.json', '.xml', '.txt', '.pdf')
    if link_lower.endswith(static_extensions):
        return False
    
    # Проверяем, содержит ли ссылка хотя бы один из разрешённых доменов
    allowed_domains = [
        'logistics360.ru',
        'ati.su',
        'cnews.ru',
        'logistics.ru',
        'vc.ru',
        'habr.com',
        'tadviser.ru',
        'interfax.ru',
        'rzd-partner.ru',
        'xpert.digital',
        'abn24.ru',
        'logirus.ru',
        'kommersant.ru',
        'vedomosti.ru',
        'rbc.ru',
        '1prime.ru',
        'rg.ru'
    ]
    for domain in allowed_domains:
        if domain in link_lower:
            return True
    
    # Если домен не из списка, выводим предупреждение и пропускаем
    print(f"   ⚠️  Неизвестный домен: {link}")
    return False

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
        match = re.search(r'[–—]\s*([^–—]+?)$', subject)
        if match:
            keyword = match.group(1).strip()
            keyword = keyword.strip('"')
            return keyword
        for prefix in ["Google Alert – ", "Оповещение Google – ", "Оповещение Google – "]:
            if subject.startswith(prefix):
                return subject.replace(prefix, "").strip()
        return "unknown"

    def _extract_links(self, body):
        links = []
        soup = BeautifulSoup(body, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http'):
                links.append(href)
        md_links = re.findall(r'\[[^\]]*\]\((https?://[^\)]+)\)', body)
        links.extend(md_links)
        url_pattern = r'https?://[^\s<>"\'\)]+'
        raw_urls = re.findall(url_pattern, body)
        links.extend(raw_urls)

        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        clean = []
        for link in unique_links:
            if "google.com/url?" in link:
                q_match = re.search(r'[?&]q=([^&]+)', link)
                if q_match:
                    link = q_match.group(1)
                    try:
                        link = urllib.parse.unquote(link)
                    except:
                        pass
            if link.startswith("http") and not link.startswith("https://www.google.com"):
                link = link.rstrip('.,:;!?)]')
                if is_valid_link(link):
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
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/html":
                                payload = part.get_payload(decode=True)
                                body = payload.decode("utf-8", errors="ignore")
                                break
                        if not body:
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    body = payload.decode("utf-8", errors="ignore")
                                    break
                    else:
                        payload = msg.get_payload(decode=True)
                        body = payload.decode("utf-8", errors="ignore")

                    links = self._extract_links(body)
                    if links:
                        print(f"   Из письма '{subject[:50]}...' извлечено ссылок: {len(links)} (тема: {keyword})")
                    else:
                        body_preview = body[:300].replace('\n', ' ')
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
