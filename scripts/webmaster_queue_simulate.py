#!/usr/bin/env python3
"""Exercise queue preparation on a temporary database; no Yandex credentials or writes."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import indexnow_submit as ix
from webmaster_queue import Queue
from webmaster_queue_prepare import prepare


def run(repo, token, temp_root, *, git=ix.git, prepare_queue=prepare, queue_cls=Queue):
    if not isinstance(temp_root, str) or not os.path.isabs(temp_root) or not Path(temp_root).is_dir():
        raise ValueError('invalid temporary directory')
    baseline=git('rev-parse','HEAD^1')
    if not re.fullmatch(r'[a-f0-9]{40}',baseline or ''):
        raise ValueError('invalid baseline')
    with tempfile.TemporaryDirectory(prefix='webmaster-queue-simulation-',dir=temp_root) as temp:
        queue=queue_cls(os.path.join(temp,'queue.sqlite'))
        try:
            result=prepare_queue(queue,repo,token,baseline)
            rows=queue.items()
            if result.get('mode')!='prepare_only' or result.get('blocked') != 0 or any(row[3]!='pending' for row in rows):
                raise ValueError('unexpected simulation state')
            return {'mode':'temporary_simulation','changed_count':result['deployment']['count'],
                    'pending_count':len(result['pending']),'yandex_requests':0,'persistent':False}
        finally:
            queue.close()


def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main':
        print('Simulation allowed only by manual dispatch on main.',file=sys.stderr)
        return 1
    token=os.environ.pop('GITHUB_TOKEN','')
    try:
        result=run(os.environ.get('GITHUB_REPOSITORY',''),token,os.environ.get('RUNNER_TEMP',''))
        print('::notice title=Queue simulation::changed='+str(result['changed_count'])+'; pending='+str(result['pending_count'])+'; yandex_requests=0; persistent=false')
        print(json.dumps(result))
        return 0
    except Exception:
        print('Queue preparation simulation failed; no Yandex actions were attempted.',file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
