#!/usr/bin/env python3
"""One-off migration of archived old key events to the 30 approved key events."""
import hashlib
import json
import os
import re
import sys
import urllib.request
from analytics_ga4_diagnostic import API, GOALS, PROPERTY, AnalyticsError, inventory, pages
from analytics_ga4_configure import create
from analytics_ga4_privacy_inventory import get
from webmaster_readonly import NoRedirect

# Fingerprints of the six exact archived resources; the backup is independently decrypted and verified.
OLD_FINGERPRINTS=frozenset((
    '00406e6248a47358754043bcec395b44a63d55078d44fada3edcce544951a80a',
    'cc8db6d8ba903f621c6a376495f81fff0f7fe2aa834e478f575f54c39ae7d6af',
    '42c0de81b78f434adde75d3c49203ecea1e743d765d3a1bf5acdecb72732da06',
    'ae97746a5c86817d7837d1eb4fa5f917ebbc3b7b958a2cd5bc26967f5ff69bb8',
    '525becd9c37325dbbf398e6f231146c5abf6a6faf6b062e7f359c4eaa6dab924',
    'b7dfee416f7ed2b52f8e0a518011b616ae74bb2408be2ccb38fe91e8736a4f7f',
))
# Formerly uncertain interest_book is checked again and considered last, not blindly retried.
TARGETS=('interest_projects','interest_experience','interest_expertise','interest_news','book_excerpt_click','workbook_excerpt_click','interest_book')

def fingerprint(event):return hashlib.sha256(json.dumps(event,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def remove(prop,token,name):
    if not PROPERTY.fullmatch(prop) or not re.fullmatch(re.escape(prop)+r'/keyEvents/[1-9][0-9]{0,19}',name) or not isinstance(token,str) or not token or '\r' in token or '\n' in token:raise AnalyticsError('invalid delete')
    req=urllib.request.Request(API+name,headers={'Authorization':'Bearer '+token,'Accept':'application/json'},method='DELETE')
    # No redirect, no retry; a timeout means unknown outcome.
    with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as resp:
        if resp.status not in (200,204):raise AnalyticsError('unconfirmed delete')
        if len(resp.read(65537))>65536:raise AnalyticsError('invalid response')

def migrate(creds, *, find=inventory, list_pages=pages, get_ads=get, delete=remove, post=create, fingerprints=OLD_FINGERPRINTS):
    if len(fingerprints)!=6 or not set(TARGETS).issubset(GOALS):raise AnalyticsError('invalid plan')
    initial=find(*creds,include_private=True);prop=initial.get('property')
    if not isinstance(prop,str) or not PROPERTY.fullmatch(prop):raise AnalyticsError('invalid property')
    def state():
        info=find(*creds,include_private=True)
        if info.get('property')!=prop or not info.get('domain_matches') or not info.get('can_edit'):raise AnalyticsError('identity changed')
        events=list_pages(prop+'/keyEvents','keyEvents',info['token'])
        if len(events)!=info['key_event_count'] or any(not isinstance(e,dict) or not isinstance(e.get('eventName'),str) for e in events):raise AnalyticsError('inventory inconsistent')
        names=[e['eventName'] for e in events]
        if len(names)!=len(set(names)) or set(names).intersection(GOALS)!=set(info['present']):raise AnalyticsError('inventory changed')
        links=list_pages('v1beta/'+prop+'/googleAdsLinks','googleAdsLinks',info['token'],fetch=get_ads)
        if links:raise AnalyticsError('ads links present')
        return info,events
    info,events=state()
    old=[e for e in events if e['eventName'] not in GOALS and e.get('custom',False) is True and e.get('deletable',False) is True]
    if len(old)!=6 or {fingerprint(e) for e in old}!=set(fingerprints):raise AnalyticsError('archived old goals changed')
    if set(info['missing'])!=set(TARGETS):raise AnalyticsError('approved state changed')
    deleted=0;created=[];remaining=set(fingerprints)
    for old_fp in sorted(fingerprints):
        info,events=state()
        old_current=[e for e in events if e['eventName'] not in GOALS and e.get('custom',False) is True and e.get('deletable',False) is True]
        if len(old_current)!=len(remaining) or {fingerprint(e) for e in old_current}!=remaining:raise AnalyticsError('old goals changed')
        target=next(e for e in old_current if fingerprint(e)==old_fp)
        delete(prop,info['token'],target.get('name',''))
        after,events=state()
        if any(e.get('name')==target['name'] for e in events):raise AnalyticsError('delete not confirmed')
        remaining.remove(old_fp);deleted+=1
    for name in TARGETS:
        info,events=state()
        if name in info['present']:continue
        if any(e['eventName'] not in GOALS and e.get('custom',False) is True and e.get('deletable',False) is True for e in events):raise AnalyticsError('old goal reappeared')
        # GA4 limit is 30 custom key events; non-custom automatic events do not consume it.
        if info['custom_total']>=30:raise AnalyticsError('custom limit')
        post(prop,info['token'],name)
        after,_=state()
        if name not in after['present']:raise AnalyticsError('create not confirmed')
        created.append(name)
    final,_=state()
    return {'deleted':deleted,'created':len(created),'present':len(final['present']),'missing':len(final['missing']),'old_custom':final['old_custom_deletable'],'total':final['key_event_count']}

def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        r=migrate(creds)
        print('::notice title=GA4 goal migration::'+'; '.join(k+'='+str(v) for k,v in r.items())+'; history_not_deleted; delivery_not_verified')
        return 0 if r['present']==30 and r['missing']==0 and r['old_custom']==0 else 1
    except Exception:
        print('::error title=GA4 goal migration::stopped; partial_changes_possible; reconcile_state_before_any_retry',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
