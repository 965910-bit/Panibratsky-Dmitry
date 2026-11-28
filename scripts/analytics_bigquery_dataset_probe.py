#!/usr/bin/env python3
"""Read only GA4 export dataset metadata, never issue a query or reveal project IDs."""
import json,os,re,sys,urllib.error,urllib.request
from analytics_ga4_diagnostic import AnalyticsError,PROPERTY,inventory,pages
from analytics_ga4_products_inventory import get
from webmaster_readonly import NoRedirect
from webmaster_after_deploy import refresh_google

class ProbeError(Exception):pass

def probe(creds,bq_creds,*,identify=inventory,read_pages=pages,fetch=get,open_url=None,refresh=refresh_google):
    info=identify(*creds,include_private=True)
    prop=info.get('property','')
    if not info.get('domain_matches') or not isinstance(prop,str) or not PROPERTY.fullmatch(prop):raise ProbeError('identity')
    links=read_pages('v1alpha/'+prop+'/bigQueryLinks','bigqueryLinks',info['token'],fetch=fetch)
    if len(links)!=1:return 'no_unique_link'
    project=links[0].get('project','')
    # The API returns the canonical project number. Refuse arbitrary URLs/IDs.
    if not isinstance(project,str) or not re.fullmatch(r'projects/[1-9][0-9]{0,19}',project):raise ProbeError('invalid_project')
    dataset='analytics_'+prop.split('/')[1]
    url='https://bigquery.googleapis.com/bigquery/v2/'+project+'/datasets/'+dataset
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in bq_creds):return 'separate_bq_credentials_missing'
    token=refresh(*bq_creds)
    if not isinstance(token,str) or not token or '\r' in token or '\n' in token:raise ProbeError('token')
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/json'},method='GET')
    try:
        with (open_url or urllib.request.build_opener(NoRedirect).open)(req,timeout=20) as response:raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ProbeError('oversized')
        data=json.loads(raw)
        ref=data.get('datasetReference',{}) if isinstance(data,dict) else {}
        if not isinstance(ref,dict) or ref.get('datasetId')!=dataset:raise ProbeError('dataset_mismatch')
        return 'metadata_accessible'
    except urllib.error.HTTPError as error:
        # Never print API error bodies, project numbers, tokens, or dataset contents.
        return {401:'unauthorized',403:'access_or_scope_or_service_denied',404:'not_found_or_hidden',429:'rate_limited'}.get(error.code,'http_other')
    except (urllib.error.URLError,TimeoutError,OSError,ValueError):raise ProbeError('read_failed') from None

def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        bq=[os.environ.pop(k,'') for k in ('SCM_BQ_READ_CLIENT_ID','SCM_BQ_READ_CLIENT_SECRET','SCM_BQ_READ_REFRESH_TOKEN')]
        result=probe(creds,bq)
        print('::notice title=BigQuery dataset metadata::status='+result+'; read_only; no_query; table_export_and_billing_unverified')
        return 0
    except Exception:
        print('::error title=BigQuery dataset metadata::identity_or_read_failed; no_query; no_changes',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
