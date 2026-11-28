#!/usr/bin/env python3
"""Read whether the previously sent non-key synthetic event appears in GA4 history."""
import os,sys
from analytics_ga4_diagnostic import inventory,PROPERTY
from analytics_ga4_reports_diagnostic import request
from webmaster_after_deploy import refresh_google
class Error(Exception):pass

def inspect(admin,report,*,identify=inventory,refresh=refresh_google,fetch=request):
 info=identify(*admin,include_private=True);prop=info.get('property','')
 if not info.get('domain_matches') or not isinstance(prop,str) or not PROPERTY.fullmatch(prop):raise Error('identity')
 if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in report):raise Error('credentials')
 body={'dateRanges':[{'startDate':'28daysAgo','endDate':'yesterday'}],'dimensions':[{'name':'eventName'}],'metrics':[{'name':'eventCount'}], 'dimensionFilter':{'filter':{'fieldName':'eventName','stringFilter':{'matchType':'EXACT','value':'scm_delivery_test'}}},'limit':'2'}
 result=fetch(prop,refresh(*report),'runReport',body);rows=result.get('rows',[]);metadata=result.get('metadata',{})
 if not isinstance(rows,list) or len(rows)>1 or not isinstance(metadata,dict):raise Error('rows')
 threshold=metadata.get('subjectToThresholding',False);sampling=metadata.get('samplingMetadatas',[])
 if type(threshold) is not bool or not isinstance(sampling,list):raise Error('metadata')
 if not rows:return False,threshold,bool(sampling)
 row=rows[0]
 if not isinstance(row,dict):raise Error('row')
 d=row.get('dimensionValues');v=row.get('metricValues')
 if not isinstance(d,list) or len(d)!=1 or not isinstance(d[0],dict) or d[0].get('value')!='scm_delivery_test' or not isinstance(v,list) or len(v)!=1 or not isinstance(v[0],dict):raise Error('row')
 n=v[0].get('value')
 if not isinstance(n,str) or not n.isascii() or not n.isdigit() or len(n)>18:raise Error('count')
 return int(n)>0,threshold,bool(sampling)

def main():
 if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
 def credentials(prefix):return [os.environ.pop(prefix+n,'') for n in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN')]
 try:
  seen,threshold,sampled=inspect(credentials('SCM_GA4_'),credentials('SCM_GA4_REPORT_'))
  print(f'::notice title=GA4 synthetic historical report::synthetic_observed={str(seen).lower()}; thresholded={str(threshold).lower()}; sampled={str(sampled).lower()}; missing_is_not_zero; no_event_sent; actual_goals_unverified');return 0
 except Exception:
  print('::error title=GA4 synthetic historical report::read_failed; no_event_sent',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
