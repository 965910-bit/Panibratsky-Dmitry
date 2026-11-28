#!/usr/bin/env python3
"""Inspect availability of a separately named D1 queue database, without writes."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

NAME='scm-webmaster-queue'

class DiagnosticError(Exception):pass
class HttpStatus(DiagnosticError):
    def __init__(self,status):
        super().__init__('http failure')
        self.status=status
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):return None


def request(account, token, page):
    if not re.fullmatch(r'[a-fA-F0-9]{32}',account or '') or not token or '\r' in token or '\n' in token:
        raise DiagnosticError('invalid credentials')
    url='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database?'+urllib.parse.urlencode({'name':NAME,'fields':'name','page':page,'per_page':100})
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'SCM-queue-diagnostic/1.0'},method='GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:
            raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise DiagnosticError('response too large')
        obj=json.loads(raw)
        if not isinstance(obj,dict):raise DiagnosticError('invalid response')
        return obj
    except urllib.error.HTTPError as exc:
        raise HttpStatus(exc.code) from None
    except (urllib.error.URLError,TimeoutError,OSError,UnicodeError,ValueError):
        raise DiagnosticError('Cloudflare read failed') from None


def inspect(account,token,*,read=request):
    if not account and not token:return 'not_configured'
    if not re.fullmatch(r'[a-fA-F0-9]{32}',account or '') or not isinstance(token,str) or not token or '\r' in token or '\n' in token:
        raise DiagnosticError('incomplete configuration')
    for page in range(1,11):
        data=read(account,token,page)
        entries=data.get('result');info=data.get('result_info')
        if data.get('success') is not True or not isinstance(entries,list) or not isinstance(info,dict) or len(entries)>100:
            raise DiagnosticError('invalid response')
        if any(not isinstance(x,dict) or not isinstance(x.get('name'),str) for x in entries):
            raise DiagnosticError('invalid database entry')
        if any(x['name']==NAME for x in entries):return 'separate_queue_exists'
        pages=info.get('total_pages')
        if type(pages) is not int or pages < 0 or pages < page and pages != 0:
            raise DiagnosticError('invalid pagination')
        if page>=pages:return 'separate_queue_not_found'
    raise DiagnosticError('pagination limit exceeded')


def main():
    account=os.environ.pop('CLOUDFLARE_ACCOUNT_ID','');token=os.environ.pop('CLOUDFLARE_API_TOKEN','')
    try:
        result=inspect(account,token)
        print('::notice title=D1 queue storage preflight::'+result)
        print('Проверка только читает метаданные; не создаёт базы и не включает очередь.')
        return 0
    except HttpStatus as exc:
        status=str(exc.status) if type(exc.status) is int and 100<=exc.status<=599 else 'unknown'
        print('::error title=D1 queue storage preflight::http='+status)
        return 1
    except DiagnosticError as exc:
        known=('incomplete configuration','Cloudflare read failed','invalid response','invalid database entry','invalid pagination','pagination limit exceeded')
        reason=str(exc) if str(exc) in known else 'unavailable_or_unverified'
        print('::error title=D1 queue storage preflight::'+reason)
        return 1
    except Exception:
        print('::error title=D1 queue storage preflight::unavailable_or_unverified')
        print('Не удалось проверить хранилище; существующие базы не изменены.',file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
