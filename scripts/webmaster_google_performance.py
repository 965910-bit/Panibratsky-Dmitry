#!/usr/bin/env python3
"""Weekly Search Console performance health; public logs contain no raw metrics."""
import math
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
from webmaster_after_deploy import refresh_google
from webmaster_google_diagnostic import inspect
from webmaster_readonly import DOMAIN_PROPERTY, GOOGLE_API, SITE, request_json

class PerformanceError(Exception):pass

def periods(today):
    end=today-timedelta(days=5)
    start=end-timedelta(days=27)
    old_end=start-timedelta(days=1)
    return (start,end),(old_end-timedelta(days=27),old_end)

def direction(current,previous):
    if previous==0:return 'no_baseline'
    if current>previous:return 'up'
    if current<previous:return 'down'
    return 'unchanged'

def run(creds,*,refresh=refresh_google,identify=inspect,request=request_json,today=None):
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in creds):raise PerformanceError('missing credentials')
    token=refresh(*creds)
    identity=identify(*creds,refresh=lambda *args:token)
    if identity.get('status')!='connected':raise PerformanceError('property unavailable')
    property_type=identity.get('property_type')
    if property_type not in ('domain','url_prefix'):raise PerformanceError('invalid property')
    prop=DOMAIN_PROPERTY if property_type=='domain' else SITE
    url=GOOGLE_API+'/sites/'+quote(prop,safe='')+'/searchAnalytics/query'
    results=[]
    for start,end in periods(today or datetime.now(ZoneInfo('America/Los_Angeles')).date()):
        data=request(url,token,'Bearer',{'startDate':start.isoformat(),'endDate':end.isoformat(),'type':'web','dataState':'final','rowLimit':1})
        rows=data.get('rows',[]) if isinstance(data,dict) else None
        if not isinstance(rows,list) or len(rows)>1:raise PerformanceError('invalid response')
        if not rows:results.append(None);continue
        row=rows[0]
        if not isinstance(row,dict):raise PerformanceError('invalid row')
        for key in ('clicks','impressions'):
            v=row.get(key)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise PerformanceError('invalid metric')
        results.append(row)
    if any(r is None for r in results):return {'status':'insufficient_data'}
    return {'status':'available','clicks':direction(results[0]['clicks'],results[1]['clicks']),
            'impressions':direction(results[0]['impressions'],results[1]['impressions'])}

def main():
    if os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_EVENT_NAME') not in ('schedule','workflow_dispatch'):
        print('Performance check blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_WM_GOOGLE_CLIENT_ID','SCM_WM_GOOGLE_CLIENT_SECRET','SCM_WM_GOOGLE_REFRESH_TOKEN')]
    try:
        data=run(creds)
        # Avoid exposing private queries, pages, actual counts or property names in public logs.
        print('::notice title=Google search performance::'+'; '.join(k+'='+v for k,v in data.items())+'; periods=28d_vs_previous_28d; final_data; no_google_writes')
        return 0
    except Exception:
        print('::error title=Google search performance::report_unavailable; no_google_writes',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
