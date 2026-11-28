#!/usr/bin/env python3
"""One-shot REST rollback probe in the dedicated queue database, never contacts Yandex.

A partial or ambiguous result must be inspected manually, never retried blindly.
An observed rollback is evidence about this execution, not a provider guarantee.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from webmaster_d1_initialize import (request_json, locate, result_rows, UUID, OBJECT_SQL,
    META_READ, MARKER, EXPECTED, COLUMNS, CLOUDFLARE_INTERNAL)
from webmaster_d1_diagnostic import NoRedirect

PROBE = 'wm_rest_rollback_probe'
BATCH = {'batch': [
    {'sql': 'CREATE TABLE wm_rest_rollback_probe (id INTEGER PRIMARY KEY)'},
    {'sql': 'INSERT INTO wm_rest_rollback_probe(id) VALUES (1)'},
    {'sql': 'INSERT INTO wm_rest_rollback_probe(id) VALUES (1)'},
]}

class ProbeError(Exception): pass
class UnknownOutcome(ProbeError): pass


def failing_request(url, token, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST', headers={
        'Authorization': 'Bearer '+token, 'Accept': 'application/json',
        'Content-Type': 'application/json', 'User-Agent': 'SCM-queue-probe/1.0'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as response:
            raw = response.read(1048577)
    except urllib.error.HTTPError as exc:
        raw = exc.read(1048577)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise UnknownOutcome('network') from None
    try:
        if len(raw) > 1048576: raise ValueError()
        data = json.loads(raw)
        errors = data.get('errors') if isinstance(data, dict) else None
        if data.get('success') is not False or not isinstance(errors, list): raise ValueError()
        # Only a concrete constraint failure qualifies; never echo provider errors.
        if not any(isinstance(e, dict) and isinstance(e.get('message'), str) and
                   re.search(r'UNIQUE constraint failed:\s*wm_rest_rollback_probe\.id', e['message'], re.I)
                   for e in errors): raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise UnknownOutcome('unconfirmed failure') from None


def probe(account, token, *, fetch=request_json, locate_db=locate, fail=failing_request):
    if not isinstance(account, str) or not re.fullmatch(r'[a-fA-F0-9]{32}', account) or not isinstance(token,str) or not token or '\n' in token or '\r' in token:
        raise ProbeError('invalid configuration')
    url=locate_db(account, token, fetch=fetch)
    prefix='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database/'
    if not isinstance(url,str) or not url.startswith(prefix) or not url.endswith('/query') or not UUID.fullmatch(url[len(prefix):-len('/query')]):
        raise ProbeError('invalid endpoint')
    def query(sql): return result_rows(fetch(url,token,{'sql':sql}))
    def objects():
        rows=query(OBJECT_SQL)
        if any(not isinstance(x,dict) or not isinstance(x.get('name'),str) or x.get('type') not in ('table','index','view','trigger') for x in rows): raise ProbeError('invalid schema')
        return {(x['name'],x['type']) for x in rows if x['name'] not in CLOUDFLARE_INTERNAL}
    expected={(name,'table') for name in EXPECTED}
    if objects()!=expected or query(META_READ)!=[{'marker':MARKER}]: raise ProbeError('wrong schema')
    for table, cols in COLUMNS.items():
        rows=query('PRAGMA table_info('+table+')')
        if any(not isinstance(x,dict) for x in rows) or [(x.get('name'),x.get('type')) for x in rows]!=cols: raise ProbeError('wrong columns')
    for table in ('wm_cursor','wm_queue','wm_receipts'):
        if query('SELECT count(*) AS n FROM '+table)!=[{'n':0}]: raise ProbeError('queue not empty')
    # No retries or automatic cleanup, even when failure is ambiguous.
    try:
        fail(url,token,BATCH)
        if objects()!=expected or query(META_READ)!=[{'marker':MARKER}]: raise UnknownOutcome('partial changes')
        for table in ('wm_cursor','wm_queue','wm_receipts'):
            if query('SELECT count(*) AS n FROM '+table)!=[{'n':0}]: raise UnknownOutcome('unexpected queue state')
    except Exception:
        raise UnknownOutcome('inspect before any retry') from None
    return 'rollback_observed'


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388' or
        os.environ.get('CONFIRMATION')!='PROBE_DEDICATED_QUEUE_ROLLBACK'):
        print('Probe blocked.',file=sys.stderr); return 1
    account=os.environ.pop('CLOUDFLARE_ACCOUNT_ID',''); token=os.environ.pop('CLOUDFLARE_API_TOKEN','')
    try:
        print('::notice title=D1 REST probe::'+probe(account,token)+'; yandex_requests=0'); return 0
    except UnknownOutcome:
        print('::error title=D1 REST probe::unknown_outcome_inspect_do_not_retry'); return 1
    except Exception:
        print('::error title=D1 REST probe::preflight_failed_no_probe'); return 1
if __name__=='__main__': sys.exit(main())
