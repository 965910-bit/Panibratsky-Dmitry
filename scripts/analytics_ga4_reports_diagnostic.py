#!/usr/bin/env python3
"""Bounded GA4 reports diagnostic: reads aggregate rows, never logs counts or visitor data."""
import json
import os
import sys
import urllib.error
import urllib.request
from analytics_ga4_diagnostic import GOALS, PROPERTY, AnalyticsError, inventory
from webmaster_after_deploy import refresh_google
from webmaster_readonly import NoRedirect

API='https://analyticsdata.googleapis.com/v1beta/'
class ReportError(Exception):
    def __init__(self, stage): self.stage=stage

def request(prop,token,method,body):
    if not PROPERTY.fullmatch(prop) or method not in ('runReport','runRealtimeReport'):
        raise ReportError('invalid_request')
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:raise ReportError('invalid_token')
    req=urllib.request.Request(API+prop+':'+method,method='POST',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ReportError('invalid_response')
        data=json.loads(raw)
        if not isinstance(data,dict):raise ReportError('invalid_response')
        return data
    except urllib.error.HTTPError as error:
        # Expose only documented reason enums; discard descriptions, IDs and URLs.
        reason='unknown'
        if error.code==403:
            try:
                payload=json.loads(error.read(65537))
                details=payload.get('error',{}).get('details',[])
                allowed={'SERVICE_DISABLED','ACCESS_TOKEN_SCOPE_INSUFFICIENT','PERMISSION_DENIED','RATE_LIMIT_EXCEEDED','QUOTA_EXCEEDED','CONSUMER_INVALID'}
                candidates=[x.get('reason') for x in details if isinstance(x,dict) and x.get('reason') in allowed]
                if len(set(candidates))==1:reason=candidates[0].lower()
            except (ValueError,TypeError,AttributeError,OSError):pass
        code=error.code
        status='http_'+str(code) if code in (400,401,403,404,429,500,503) else 'http_other'
        raise ReportError(status+'_'+reason if code==403 else status) from None
    except (urllib.error.URLError,TimeoutError,OSError,ValueError):raise ReportError('network_or_response') from None

def inspect(admin_creds,report_creds,*,identify=inventory,refresh=refresh_google,fetch=request):
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in (*admin_creds,*report_creds)):raise ReportError('missing_credentials')
    info=identify(*admin_creds,include_private=True)
    if not info.get('domain_matches') or not PROPERTY.fullmatch(info.get('property','')):raise ReportError('identity_mismatch')
    prop=info['property'];token=refresh(*report_creds)
    body={'dateRanges':[{'startDate':'28daysAgo','endDate':'yesterday'}],
          'dimensions':[{'name':'eventName'}],'metrics':[{'name':'eventCount'}],
          'dimensionFilter':{'filter':{'fieldName':'eventName','inListFilter':{'values':list(GOALS)+['page_view']}}},'limit':'100'}
    result=fetch(prop,token,'runReport',body)
    rows=result.get('rows',[])
    if not isinstance(rows,list) or len(rows)>len(GOALS)+1:raise ReportError('invalid_rows')
    names=[]
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('dimensionValues'),list) or len(row['dimensionValues'])!=1:raise ReportError('invalid_rows')
        name=row['dimensionValues'][0].get('value') if isinstance(row['dimensionValues'][0],dict) else None
        values=row.get('metricValues')
        if name not in (*GOALS,'page_view') or name in names or not isinstance(values,list) or len(values)!=1 or not isinstance(values[0],dict):raise ReportError('invalid_rows')
        count=values[0].get('value')
        if not isinstance(count,str) or not count.isascii() or not count.isdigit() or len(count)>20:raise ReportError('invalid_count')
        if int(count)>0:names.append(name)
    # Metadata flags indicate limitations, not permission to treat missing events as zero.
    metadata=result.get('metadata',{})
    if not isinstance(metadata,dict):raise ReportError('invalid_metadata')
    threshold=metadata.get('subjectToThresholding',False)
    if type(threshold) is not bool:raise ReportError('invalid_metadata')
    sampling=metadata.get('samplingMetadatas',[])
    if not isinstance(sampling,list):raise ReportError('invalid_metadata')
    return {'observed':[n for n in GOALS if n in names],'page_view_observed':'page_view' in names,'thresholded':threshold,'sampled':bool(sampling)}

def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Report diagnostic blocked.',file=sys.stderr);return 1
    admin=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    report=[os.environ.pop(k,'') for k in ('SCM_GA4_REPORT_CLIENT_ID','SCM_GA4_REPORT_CLIENT_SECRET','SCM_GA4_REPORT_REFRESH_TOKEN')]
    try:
        result=inspect(admin,report)
        print('::notice title=GA4 report diagnostic::connected; known_events_observed='+str(len(result['observed']))+'; page_view_observed='+str(result['page_view_observed']).lower()+'; thresholded='+str(result['thresholded']).lower()+'; sampled='+str(result['sampled']).lower()+'; period=28daysAgo_to_yesterday; writes=0')
        print('::notice title=GA4 observed project events::'+(','.join(result['observed']) or 'none'))
        return 0
    except ReportError as exc:
        print('::error title=GA4 report diagnostic::'+exc.stage+'; writes=0',file=sys.stderr);return 1
    except Exception:
        print('::error title=GA4 report diagnostic::authorization_or_identity_failed; writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
