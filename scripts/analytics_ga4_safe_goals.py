#!/usr/bin/env python3
"""Configure three new independent goals; skip previously uncertain interest_book."""
import os
import sys
from analytics_ga4_configure import configure
# Following previous stop, interest_book may have been attempted: never repeat it here.
TARGETS=('interest_checklist','interest_guides','interest_articles')

def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Setup blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        result=configure(creds,targets=TARGETS)
        print('::notice title=GA4 independent key events::created='+str(len(result['created']))+'; present='+str(len(result['present']))+'; missing='+str(len(result['missing']))+'; total='+str(result['count'])+'; uncertain_event_skipped=true')
        print('::notice title=GA4 project events::present='+(','.join(result['present']) or 'none')+'; missing='+(','.join(result['missing']) or 'none'))
        return 0
    except Exception:
        print('::error title=GA4 independent key events::stopped; inspect state before any further write; some writes may have succeeded',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
