#!/usr/bin/env python3
"""Bounded, read-only GA4 configuration inventory. No event or setting writes."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from webmaster_after_deploy import refresh_google
from webmaster_readonly import NoRedirect

API='https://analyticsadmin.googleapis.com/v1beta/'
MEASUREMENT='G-DM41FJYWX0'
# Only these project-owned event names may appear in public Actions annotations.
GOALS=('presentation_download','resume_click_hh','resume_click_zarplata','contact_phone_click','contact_email_click','setka_profile_click',
       'channel_telegram_click','channel_max_click','channel_dzen_click','setka_community_click','setka_channel_click','tenchat_profile_click',
       'interest_book','interest_checklist','checklist_print_click','book_excerpt_click','workbook_excerpt_click','interest_academy',
       'corporate_training_click','interest_guides','interest_articles','interest_projects','interest_experience','interest_expertise',
       'interest_news','interest_calculators','calculator_calculate','interest_diagnostic','diagnostic_start','interest_career')
PROPERTY=re.compile(r'properties/[1-9][0-9]{0,19}\Z')

class AnalyticsError(Exception):pass


def request(path,token,params):
    if not (path=='accountSummaries' or re.fullmatch(r'properties/[1-9][0-9]{0,19}/(?:dataStreams|keyEvents)',path)):
        raise AnalyticsError('invalid path')
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:raise AnalyticsError('invalid token')
    url=API+path+'?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/json'},method='GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as resp:raw=resp.read(1024*1024+1)
        if len(raw)>1024*1024:raise AnalyticsError('oversized')
        data=json.loads(raw)
        if not isinstance(data,dict):raise AnalyticsError('invalid response')
        return data
    except (urllib.error.URLError,TimeoutError,OSError,UnicodeError,ValueError):
        raise AnalyticsError('read failed') from None


def pages(path,field,token,*,fetch=request):
    items=[];next_token='';seen=set()
    for _ in range(10):
        params={'pageSize':100}
        if next_token:params['pageToken']=next_token
        data=fetch(path,token,params)
        if not isinstance(data,dict):raise AnalyticsError('invalid response')
        page=data.get(field,[])
        if not isinstance(page,list) or len(page)>100 or any(not isinstance(x,dict) for x in page):raise AnalyticsError('invalid page')
        items.extend(page)
        next_token=data.get('nextPageToken','')
        if not isinstance(next_token,str) or len(next_token)>4096:raise AnalyticsError('invalid pagination')
        if not next_token:return items
        if next_token in seen:raise AnalyticsError('pagination loop')
        seen.add(next_token)
    raise AnalyticsError('pagination limit')


def inventory(client_id,secret,refresh_token,*,refresh=refresh_google,fetch=request,include_private=False):
    creds=(client_id,secret,refresh_token)
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in creds):raise AnalyticsError('missing credentials')
    token=refresh(*creds)
    accounts=pages('accountSummaries','accountSummaries',token,fetch=fetch)
    props=[]
    for account in accounts:
        summaries=account.get('propertySummaries',[])
        if not isinstance(summaries,list) or any(not isinstance(x,dict) or not isinstance(x.get('property'),str) or not PROPERTY.fullmatch(x['property']) for x in summaries):raise AnalyticsError('invalid properties')
        props.extend(summaries)
    if len(props)>50 or len({x['property'] for x in props})!=len(props):raise AnalyticsError('too many or duplicate properties')
    matches=[]
    for item in props:
        prop=item['property']
        for stream in pages(prop+'/dataStreams','dataStreams',token,fetch=fetch):
            web=stream.get('webStreamData',{})
            if not isinstance(web,dict):raise AnalyticsError('invalid stream')
            if web.get('measurementId')==MEASUREMENT:
                parsed=urllib.parse.urlsplit(web.get('defaultUri',''))
                domain_ok=(parsed.scheme in ('http','https') and parsed.hostname=='scm-news.ru' and not parsed.username and not parsed.password and parsed.port in (None,80,443) and parsed.path in ('','/') and not parsed.query and not parsed.fragment)
                matches.append((prop,item.get('canEdit'),domain_ok))
    if len(matches)!=1:raise AnalyticsError('target stream not uniquely found')
    prop,can_edit,domain_ok=matches[0]
    if type(can_edit) is not bool:raise AnalyticsError('unknown permission')
    events=pages(prop+'/keyEvents','keyEvents',token,fetch=fetch)
    names=[]
    for event in events:
        name=event.get('eventName')
        if not isinstance(name,str) or not name or len(name)>128:raise AnalyticsError('invalid event')
        names.append(name)
    if len(names)!=len(set(names)):raise AnalyticsError('duplicate event')
    # Absence of protobuf boolean fields is equivalent to false. Reject unexpected types.
    for event in events:
        if any(type(event.get(k,False)) is not bool for k in ('custom','deletable')):raise AnalyticsError('invalid event flags')
    old=[event for event in events if event['eventName'] not in GOALS]
    counts={'old_custom_deletable':sum(e.get('custom',False) and e.get('deletable',False) for e in old),
            'old_default_deletable':sum(not e.get('custom',False) and e.get('deletable',False) for e in old),
            'old_nondeletable':sum(not e.get('deletable',False) for e in old),
            'custom_total':sum(e.get('custom',False) for e in events)}
    result={'status':'connected','can_edit':can_edit,'domain_matches':domain_ok,
            'key_event_count':len(names),'present':[name for name in GOALS if name in names],
            'missing':[name for name in GOALS if name not in names]}
    result.update(counts)
    if include_private: result.update(property=prop,token=token)
    return result


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or
        os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Inventory blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        data=inventory(*creds)
        print('::notice title=GA4 inventory::status=connected; editable='+str(data['can_edit']).lower()+'; domain_matches='+str(data['domain_matches']).lower()+'; key_events='+str(data['key_event_count'])+'; known_present='+str(len(data['present']))+'; known_missing='+str(len(data['missing']))+'; writes=0')
        print('::notice title=GA4 old event classification::custom_deletable='+str(data['old_custom_deletable'])+'; default_deletable='+str(data['old_default_deletable'])+'; nondeletable='+str(data['old_nondeletable'])+'; custom_total='+str(data['custom_total']))
        print('::notice title=GA4 known events::present='+(','.join(data['present']) or 'none'))
        return 0
    except Exception:
        print('::error title=GA4 inventory::read_or_identity_failed; writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
