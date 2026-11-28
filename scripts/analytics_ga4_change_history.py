#!/usr/bin/env python3
"""Read bounded GA4 key event change history; emit only classifications."""
import json
import os
import re
import sys
import urllib.request
from analytics_ga4_diagnostic import AnalyticsError, PROPERTY, inventory, pages
from webmaster_readonly import NoRedirect

ACCOUNT=re.compile(r'accounts/[1-9][0-9]{0,19}\Z')
API='https://analyticsadmin.googleapis.com/v1alpha/'

def history_request(account,token,body):
    if not isinstance(account,str) or not ACCOUNT.fullmatch(account) or not isinstance(token,str) or not token or '\r' in token or '\n' in token:raise AnalyticsError('invalid request')
    req=urllib.request.Request(API+account+':searchChangeHistoryEvents',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json'},method='POST')
    with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as res:raw=res.read(1024*1024+1)
    if len(raw)>1024*1024:raise AnalyticsError('oversized response')
    result=json.loads(raw)
    if not isinstance(result,dict):raise AnalyticsError('invalid response')
    return result

def inspect_history(creds,*,find=inventory,read_pages=pages,read=history_request):
    info=find(*creds,include_private=True)
    prop=info.get('property');token=info.get('token')
    if not info.get('domain_matches') or not isinstance(prop,str) or not PROPERTY.fullmatch(prop):raise AnalyticsError('identity mismatch')
    accounts=read_pages('accountSummaries','accountSummaries',token)
    matching=[]
    for account in accounts:
        summaries=account.get('propertySummaries',[])
        if not isinstance(summaries,list) or any(not isinstance(x,dict) for x in summaries):raise AnalyticsError('invalid summary')
        if any(x.get('property')==prop for x in summaries):matching.append(account.get('account'))
    if len(matching)!=1 or not isinstance(matching[0],str) or not ACCOUNT.fullmatch(matching[0]):raise AnalyticsError('account mismatch')
    body={'property':prop,'resourceType':['KEY_EVENT'],'pageSize':100}
    events=[];seen=set()
    for _ in range(10):
        data=read(matching[0],token,body)
        rows=data.get('changeHistoryEvents',[]);next_token=data.get('nextPageToken','')
        if not isinstance(rows,list) or len(rows)>100 or any(not isinstance(x,dict) for x in rows):raise AnalyticsError('invalid page')
        events.extend(rows)
        if not isinstance(next_token,str) or len(next_token)>4096:raise AnalyticsError('invalid token')
        if not next_token:break
        if next_token in seen:raise AnalyticsError('pagination loop')
        seen.add(next_token);body['pageToken']=next_token
    else:raise AnalyticsError('pagination limit')
    known_created=0;target_changes=0;incomplete=False
    for event in events:
        filtered=event.get('changesFiltered',False)
        if type(filtered) is not bool:raise AnalyticsError('invalid history')
        incomplete |= filtered
        changes=event.get('changes',[])
        if not isinstance(changes,list):raise AnalyticsError('invalid history')
        for change in changes:
            if not isinstance(change,dict):raise AnalyticsError('invalid history')
            for field in ('resourceBeforeChange','resourceAfterChange'):
                snapshot=change.get(field,{})
                if not isinstance(snapshot,dict):raise AnalyticsError('invalid history')
                key=snapshot.get('keyEvent',{})
                if not isinstance(key,dict):raise AnalyticsError('invalid history')
                if key.get('eventName')=='interest_book':target_changes+=1;break
            after=change.get('resourceAfterChange',{}).get('keyEvent',{})
            if change.get('action')=='CREATED' and after.get('eventName') in info['present']:known_created+=1
    return {'events':len(events),'known_creations_observed':known_created,'target_changes':target_changes,'filtered':incomplete,'target_present':'interest_book' in info['present']}

def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('History check blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        data=inspect_history(creds)
        print('::notice title=GA4 history::'+'; '.join(k+'='+str(v).lower() for k,v in data.items())+'; absent_history_not_proof; writes=0')
        return 0
    except Exception:
        print('::error title=GA4 history::history_unavailable_or_invalid; writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
