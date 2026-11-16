"""Collect alerts without interpolating credentials into code or logs."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from collectors.google_alerts import GoogleAlertsCollector


def main():
    user, password = os.environ.get('GMAIL_USER'), os.environ.get('GMAIL_PASSWORD')
    if not user or not password:
        print('Google Alerts: credentials not configured; retaining existing data')
        return
    alerts = GoogleAlertsCollector(user, password).fetch()
    path = ROOT / 'data/google_alerts.json'
    temp = path.with_suffix('.json.tmp')
    try:
        temp.write_text(json.dumps(alerts, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
