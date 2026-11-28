#!/usr/bin/env python3
"""Bounded read-only indexed-version inspection; never requests indexing."""
import json
import os
import sys
import urllib.error
import urllib.request
from webmaster_actions import SITE, DOMAIN_PROPERTY, GOOGLE_API
from webmaster_google_diagnostic import inspect
from webmaster_after_deploy import refresh_google
from webmaster_readonly import NoRedirect

ENDPOINT='https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
URLS=(SITE, SITE+'wiki.html', SITE+'scm-metrics.html', SITE+'scm-knowledge.html', SITE+'scm-academy.html')

class InspectionError(Exception): pass


def request(token,url,property_name):
    if (url not in URLS or property_name not in (SITE,DOMAIN_PROPERTY) or not isinstance(token,str)
        or not token or '\r' in token or '\n' in token):raise InspectionError('invalid request')
    body=json.dumps({'inspectionUrl':url,'siteUrl':property_name,'languageCode':'en-US'}).encode()
    req=urllib.request.Request(ENDPOINT,data=body,method='POST',headers={'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise InspectionError('response too large')
        value=json.loads(raw)
        if not isinstance(value,dict):raise InspectionError('invalid response')
        return value
    except (urllib.error.URLError,TimeoutError,OSError,UnicodeError,ValueError):
        raise InspectionError('inspection unavailable') from None


def inspect_pages(creds,*,diagnostic=inspect,refresh=refresh_google,call=request):
    result=diagnostic(*creds)
    if result.get('status')!='connected' or result.get('property_type') not in ('url_prefix','domain'):raise InspectionError('property unavailable')
    prop=SITE if result['property_type']=='url_prefix' else DOMAIN_PROPERTY
    token=refresh(*creds)
    pages=[]
    for url in URLS:
        try:
            data=call(token,url,prop)['inspectionResult']['indexStatusResult']
            if not isinstance(data,dict):raise InspectionError('invalid status')
            verdict=data.get('verdict')
            if verdict not in ('PASS','FAIL','NEUTRAL','PARTIAL','VERDICT_UNSPECIFIED'):verdict='UNKNOWN'
            coverage=data.get('coverageState')
            # No logs of arbitrary provider-supplied strings, links or canonicals.
            if not isinstance(coverage,str) or not 0<len(coverage)<=160 or any(ord(c)<32 or ord(c)>126 for c in coverage):coverage='UNKNOWN'
            pages.append({'url':url,'verdict':verdict,'coverage':coverage})
        except Exception:
            pages.append({'url':url,'verdict':'UNKNOWN','coverage':'UNKNOWN'})
            # Unavailability or quota could affect remaining requests. Stop without retries.
            break
    return pages


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Inspection blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_WM_GOOGLE_CLIENT_ID','SCM_WM_GOOGLE_CLIENT_SECRET','SCM_WM_GOOGLE_REFRESH_TOKEN')]
    try:
        pages=inspect_pages(creds)
        for item in pages:print(json.dumps(item,ensure_ascii=True))
        print('::notice title=Google URL inspection::checked='+str(len(pages))+'; unknown='+str(sum(x['verdict']=='UNKNOWN' for x in pages))+'; indexing_requests=0')
        return 0 if len(pages)==len(URLS) and all(x['verdict']!='UNKNOWN' for x in pages) else 1
    except Exception:
        print('::error title=Google URL inspection::inspection_unavailable; indexing_requests=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
