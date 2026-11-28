#!/usr/bin/env python3
"""Prepare a durable local queue from a verified Pages deployment, without writes to Yandex.

This is a library primitive, not a scheduled job. SQLite must live on persistent,
trusted local storage; Actions runners, caches and uncoordinated network volumes
are not suitable. A caller must serialize a future writer across the entire
verify/claim/POST/record sequence. No provider tokens are read here.
"""
import json
import re
import indexnow_submit as ix
from webmaster_deployment_cursor import is_ancestor, changed_canonical

REPOSITORY_ID = 1102759388
SHA = re.compile(r'[a-f0-9]{40}\Z')


class PreparationError(Exception):
    pass


def prepare(queue, repo, github_token, baseline, *, git=ix.git, fetch=ix.request,
            validate=ix.validate_live, ancestor=is_ancestor, changed=changed_canonical):
    """Advance cursor atomically and describe pending tasks; never claim or submit.

    The explicit baseline is only used for an uninitialized queue. Repository
    identity, current main and the latest successful Pages build are verified.
    State can change after the final main check: a future sender must revalidate
    immediately before each write, and this check cannot eliminate that race.
    """
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or ''):
        raise PreparationError('invalid repository')
    if not isinstance(github_token,str) or not github_token or '\r' in github_token or '\n' in github_token:
        raise PreparationError('invalid GitHub token')
    if baseline is not None and (not isinstance(baseline,str) or not SHA.fullmatch(baseline)):
        raise PreparationError('invalid baseline')
    head=git('rev-parse','HEAD')
    if not isinstance(head,str) or not SHA.fullmatch(head):
        raise PreparationError('invalid checkout')
    root='https://api.github.com/repos/'+repo
    def read(path):
        status,_,body=fetch(root+path,token=github_token)
        if status != 200: raise PreparationError('GitHub request failed')
        result=json.loads(body)
        if not isinstance(result,dict): raise PreparationError('invalid GitHub response')
        return result
    if read('').get('id') != REPOSITORY_ID:
        raise PreparationError('wrong repository identity')
    def current_main():
        try: return read('/git/ref/heads/main')['object']['sha']
        except (KeyError,TypeError): raise PreparationError('invalid main reference') from None
    if current_main() != head:
        raise PreparationError('main differs from checkout')
    build=read('/pages/builds/latest')
    if build.get('status') != 'built' or build.get('commit') != head:
        raise PreparationError('latest Pages build differs from checkout')
    validate([])
    if current_main() != head:
        raise PreparationError('main advanced during verification')
    advancement=queue.enqueue_deployment(head,baseline,ancestor=ancestor,changed=changed)
    if advancement['status'] == 'stale':
        raise PreparationError('deployment is older than queue cursor; stop')
    rows=queue.items()
    pending=[url for url,_,_,state,_ in rows if state=='pending']
    blocked=sum(state in ('uncertain','in_flight') for _,_,_,state,_ in rows)
    return {'deployment':advancement, 'pending':pending, 'blocked':blocked,
            'mode':'prepare_only', 'indexing_guaranteed':False}
