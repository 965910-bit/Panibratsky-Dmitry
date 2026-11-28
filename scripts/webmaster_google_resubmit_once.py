#!/usr/bin/env python3
"""One-off Google sitemap resubmission for a stale error, never automatic or retried."""
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from indexnow_submit import validate_live
from webmaster_actions import api, GOOGLE_API, SITE, DOMAIN_PROPERTY, MAP, ActionError
from webmaster_after_deploy import refresh_google
from webmaster_google_diagnostic import sitemap_health


def stale(value, now):
    try:
        if not isinstance(value,str):return False
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        return stamp.tzinfo is not None and stamp <= now-timedelta(days=30)
    except (ValueError,OverflowError):return False


def resubmit(creds, *, refresh=refresh_google, request=api, validate=validate_live, now=None):
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in creds):raise ActionError('invalid credentials')
    token=refresh(*creds)
    sites=request(GOOGLE_API+'/sites',token,'Bearer').get('siteEntry')
    if not isinstance(sites,list) or any(not isinstance(x,dict) or not isinstance(x.get('siteUrl'),str) for x in sites):raise ActionError('invalid sites')
    matching=[x for x in sites if x['siteUrl'] in (SITE,DOMAIN_PROPERTY)]
    if len({x['siteUrl'] for x in matching})!=len(matching):raise ActionError('ambiguous property')
    selected=next((x for x in matching if x['siteUrl']==SITE),None) or next((x for x in matching if x['siteUrl']==DOMAIN_PROPERTY),None)
    if not selected or selected.get('permissionLevel') not in ('siteOwner','siteFullUser'):raise ActionError('permission unavailable')
    base=GOOGLE_API+'/sites/'+quote(selected['siteUrl'],safe='')
    maps=request(base+'/sitemaps',token,'Bearer').get('sitemap')
    if not isinstance(maps,list) or any(not isinstance(x,dict) or not isinstance(x.get('path'),str) for x in maps):raise ActionError('invalid sitemap')
    found=[x for x in maps if x['path']==MAP]
    now=now or datetime.now(timezone.utc)
    if len(found)!=1:raise ActionError('sitemap missing or ambiguous')
    item=found[0]
    # Both last fetch and last submission must be old: do not repeat a recent attempt.
    if sitemap_health(item)!='error' or item.get('isPending') is not False or not stale(item.get('lastDownloaded'),now) or not stale(item.get('lastSubmitted'),now):
        return 'not_eligible'
    validate([]) # Live XML must be valid and match the repository's exact URL set.
    # Exactly one PUT. API's generic request only retries GET, never a write.
    request(base+'/sitemaps/'+quote(MAP,safe=''),token,'Bearer',method='PUT')
    return 'submitted'


def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':
        print('Blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(x,'') for x in ('SCM_WM_GOOGLE_CLIENT_ID','SCM_WM_GOOGLE_CLIENT_SECRET','SCM_WM_GOOGLE_REFRESH_TOKEN')]
    try:
        status=resubmit(creds)
        print('::notice title=Google sitemap::status='+status+'; indexing_not_guaranteed; no_yandex_requests')
        return 0
    except Exception:
        print('::error title=Google sitemap::stopped; write_outcome_may_be_unknown; do_not_retry_without_reconciliation',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
