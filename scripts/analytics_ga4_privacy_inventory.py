#!/usr/bin/env python3
"""Read exact GA4 stream privacy settings and Ads link count. No writes."""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from analytics_ga4_diagnostic import AnalyticsError, PROPERTY, inventory, pages
from webmaster_readonly import NoRedirect

BASE='https://analyticsadmin.googleapis.com/'

def get(path,token,params=None):
    if not (re.fullmatch(r'v1alpha/properties/[1-9][0-9]{0,19}/dataStreams/[1-9][0-9]{0,19}/(?:enhancedMeasurementSettings|dataRedactionSettings)',path)
            or re.fullmatch(r'v1beta/properties/[1-9][0-9]{0,19}/googleAdsLinks',path)):
        raise AnalyticsError('invalid path')
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:raise AnalyticsError('invalid token')
    url=BASE+path
    if params:url+='?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/json'},method='GET')
    with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as res:raw=res.read(1024*1024+1)
    if len(raw)>1024*1024:raise AnalyticsError('oversized')
    data=json.loads(raw)
    if not isinstance(data,dict):raise AnalyticsError('invalid response')
    return data

def inventory_settings(creds,*,find=inventory,read=get):
    info=find(*creds,include_private=True)
    if not info['domain_matches'] or not PROPERTY.fullmatch(info['property']):raise AnalyticsError('identity mismatch')
    prop,stream,token=info['property'],info['stream'],info['token']
    if not re.fullmatch(re.escape(prop)+r'/dataStreams/[1-9][0-9]{0,19}',stream):raise AnalyticsError('stream mismatch')
    enhanced=read('v1alpha/'+stream+'/enhancedMeasurementSettings',token)
    redact=read('v1alpha/'+stream+'/dataRedactionSettings',token)
    if enhanced.get('name')!=stream+'/enhancedMeasurementSettings' or redact.get('name')!=stream+'/dataRedactionSettings':raise AnalyticsError('settings identity mismatch')
    links=pages('v1beta/'+prop+'/googleAdsLinks','googleAdsLinks',token,fetch=read)
    def flag(obj,key):
        # Absent protobuf booleans are false, but malformed values are unknown.
        val=obj.get(key,False)
        if type(val) is not bool:raise AnalyticsError('invalid flag')
        return val
    return {'ads_links':len(links), 'enhanced':flag(enhanced,'streamEnabled'),
        'search':flag(enhanced,'siteSearchEnabled'),'forms':flag(enhanced,'formInteractionsEnabled'),
        'outbound':flag(enhanced,'outboundClicksEnabled'), 'downloads':flag(enhanced,'fileDownloadsEnabled'),
        'email_redaction':flag(redact,'emailRedactionEnabled'), 'query_redaction':flag(redact,'queryParameterRedactionEnabled')}

def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Inventory blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        data=inventory_settings(creds)
        print('::notice title=GA4 settings inventory::'+'; '.join(k+'='+str(v).lower() for k,v in data.items())+'; writes=0')
        return 0
    except Exception:
        print('::error title=GA4 settings inventory::read_or_identity_failed; writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
