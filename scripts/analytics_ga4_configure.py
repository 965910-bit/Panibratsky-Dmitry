#!/usr/bin/env python3
"""One-off conservative GA4 key-event setup; no deletes or automatic POST retry."""
import json
import os
import re
import sys
import urllib.request
from webmaster_readonly import NoRedirect
from analytics_ga4_diagnostic import API, GOALS, PROPERTY, AnalyticsError, inventory

# Conservative for standard GA4: includes even default events in this bound.
LIMIT = 30
# Prioritize active, meaningful interactions; unpublished excerpts take remaining slots last.
PRIORITY = ('presentation_download','resume_click_hh','resume_click_zarplata',
    'contact_phone_click','contact_email_click','setka_profile_click',
    'channel_telegram_click','channel_max_click','channel_dzen_click',
    'setka_community_click','setka_channel_click','tenchat_profile_click',
    'corporate_training_click','calculator_calculate','diagnostic_start',
    'checklist_print_click','interest_career','interest_diagnostic',
    'interest_calculators','interest_academy','interest_book','interest_checklist',
    'interest_guides','interest_articles','interest_projects','interest_experience',
    'interest_expertise','interest_news','book_excerpt_click','workbook_excerpt_click')
assert len(PRIORITY)==len(GOALS) and set(PRIORITY)==set(GOALS)

def create(prop, token, name):
    if not PROPERTY.fullmatch(prop) or name not in GOALS or not token or '\n' in token or '\r' in token:
        raise AnalyticsError('invalid request')
    req = urllib.request.Request(API + prop + '/keyEvents',
        data=json.dumps({'eventName':name}).encode(),
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'}, method='POST')
    # No redirects, retries, or logging response/error bodies. Failure may have an unknown outcome.
    with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:
        raw=response.read(65537)
    if len(raw)>65536: raise AnalyticsError('invalid response')
    data=json.loads(raw)
    if not isinstance(data,dict) or data.get('eventName') != name: raise AnalyticsError('unconfirmed response')

def configure(creds, *, inspect=inventory, post=create, targets=PRIORITY):
    if not isinstance(targets,tuple) or len(set(targets))!=len(targets) or any(n not in GOALS for n in targets):
        raise AnalyticsError('invalid target list')
    initial=inspect(*creds, include_private=True)
    if not initial['can_edit'] or not initial['domain_matches']:
        raise AnalyticsError('identity or permissions not verified')
    prop=initial['property']; created=[]
    # Recheck state before each write: never overwrite or remove other goals.
    for name in targets:
        state=inspect(*creds, include_private=True)
        if state['property']!=prop or not state['can_edit'] or not state['domain_matches']:
            raise AnalyticsError('identity or permissions changed')
        if name in state['present']: continue
        if state['key_event_count']>=LIMIT: break
        try:
            post(prop,state['token'],name)
        except Exception:
            # A rejected/timeout POST may have reached Google. Never retry here.
            raise AnalyticsError('write outcome uncertain; stopped') from None
        confirmed=inspect(*creds, include_private=True)
        if (confirmed['property']!=prop or not confirmed['can_edit'] or not confirmed['domain_matches']
            or name not in confirmed['present']):
            raise AnalyticsError('write not confirmed; stopped')
        created.append(name)
    final=inspect(*creds, include_private=True)
    if final['property']!=prop or not final['can_edit'] or not final['domain_matches']:
        raise AnalyticsError('final identity check failed')
    return {'created':created,'present':final['present'],'missing':final['missing'],'count':final['key_event_count']}

def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main'
        or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Configuration blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        result=configure(creds)
        print('::notice title=GA4 key events::created='+str(len(result['created']))+'; present='+str(len(result['present']))+'; missing='+str(len(result['missing']))+'; total='+str(result['count']))
        print('::notice title=GA4 project events::present='+(','.join(result['present']) or 'none')+'; missing='+(','.join(result['missing']) or 'none'))
        return 0
    except Exception:
        print('::error title=GA4 key events::configuration_stopped; inspect current state before any retry; some writes may have succeeded',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
