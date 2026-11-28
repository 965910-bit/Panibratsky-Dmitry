#!/usr/bin/env python3
"""Read GA4 BigQuery and AdSense links without exposing project or account IDs."""
import json,os,re,sys,urllib.parse,urllib.request
from analytics_ga4_diagnostic import AnalyticsError, PROPERTY, GOALS, inventory, pages
from webmaster_readonly import NoRedirect
BASE='https://analyticsadmin.googleapis.com/'

def get(path,token,params):
    if not re.fullmatch(r'v1alpha/properties/[1-9][0-9]{0,19}/(?:bigQueryLinks|adSenseLinks)',path):raise AnalyticsError('invalid path')
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:raise AnalyticsError('invalid token')
    req=urllib.request.Request(BASE+path+'?'+urllib.parse.urlencode(params),headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as r:raw=r.read(1024*1024+1)
    if len(raw)>1024*1024:raise AnalyticsError('oversized')
    data=json.loads(raw)
    if not isinstance(data,dict):raise AnalyticsError('invalid response')
    return data

def inspect(creds,*,find=inventory,read_pages=pages,fetch=get):
    info=find(*creds,include_private=True);prop=info.get('property','')
    if not isinstance(prop,str) or not PROPERTY.fullmatch(prop) or not info.get('domain_matches'):raise AnalyticsError('identity mismatch')
    bq=read_pages('v1alpha/'+prop+'/bigQueryLinks','bigqueryLinks',info['token'],fetch=fetch)
    adsense=read_pages('v1alpha/'+prop+'/adSenseLinks','adsenseLinks',info['token'],fetch=fetch)
    if len(bq)>10 or len(adsense)>10:raise AnalyticsError('unexpected number')
    flags=[]
    for link in bq:
        def boolean(key):
            val=link.get(key,False)
            if type(val) is not bool:raise AnalyticsError('invalid boolean')
            return val
        streams=link.get('exportStreams',[]);excluded=link.get('excludedEvents',[])
        if not isinstance(streams,list) or not isinstance(excluded,list) or any(not isinstance(x,str) for x in streams+excluded):raise AnalyticsError('invalid list')
        flags.append({'daily':boolean('dailyExportEnabled'),'streaming':boolean('streamingExportEnabled'),
                      'fresh_daily':boolean('freshDailyExportEnabled'),'advertising_id':boolean('includeAdvertisingId'),
                      'target_stream_listed':info['stream'] in streams,'stream_list_empty':not streams,
                      'agreed_events_excluded':len(set(excluded).intersection(GOALS))})
    return {'bigquery_links':len(bq),'adsense_links':len(adsense),'flags':flags}

def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        r=inspect(creds)
        print('::notice title=GA4 linked products::bigquery_links='+str(r['bigquery_links'])+'; adsense_links='+str(r['adsense_links'])+'; writes=0')
        for i,item in enumerate(r['flags']):
            print('::notice title=GA4 BigQuery link '+str(i+1)+'::'+'; '.join(k+'='+str(v).lower() for k,v in item.items())+'; export_success_and_billing_not_checked')
        return 0
    except Exception:
        print('::error title=GA4 linked products::read_or_identity_failed; writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
