#!/usr/bin/env python3
"""One manual, bounded creation of the dedicated queue database; no schema or provider writes."""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from webmaster_d1_diagnostic import NAME, NoRedirect, DiagnosticError, request as read_page

class ProvisionError(Exception):pass
class UnknownOutcome(ProvisionError):pass


def create(account,token):
    # Caller validates account and token. No retries: any failure may follow creation.
    url='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database'
    req=urllib.request.Request(url,data=json.dumps({'name':NAME}).encode(),method='POST',headers={
        'Authorization':'Bearer '+token,'Accept':'application/json','Content-Type':'application/json','User-Agent':'SCM-queue-provision/1.0'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:
            raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise UnknownOutcome('oversized response')
        data=json.loads(raw)
        result=data.get('result') if isinstance(data,dict) else None
        if (data.get('success') is not True or not isinstance(result,dict) or result.get('name')!=NAME or
            not isinstance(result.get('uuid'),str) or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',result['uuid'])):
            raise UnknownOutcome('unverified response')
    except (urllib.error.URLError,OSError,TimeoutError,UnicodeError,ValueError,AttributeError):
        raise UnknownOutcome('create not confirmed') from None
    return 'created'


def provision(account,token,*,read=read_page,post=create):
    if not isinstance(account,str) or not re.fullmatch(r'[a-fA-F0-9]{32}',account):raise ProvisionError('invalid configuration')
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:raise ProvisionError('invalid configuration')
    data=read(account,token,1)
    if not isinstance(data,dict):raise ProvisionError('invalid listing')
    entries=data.get('result');info=data.get('result_info')
    if data.get('success') is not True or not isinstance(entries,list) or not isinstance(info,dict):raise ProvisionError('invalid listing')
    if any(not isinstance(x,dict) or not isinstance(x.get('name'),str) for x in entries):raise ProvisionError('invalid listing')
    if any(x['name']==NAME for x in entries):return 'already_exists'
    page,per_page,count,total=info.get('page'),info.get('per_page'),info.get('count'),info.get('total_count')
    if (type(page) is not int or page!=1 or type(per_page) is not int or not 1<=per_page<=100 or
        type(count) is not int or count!=len(entries) or len(entries)>=per_page or
        type(total) is not int or total<0 or total<len(entries)):
        raise ProvisionError('incomplete inventory')
    # Cloudflare documents 10 included databases on Free, 100000 on Paid.
    # Stay below 10 under the observed total; this is not a billing guarantee.
    if total>=9:raise ProvisionError('database count safety limit')
    return post(account,token)


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388' or
        os.environ.get('CONFIRMATION')!='CREATE_SEPARATE_QUEUE'):
        print('Provisioning blocked.',file=sys.stderr);return 1
    account=os.environ.pop('CLOUDFLARE_ACCOUNT_ID','');token=os.environ.pop('CLOUDFLARE_API_TOKEN','')
    try:
        result=provision(account,token)
        print('::notice title=D1 queue provisioning::'+result)
        print('Схема и автоматизация не установлены; данные других баз не менялись.')
        return 0
    except UnknownOutcome:
        print('::error title=D1 queue provisioning::unknown_outcome_do_not_retry')
        return 1
    except (ProvisionError,DiagnosticError):
        print('::error title=D1 queue provisioning::preflight_failed_no_create')
        return 1
    except Exception:
        # An unexpected exception might occur after POST. Never assert no write.
        print('::error title=D1 queue provisioning::unknown_outcome_do_not_retry')
        return 1
if __name__=='__main__':sys.exit(main())
