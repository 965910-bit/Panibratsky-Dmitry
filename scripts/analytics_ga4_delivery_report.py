#!/usr/bin/env python3
"""Read only a synthetic, non-key GA4 event in the realtime report."""
import os
import sys
import time
from analytics_ga4_diagnostic import AnalyticsError, PROPERTY, inventory, pages
from analytics_ga4_reports_diagnostic import request
from webmaster_after_deploy import refresh_google

EVENT='scm_delivery_test'

def status(admin, report, *, identify=inventory, list_pages=pages, refresh=refresh_google, fetch=request):
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in (*admin,*report)):raise AnalyticsError('missing credentials')
    info=identify(*admin,include_private=True)
    prop=info.get('property','')
    if not info.get('domain_matches') or not PROPERTY.fullmatch(prop):raise AnalyticsError('identity mismatch')
    configured=list_pages(prop+'/keyEvents','keyEvents',info['token'])
    if any(not isinstance(e,dict) or not isinstance(e.get('eventName'),str) for e in configured):raise AnalyticsError('invalid events')
    if any(e['eventName']==EVENT for e in configured):raise AnalyticsError('synthetic event is key event')
    token=refresh(*report)
    body={'dimensions':[{'name':'eventName'}],'metrics':[{'name':'eventCount'}],
          'dimensionFilter':{'filter':{'fieldName':'eventName','stringFilter':{'matchType':'EXACT','value':EVENT}}},'limit':'2'}
    result=fetch(prop,token,'runRealtimeReport',body)
    rows=result.get('rows',[])
    if not isinstance(rows,list) or len(rows)>1:raise AnalyticsError('invalid report')
    if not rows:return False
    row=rows[0]
    if not isinstance(row,dict):raise AnalyticsError('invalid row')
    dims=row.get('dimensionValues');vals=row.get('metricValues')
    if not isinstance(dims,list) or len(dims)!=1 or not isinstance(dims[0],dict) or dims[0].get('value')!=EVENT:raise AnalyticsError('invalid dimension')
    if not isinstance(vals,list) or len(vals)!=1 or not isinstance(vals[0],dict):raise AnalyticsError('invalid count')
    n=vals[0].get('value')
    if not isinstance(n,str) or not n.isascii() or not n.isdigit() or len(n)>20:raise AnalyticsError('invalid count')
    return int(n)>0

def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    admin=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    report=[os.environ.pop(k,'') for k in ('SCM_GA4_REPORT_CLIENT_ID','SCM_GA4_REPORT_CLIENT_SECRET','SCM_GA4_REPORT_REFRESH_TOKEN')]
    try:
        mode=sys.argv[1]
        if mode=='before':
            if status(admin,report):
                print('::warning title=GA4 delivery::test_already_in_realtime; no_test_sent');return 2
            print('::notice title=GA4 delivery::baseline_absent; no_test_sent');return 0
        if mode=='after':
            for attempt in range(6):
                if status(admin,report):
                    print('::notice title=GA4 delivery::synthetic_event_observed_in_realtime; not_a_goal; actual_goal_delivery_not_proven');return 0
                if attempt<5:time.sleep(20)
            print('::warning title=GA4 delivery::synthetic_event_not_observed_within_window; outcome_inconclusive');return 0
        return 1
    except Exception:
        print('::error title=GA4 delivery::report_or_identity_failed; delivery_unknown',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
