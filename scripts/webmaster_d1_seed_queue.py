#!/usr/bin/env python3
"""One-time seed of a dedicated D1 queue from a verified production deployment.

Never calls Yandex. A mutating batch may have succeeded on timeout; do not retry
without independently inspecting cursor and queue. No scheduling or sending.
"""
import json
import os
import re
import sys
import indexnow_submit as ix
from webmaster_deployment_cursor import is_ancestor, changed_canonical
from webmaster_d1_queue_sql import deployment_batch
from webmaster_d1_initialize import (request_json,locate,result_rows,EXPECTED,COLUMNS,
                                     OBJECT_SQL,META_READ,MARKER,CLOUDFLARE_INTERNAL)
from webmaster_queue_prepare import REPOSITORY_ID

# The REST batch endpoint's atomicity and isolation have not yet been verified.
# Keep the production entry point disabled until the exact integration is proven.
REST_BATCH_VERIFIED = False

class SeedError(Exception):pass
class UnknownOutcome(SeedError):pass


def seed(account,token,repo,github_token,baseline,*,git=ix.git,gh_fetch=ix.request,
         live=ix.validate_live,ancestor=is_ancestor,changed=changed_canonical,
         cf=request_json,locate_db=locate):
    if not isinstance(account,str) or not re.fullmatch(r'[a-fA-F0-9]{32}',account) or not isinstance(token,str) or not token or '\n' in token or '\r' in token:
        raise SeedError('invalid Cloudflare configuration')
    if not isinstance(repo,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not isinstance(github_token,str) or not github_token or '\n' in github_token or '\r' in github_token:
        raise SeedError('invalid GitHub configuration')
    if not isinstance(baseline,str) or not re.fullmatch(r'[a-f0-9]{40}',baseline):raise SeedError('invalid baseline')
    sha=git('rev-parse','HEAD')
    if not isinstance(sha,str) or not re.fullmatch(r'[a-f0-9]{40}',sha):raise SeedError('invalid checkout')
    root='https://api.github.com/repos/'+repo
    def gh(path):
        status,_,body=gh_fetch(root+path,token=github_token)
        if status!=200:raise SeedError('GitHub unavailable')
        result=json.loads(body)
        if not isinstance(result,dict):raise SeedError('invalid response')
        return result
    if gh('').get('id')!=REPOSITORY_ID:raise SeedError('wrong repository')
    def main_sha():
        try:return gh('/git/ref/heads/main')['object']['sha']
        except (KeyError,TypeError):raise SeedError('invalid main') from None
    if main_sha()!=sha:raise SeedError('checkout stale')
    build=gh('/pages/builds/latest')
    if build.get('status')!='built' or build.get('commit')!=sha:raise SeedError('Pages stale')
    if baseline!=sha and not ancestor(baseline,sha):raise SeedError('baseline not ancestor')
    urls=list(changed(baseline,sha)) if baseline!=sha else []
    batch=deployment_batch(baseline,sha,urls) # validates URLs and duplicates before any D1 action
    live([])
    if main_sha()!=sha:raise SeedError('main advanced')
    url=locate_db(account,token,fetch=cf)
    prefix='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database/'
    from webmaster_d1_initialize import UUID
    if not isinstance(url,str) or not url.startswith(prefix) or not url.endswith('/query') or not UUID.fullmatch(url[len(prefix):-len('/query')]):
        raise SeedError('invalid database endpoint')
    def query(sql,params=None):
        body={'sql':sql}
        if params is not None:body['params']=params
        return result_rows(cf(url,token,body))
    objects=query(OBJECT_SQL)
    if any(not isinstance(x,dict) or not isinstance(x.get('name'),str) or x.get('type') not in ('table','index','view','trigger') for x in objects):raise SeedError('invalid schema')
    actual={(x['name'],x['type']) for x in objects if x['name'] not in CLOUDFLARE_INTERNAL}
    if actual!={(name,'table') for name in EXPECTED}:raise SeedError('unexpected schema')
    for table, expected in COLUMNS.items():
        cols=query('PRAGMA table_info('+table+')')
        if any(not isinstance(x,dict) for x in cols) or [(x.get('name'),x.get('type')) for x in cols]!=expected:raise SeedError('unexpected columns')
    if query(META_READ)!=[{'marker':MARKER}]:raise SeedError('marker missing')
    cursors=query('SELECT revision FROM wm_cursor WHERE singleton=1')
    if cursors:
        if cursors==[{'revision':sha}]:return {'status':'already_current','queued':None}
        raise SeedError('cursor already initialized; no seed')
    if query('SELECT count(*) AS n FROM wm_queue')!=[{'n':0}] or query('SELECT count(*) AS n FROM wm_receipts')!=[{'n':0}]:
        raise SeedError('database not empty')
    if main_sha()!=sha:raise SeedError('main advanced')
    # One guarded D1 batch: cursor initialization only if genuinely empty,
    # followed by CAS enqueue and cursor advance. No automatic retries.
    init=("INSERT INTO wm_cursor(singleton,revision) SELECT 1,? WHERE NOT EXISTS (SELECT 1 FROM wm_cursor) AND NOT EXISTS (SELECT 1 FROM wm_queue) AND NOT EXISTS (SELECT 1 FROM wm_receipts)",[baseline])
    statements=[init]+batch
    payload={'batch':[{'sql':sql,'params':params} for sql,params in statements]}
    try:
        response=cf(url,token,payload);results=response.get('result') if isinstance(response,dict) else None
        if not isinstance(results,list) or len(results)!=len(statements) or any(not isinstance(x,dict) or x.get('success') is not True for x in results):raise SeedError('batch unconfirmed')
        if results[-1].get('results') != [{'revision':sha}]:raise SeedError('cursor CAS failed')
        if query('SELECT revision FROM wm_cursor WHERE singleton=1') != [{'revision':sha}]:raise SeedError('cursor unconfirmed')
        if query("SELECT count(*) AS n FROM wm_queue WHERE state='pending'") != [{'n':len(urls)}]:raise SeedError('queue count unconfirmed')
        return {'status':'seeded','queued':len(urls)}
    except Exception:
        raise UnknownOutcome('inspect database before any retry') from None


def main():
    if not REST_BATCH_VERIFIED:
        print('::error title=D1 queue seed::rest_batch_unverified_no_seed');return 1
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388' or
        os.environ.get('CONFIRMATION')!='SEED_VERIFIED_QUEUE'):
        print('Seed blocked.',file=sys.stderr);return 1
    account=os.environ.pop('CLOUDFLARE_ACCOUNT_ID','');token=os.environ.pop('CLOUDFLARE_API_TOKEN','');gh=os.environ.pop('GITHUB_TOKEN','')
    try:
        result=seed(account,token,os.environ.get('GITHUB_REPOSITORY',''),gh,os.environ.get('BASELINE',''))
        print('::notice title=D1 queue seed::'+result['status']+'; queued='+str(result['queued'] if result['queued'] is not None else 'unknown')+'; yandex_requests=0')
        return 0
    except UnknownOutcome:
        print('::error title=D1 queue seed::unknown_outcome_do_not_retry');return 1
    except Exception:
        print('::error title=D1 queue seed::preflight_failed_no_seed');return 1
if __name__=='__main__':sys.exit(main())
