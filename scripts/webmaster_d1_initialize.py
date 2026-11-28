#!/usr/bin/env python3
"""One-time initialization of the dedicated, verified empty D1 database."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from webmaster_d1_diagnostic import NAME, NoRedirect
from webmaster_d1_queue_sql import SCHEMA

UUID=re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z')
MARKER='scm-webmaster-queue-v1'
META_SQL="CREATE TABLE wm_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), marker TEXT NOT NULL)"
INSERT_SQL="INSERT INTO wm_meta(singleton,marker) VALUES (1, 'scm-webmaster-queue-v1')"
OBJECT_SQL="SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
META_READ="SELECT marker FROM wm_meta WHERE singleton=1"
EXPECTED={'wm_cursor','wm_queue','wm_receipts','wm_meta'}
CLOUDFLARE_INTERNAL={'_cf_KV','_cf_METADATA'}
COLUMNS={
    'wm_cursor':[('singleton','INTEGER'),('revision','TEXT')],
    'wm_queue':[('url','TEXT'),('revision','TEXT'),('sent_revision','TEXT'),('state','TEXT'),('task_id','TEXT')],
    'wm_receipts':[('task_id','TEXT'),('url','TEXT'),('revision','TEXT'),('observed_state','TEXT')],
    'wm_meta':[('singleton','INTEGER'),('marker','TEXT')],
}

class InitError(Exception):pass
class UnknownOutcome(InitError):pass


def request_json(url,token,body=None):
    headers={'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'SCM-queue-init/1.0'}
    if body is not None:headers['Content-Type']='application/json'
    req=urllib.request.Request(url,headers=headers,data=None if body is None else json.dumps(body).encode(),method='GET' if body is None else 'POST')
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise InitError('oversized')
        result=json.loads(raw)
        if not isinstance(result,dict) or result.get('success') is not True:raise InitError('invalid response')
        return result
    except (urllib.error.URLError,TimeoutError,OSError,UnicodeError,ValueError):
        raise InitError('request failed') from None


def locate(account,token,*,fetch=request_json):
    root='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database'
    url=root+'?'+urllib.parse.urlencode({'name':NAME,'fields':'name,uuid','page':1,'per_page':100})
    data=fetch(url,token);entries=data.get('result');info=data.get('result_info')
    if not isinstance(entries,list) or not isinstance(info,dict) or len(entries)>=100 or info.get('page')!=1 or info.get('per_page')!=100 or info.get('count')!=len(entries):
        raise InitError('incomplete inventory')
    matches=[x for x in entries if isinstance(x,dict) and x.get('name')==NAME]
    if len(matches)!=1 or not isinstance(matches[0].get('uuid'),str) or not UUID.fullmatch(matches[0]['uuid']):
        raise InitError('database identity ambiguous')
    return root+'/'+matches[0]['uuid']+'/query'


def result_rows(data):
    result=data.get('result') if isinstance(data,dict) else None
    if not isinstance(result,list) or len(result)!=1 or not isinstance(result[0],dict) or result[0].get('success') is not True or not isinstance(result[0].get('results'),list):
        raise InitError('unexpected query result')
    return result[0]['results']


def initialize(account,token,*,fetch=request_json, locate_db=locate):
    if not isinstance(account,str) or not re.fullmatch(r'[a-fA-F0-9]{32}',account) or not isinstance(token,str) or not token or '\n' in token or '\r' in token:
        raise InitError('invalid configuration')
    url=locate_db(account,token,fetch=fetch)
    # locate() constructs only a verified Cloudflare account and UUID endpoint.
    prefix='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database/'
    if not isinstance(url,str) or not url.startswith(prefix) or not url.endswith('/query') or not UUID.fullmatch(url[len(prefix):-len('/query')]):
        raise InitError('invalid database endpoint')
    def read_objects():
        rows=result_rows(fetch(url,token,{'sql':OBJECT_SQL}))
        if any(not isinstance(x,dict) or not isinstance(x.get('name'),str) or x.get('type') not in ('table','index','view','trigger') for x in rows):
            raise InitError('invalid schema list')
        return {(x['name'],x['type']) for x in rows if x['name'] not in CLOUDFLARE_INTERNAL}
    def verify_columns():
        for table, expected_columns in COLUMNS.items():
            rows=result_rows(fetch(url,token,{'sql':'PRAGMA table_info('+table+')'}))
            actual=[(x.get('name'),x.get('type')) for x in rows if isinstance(x,dict)]
            if len(actual)!=len(rows) or actual!=expected_columns:raise InitError('unexpected columns')
    objects=read_objects()
    expected={(name,'table') for name in EXPECTED}
    if objects:
        if objects!=expected:raise InitError('nonempty or unexpected schema')
        verify_columns()
        rows=result_rows(fetch(url,token,{'sql':META_READ}))
        if rows != [{'marker':MARKER}]:raise InitError('ownership marker missing')
        return 'already_initialized'
    # Never retry a mutating batch. Any subsequent failure is ambiguous.
    try:
        batch=[{'sql':sql} for sql in (*SCHEMA,META_SQL,INSERT_SQL)]
        data=fetch(url,token,{'batch':batch})
        results=data.get('result')
        if not isinstance(results,list) or len(results)!=len(batch) or any(not isinstance(x,dict) or x.get('success') is not True for x in results):
            raise InitError('batch not confirmed')
        if read_objects()!=expected:raise InitError('schema verification failed')
        verify_columns()
        if result_rows(fetch(url,token,{'sql':META_READ})) != [{'marker':MARKER}]:raise InitError('marker verification failed')
        return 'initialized'
    except Exception:
        raise UnknownOutcome('inspect schema before any retry') from None


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388' or
        os.environ.get('CONFIRMATION')!='INIT_SEPARATE_QUEUE'):
        print('Initialization blocked.',file=sys.stderr);return 1
    account=os.environ.pop('CLOUDFLARE_ACCOUNT_ID','');token=os.environ.pop('CLOUDFLARE_API_TOKEN','')
    try:
        result=initialize(account,token)
        print('::notice title=D1 queue schema::'+result)
        print('Схема пустой отдельной очереди проверена; переобход не запущен.')
        return 0
    except UnknownOutcome:
        print('::error title=D1 queue schema::unknown_outcome_do_not_retry');return 1
    except Exception:
        print('::error title=D1 queue schema::preflight_failed_no_schema_write');return 1
if __name__=='__main__':sys.exit(main())
