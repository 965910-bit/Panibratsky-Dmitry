#!/usr/bin/env python3
"""Single-host local queue cycle primitive; no service, schedule, or token storage.

Requires a trusted private local filesystem directory that persists across runs,
all writers cooperating on the same lock, and a current full git checkout.
Not suitable for ephemeral GitHub runners, cache, or independent hosts.
"""
import fcntl
import json
import os
from pathlib import Path
import re
from contextlib import contextmanager
import indexnow_submit as ix
from webmaster_queue import Queue
from webmaster_queue_prepare import prepare, REPOSITORY_ID
from webmaster_queue_worker import drain


class CycleError(Exception):
    pass


@contextmanager
def exclusive_lock(path):
    """Lock one trusted path for the whole cycle; other cooperating writers stop."""
    if not isinstance(path,str) or not os.path.isabs(path) or not Path(path).parent.is_dir():
        raise CycleError('absolute local path in existing directory required')
    if Path(path).is_symlink():
        raise CycleError('queue database symlink forbidden')
    flags=os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(path+'.lock',flags,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise CycleError('another worker holds the lock') from None
        yield
    finally:
        os.close(fd)


def verify_before_write(repo, github_token, expected_sha, urls, *, git=ix.git, fetch=ix.request, validate=ix.validate_live):
    """Check current main, exact Pages build and live bytes before each submission.

    Main may still change between the last check and provider POST. This reduces,
    but cannot remove, that race across independent services.
    """
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or not re.fullmatch(r'[a-f0-9]{40}',expected_sha or ''):
        raise CycleError('invalid repository or revision')
    root='https://api.github.com/repos/'+repo
    def read(path):
        status,_,body=fetch(root+path,token=github_token)
        if status!=200:raise CycleError('GitHub unavailable')
        result=json.loads(body)
        if not isinstance(result,dict):raise CycleError('invalid GitHub response')
        return result
    if git('rev-parse','HEAD') != expected_sha or read('').get('id') != REPOSITORY_ID:
        raise CycleError('checkout or repository changed')
    def main_sha():
        try:return read('/git/ref/heads/main')['object']['sha']
        except (KeyError,TypeError):raise CycleError('invalid main') from None
    if main_sha()!=expected_sha:raise CycleError('main changed')
    build=read('/pages/builds/latest')
    if build.get('status')!='built' or build.get('commit')!=expected_sha:
        raise CycleError('build changed')
    validate(urls)
    if main_sha()!=expected_sha:raise CycleError('main changed during live check')


def cycle(db_path, repo, github_token, baseline, yandex_token='', *, apply=False,
          lock=exclusive_lock, queue_cls=Queue, prepare_queue=prepare, drain_queue=drain,
          preflight=verify_before_write):
    if type(apply) is not bool:
        raise CycleError('invalid mode')
    if apply and (not isinstance(yandex_token,str) or not yandex_token or '\r' in yandex_token or '\n' in yandex_token):
        raise CycleError('missing provider token')
    with lock(db_path):
        queue=queue_cls(db_path)
        try:
            plan=prepare_queue(queue,repo,github_token,baseline)
            if plan.get('mode')!='prepare_only' or not isinstance(plan.get('deployment'),dict):
                raise CycleError('invalid preparation')
            sha=plan['deployment'].get('target')
            if not isinstance(sha,str) or not re.fullmatch(r'[a-f0-9]{40}',sha):
                raise CycleError('invalid prepared revision')
            if not apply:
                return {'mode':'prepare_only','plan':plan}
            if type(plan.get('blocked')) is not int or plan['blocked'] != 0:
                return {'mode':'apply','status':'blocked','plan':plan}
            # drain() records a claim before each write. Failed preflight releases
            # it; post-write errors leave uncertainty and stop all future writes.
            result=drain_queue(queue,yandex_token,validate=lambda urls:preflight(repo,github_token,sha,urls))
            return {'mode':'apply','plan':plan,'result':result}
        finally:
            queue.close()
