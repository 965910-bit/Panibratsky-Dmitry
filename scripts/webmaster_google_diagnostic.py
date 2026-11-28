#!/usr/bin/env python3
"""Manual Google Search Console connection check. No Search Console writes."""
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote
from webmaster_actions import api, GOOGLE_API, SITE, DOMAIN_PROPERTY, MAP
from webmaster_after_deploy import refresh_google

class GoogleDiagnosticError(Exception): pass


def sitemap_health(item):
    """Classify conservatively; absent or malformed metadata is not success."""
    errors=item.get('errors')
    if isinstance(errors,str) and errors.isascii() and errors.isdigit() and len(errors)<=18:
        errors=int(errors)
    if type(errors) is not int or errors<0:return 'unknown'
    if errors>0:return 'error'
    pending=item.get('isPending')
    if pending is True:return 'pending'
    if pending is not False:return 'unknown'
    date=item.get('lastDownloaded')
    try:
        if not isinstance(date,str):raise ValueError()
        parsed=datetime.fromisoformat(date.replace('Z','+00:00'))
        if parsed.tzinfo is None or parsed>datetime.now(timezone.utc):raise ValueError()
    except ValueError:return 'unknown'
    return 'healthy'


def inspect(client_id, client_secret, refresh_token, *, refresh=refresh_google, request=api):
    creds=(client_id,client_secret,refresh_token)
    if not any(creds):return {'status':'not_connected'}
    if not all(isinstance(x,str) and x and '\n' not in x and '\r' not in x for x in creds):
        raise GoogleDiagnosticError('incomplete credentials')
    token=refresh(*creds)
    payload=request(GOOGLE_API+'/sites',token,'Bearer')
    entries=payload.get('siteEntry',[]) if isinstance(payload,dict) else None
    if not isinstance(entries,list) or any(not isinstance(x,dict) or not isinstance(x.get('siteUrl'),str) for x in entries):
        raise GoogleDiagnosticError('invalid sites')
    # Prefer the URL-prefix property; never modify or disclose unrelated properties.
    matches=[x for x in entries if x['siteUrl'] in (SITE,DOMAIN_PROPERTY)]
    if not matches:return {'status':'property_missing'}
    if len({x['siteUrl'] for x in matches}) != len(matches):raise GoogleDiagnosticError('ambiguous properties')
    selected=next((x for x in matches if x['siteUrl']==SITE),matches[0])
    permission=selected.get('permissionLevel')
    if permission not in ('siteOwner','siteFullUser','siteRestrictedUser','siteUnverifiedUser'):
        raise GoogleDiagnosticError('unknown permission')
    if permission=='siteUnverifiedUser':return {'status':'unverified','permission':permission}
    prop=selected['siteUrl'];base=GOOGLE_API+'/sites/'+quote(prop,safe='')
    result=request(base+'/sitemaps',token,'Bearer')
    maps=result.get('sitemap',[]) if isinstance(result,dict) else None
    if not isinstance(maps,list) or any(not isinstance(x,dict) or not isinstance(x.get('path'),str) for x in maps):
        raise GoogleDiagnosticError('invalid sitemaps')
    found=[x for x in maps if x['path']==MAP]
    if len(found)>1:raise GoogleDiagnosticError('ambiguous sitemap')
    return {'status':'connected','property_type':'url_prefix' if prop==SITE else 'domain',
            'permission':permission,'sitemap':'present' if found else 'not_listed',
            'sitemap_health':sitemap_health(found[0]) if found else 'missing'}


def main():
    creds=[os.environ.pop(key,'') for key in ('SCM_WM_GOOGLE_CLIENT_ID','SCM_WM_GOOGLE_CLIENT_SECRET','SCM_WM_GOOGLE_REFRESH_TOKEN')]
    try:
        result=inspect(*creds)
        # Deliberately expose only known classifications, never API data or credentials.
        status=result['status']
        parts=['status='+status]
        for key in ('property_type','permission','sitemap','sitemap_health'):
            if key in result:parts.append(key+'='+result[key])
        print('::notice title=Google Search Console::'+'; '.join(parts)+'; writes=0')
        return 0 if status=='connected' else 1
    except Exception:
        print('::error title=Google Search Console::connection_check_failed; writes=0',file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
