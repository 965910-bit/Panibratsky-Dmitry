#!/usr/bin/env python3
"""Collect aggregate GA4/GSC metrics and store only an encrypted snapshot."""
import json,math,os,re,sys
from datetime import datetime,timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo
from analytics_ga4_diagnostic import GOALS, PROPERTY, inventory
from analytics_ga4_reports_diagnostic import request as ga_request
from analytics_ga4_encrypted_backup import encrypt
from live_seo_issue import request as gh_request
from webmaster_after_deploy import refresh_google
from webmaster_google_diagnostic import inspect as gsc_identity
from webmaster_google_performance import periods
from webmaster_readonly import GOOGLE_API, DOMAIN_PROPERTY, SITE, request_json

MARKER='<!-- scm-private-promotion-snapshot:v1 -->'
class SnapshotError(Exception):pass

def collect(admin,report,webmaster,*,identify=inventory,refresh=refresh_google,ga=ga_request,gsc_identify=gsc_identity,gsc=request_json):
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in (*admin,*report,*webmaster)):raise SnapshotError('credentials')
    info=identify(*admin,include_private=True);prop=info.get('property','')
    if not isinstance(prop,str) or not PROPERTY.fullmatch(prop) or not info.get('domain_matches'):raise SnapshotError('identity')
    token=refresh(*report)
    body={'dateRanges':[{'startDate':'28daysAgo','endDate':'yesterday'}], 'metrics':[{'name':'activeUsers'},{'name':'sessions'},{'name':'screenPageViews'}], 'limit':'1'}
    data=ga(prop,token,'runReport',body);rows=data.get('rows',[]);metadata=data.get('metadata',{})
    if not isinstance(rows,list) or len(rows)>1 or not isinstance(metadata,dict):raise SnapshotError('ga rows')
    def metadata_flags(m):
        t=m.get('subjectToThresholding',False);sampling=m.get('samplingMetadatas',[])
        if type(t) is not bool or not isinstance(sampling,list):raise SnapshotError('ga metadata')
        return {'thresholded':t,'sampled':bool(sampling)}
    def digits(x):
        if not isinstance(x,str) or not x.isascii() or not x.isdigit() or len(x)>18:raise SnapshotError('ga count')
        return int(x)
    totals=None
    if rows:
        vals=rows[0].get('metricValues') if isinstance(rows[0],dict) else None
        if not isinstance(vals,list) or len(vals)!=3 or any(not isinstance(v,dict) for v in vals):raise SnapshotError('ga metrics')
        totals=dict(zip(('active_users','sessions','page_views'),[digits(v.get('value')) for v in vals]))
    body={'dateRanges':[{'startDate':'28daysAgo','endDate':'yesterday'}],'dimensions':[{'name':'eventName'}], 'metrics':[{'name':'eventCount'}], 'dimensionFilter':{'filter':{'fieldName':'eventName','inListFilter':{'values':list(GOALS)}}},'limit':'100'}
    events=ga(prop,token,'runReport',body);event_rows=events.get('rows',[]);event_meta=events.get('metadata',{})
    if not isinstance(event_rows,list) or len(event_rows)>len(GOALS) or not isinstance(event_meta,dict):raise SnapshotError('event rows')
    counts={}
    for row in event_rows:
        if not isinstance(row,dict):raise SnapshotError('event row')
        d=row.get('dimensionValues');v=row.get('metricValues')
        if not isinstance(d,list) or len(d)!=1 or not isinstance(d[0],dict) or not isinstance(v,list) or len(v)!=1 or not isinstance(v[0],dict):raise SnapshotError('event values')
        name=d[0].get('value')
        if name not in GOALS or name in counts:raise SnapshotError('event name')
        counts[name]=digits(v[0].get('value'))
    gt=refresh(*webmaster);identity=gsc_identify(*webmaster,refresh=lambda *args:gt)
    if identity.get('status')!='connected' or identity.get('property_type') not in ('url_prefix','domain'):raise SnapshotError('gsc identity')
    site=DOMAIN_PROPERTY if identity['property_type']=='domain' else SITE
    url=GOOGLE_API+'/sites/'+quote(site,safe='')+'/searchAnalytics/query'
    search=[]
    for start,end in periods(datetime.now(ZoneInfo('America/Los_Angeles')).date()):
        result=gsc(url,gt,'Bearer',{'startDate':start.isoformat(),'endDate':end.isoformat(),'type':'web','dataState':'final','rowLimit':1})
        entries=result.get('rows',[]) if isinstance(result,dict) else None
        if not isinstance(entries,list) or len(entries)>1:raise SnapshotError('search rows')
        metrics=None
        if entries:
            row=entries[0]
            if not isinstance(row,dict):raise SnapshotError('search row')
            metrics={}
            for key in ('clicks','impressions','ctr','position'):
                value=row.get(key)
                if type(value) not in (int,float) or not math.isfinite(value) or value<0 or (key=='ctr' and value>1):raise SnapshotError('search metric')
                metrics[key]=value
        search.append({'start':start.isoformat(),'end':end.isoformat(),'metrics':metrics})
    return {'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'ga4':{'period':'28daysAgo_to_yesterday','totals':totals,'totals_metadata':metadata_flags(metadata),'events':counts,'events_metadata':metadata_flags(event_meta)},'search_console':search}

def publish(doc,repo,token,*,seal=encrypt,call=gh_request):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or not token or '\n' in token or '\r' in token:raise SnapshotError('target')
    base='https://api.github.com/repos/'+repo
    meta=call(base,token)
    if not isinstance(meta,dict) or meta.get('id')!=1102759388:raise SnapshotError('target identity')
    raw=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode()
    if len(raw)>20000:raise SnapshotError('size')
    encrypted=seal(raw)
    body=MARKER+'\n\nEncrypted aggregate report; private recovery key required.\n\n```json\n'+json.dumps(encrypted,separators=(',',':'))+'\n```'
    result=call(base+'/issues/244/comments',token,method='POST',body={'body':body})
    if not isinstance(result,dict) or type(result.get('id')) is not int or result['id']<1:raise SnapshotError('unconfirmed')
    return result['id']

def main():
    if os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch','schedule') or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    def creds(prefix):return [os.environ.pop(prefix+x,'') for x in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN')]
    admin=creds('SCM_GA4_');report=creds('SCM_GA4_REPORT_');webmaster=creds('SCM_WM_GOOGLE_');token=os.environ.pop('GITHUB_TOKEN','')
    try:
        data=collect(admin,report,webmaster);identifier=publish(data,os.environ.get('GITHUB_REPOSITORY',''),token)
        print('::notice title=Private snapshot::encrypted_comment_id='+str(identifier)+'; no_google_writes; restore_verification_required');return 0
    except Exception:
        print('::error title=Private snapshot::report_or_storage_failed; no_google_writes; reconcile_before_retry',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
