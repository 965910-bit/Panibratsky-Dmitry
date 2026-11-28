#!/usr/bin/env python3
"""One-time targeted GA4 privacy fix: disable enhanced site-search and outbound-click events."""
import json,os,re,sys,urllib.parse,urllib.request
from analytics_ga4_diagnostic import inventory
from analytics_ga4_privacy_inventory import get
from webmaster_readonly import NoRedirect

class GuardError(Exception):pass

def change(creds,*,identify=inventory,read=get,write=None):
    info=identify(*creds,include_private=True);prop=info.get('property','');stream=info.get('stream','');token=info.get('token','')
    if prop!='properties/531336422' or not info.get('domain_matches') or not info.get('can_edit') or not isinstance(stream,str) or not re.fullmatch(re.escape(prop)+r'/dataStreams/[1-9][0-9]{0,19}',stream):raise GuardError('identity')
    path='v1alpha/'+stream+'/enhancedMeasurementSettings';before=read(path,token)
    if before.get('name')!=stream+'/enhancedMeasurementSettings' or before.get('streamEnabled') is not True or type(before.get('siteSearchEnabled',False)) is not bool:raise GuardError('settings')
    if type(before.get('outboundClicksEnabled',False)) is not bool:raise GuardError('settings')
    if not before.get('siteSearchEnabled',False) and not before.get('outboundClicksEnabled',False):return 'already_disabled'
    if write is None:
        def write(path,token):
            url='https://analyticsadmin.googleapis.com/'+path+'?'+urllib.parse.urlencode({'updateMask':'siteSearchEnabled,outboundClicksEnabled'})
            body=json.dumps({'siteSearchEnabled':False,'outboundClicksEnabled':False}).encode()
            req=urllib.request.Request(url,data=body,method='PATCH',headers={'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json'})
            with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise GuardError('oversized')
            return json.loads(raw)
    # If this call fails or times out, state is uncertain: do not automatically retry.
    result=write(path,token)
    if not isinstance(result,dict) or result.get('name')!=stream+'/enhancedMeasurementSettings' or (result.get('siteSearchEnabled',False) is not False or result.get('outboundClicksEnabled',False) is not False):raise GuardError('write_unconfirmed')
    after=read(path,token)
    if after.get('name')!=before['name'] or (after.get('siteSearchEnabled',False) is not False or after.get('outboundClicksEnabled',False) is not False):raise GuardError('readback')
    others=set(before)|set(after);others.discard('siteSearchEnabled');others.discard('outboundClicksEnabled')
    if any(before.get(k)!=after.get(k) for k in others):raise GuardError('other_settings_changed')
    return 'disabled_and_read_back'

def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    try:
        print('::notice title=GA4 automatic privacy setting::'+change(creds)+'; automatic_search_and_outbound_disabled_stream_wide; other_settings_unchanged');return 0
    except Exception:
        print('::error title=GA4 automatic privacy setting::failed_or_uncertain; do_not_retry_without_readback',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
