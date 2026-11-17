"""Collect alerts without interpolating credentials into code or logs."""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from collectors.google_alerts import GoogleAlertsCollector


def main():
    user, password = os.environ.get('GMAIL_USER'), os.environ.get('GMAIL_PASSWORD')
    if not user or not password:
        print('Google Alerts: credentials not configured; retaining existing data')
        return
    try:
        alerts = GoogleAlertsCollector(user, password).fetch()
    except Exception:
        # Mail/server errors can contain addresses, query text or credentials.
        print('Google Alerts: collection failed; details withheld')
        raise SystemExit(1) from None
    # Email-derived candidates are private scratch data, not a public feed.
    path = ROOT / '.local-news' / 'google_alerts.json'
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='.alerts-', suffix='.tmp', dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(alerts, file, ensure_ascii=False)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
