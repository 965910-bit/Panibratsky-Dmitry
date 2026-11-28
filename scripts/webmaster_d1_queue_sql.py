#!/usr/bin/env python3
"""Offline SQL prototype for a dedicated D1 recrawl queue; no network or deploy.

A caller must execute each returned batch as ONE transaction. Never apply this
schema to another application's database. D1 remote transaction semantics,
identity, credentials, provisioning and scheduling still require verification.
"""
import re
from webmaster_actions import allowed_urls

SHA=re.compile(r'[a-f0-9]{40}\Z')
SCHEMA=(
    "CREATE TABLE wm_cursor (singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision TEXT NOT NULL)",
    """CREATE TABLE wm_queue (url TEXT PRIMARY KEY, revision TEXT NOT NULL, sent_revision TEXT,
       state TEXT NOT NULL CHECK(state IN ('pending','in_flight','done','uncertain')), task_id TEXT)""",
    """CREATE TABLE wm_receipts (task_id TEXT PRIMARY KEY, url TEXT NOT NULL,
       revision TEXT NOT NULL, observed_state TEXT CHECK(observed_state IN ('IN_PROGRESS','DONE','FAILED')))""",
)
CLAIM="""UPDATE wm_queue SET state='in_flight', sent_revision=revision, task_id=NULL
 WHERE url=(SELECT url FROM wm_queue WHERE state='pending' ORDER BY url LIMIT 1)
 AND NOT EXISTS (SELECT 1 FROM wm_queue WHERE state IN ('in_flight','uncertain'))
 RETURNING url,sent_revision"""

class D1QueueError(Exception):pass


def deployment_batch(previous,target,urls):
    """CAS cursor and enqueue atomically; initialization must be explicit/verified.

    All statements must execute in one serializable transaction. A stale cursor
    results in no changes. Caller must validate ancestry and production first.
    """
    if not isinstance(previous,str) or not SHA.fullmatch(previous) or not isinstance(target,str) or not SHA.fullmatch(target):
        raise D1QueueError('invalid revision')
    urls=list(urls)
    if len(urls)!=len(set(urls)) or (previous==target and urls):raise D1QueueError('invalid diff')
    for url in urls:allowed_urls([url])
    statements=[]
    for url in urls:
        statements.append(('''INSERT INTO wm_queue(url,revision,state)
          SELECT ?,?,'pending' WHERE EXISTS (SELECT 1 FROM wm_cursor WHERE singleton=1 AND revision=?)
          ON CONFLICT(url) DO UPDATE SET revision=excluded.revision,
          state=CASE WHEN wm_queue.revision=excluded.revision THEN wm_queue.state
            WHEN wm_queue.state IN ('in_flight','uncertain') THEN wm_queue.state ELSE 'pending' END''',
          [url,target,previous]))
    statements.append(('UPDATE wm_cursor SET revision=? WHERE singleton=1 AND revision=? RETURNING revision',[target,previous]))
    return statements


def finish_batch(url,revision,outcome,task_id=None):
    """Finish an exact claim; accepted receipt and state must commit together."""
    allowed_urls([url])
    if not isinstance(revision,str) or not SHA.fullmatch(revision):raise D1QueueError('invalid revision')
    if outcome not in ('accepted','already_added','quota_exhausted','uncertain'):raise D1QueueError('invalid outcome')
    if outcome=='accepted':
        if not isinstance(task_id,str) or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',task_id):
            raise D1QueueError('invalid task id')
    elif task_id is not None:raise D1QueueError('unexpected task id')
    batch=[]
    if outcome=='accepted':
        batch.append(('''INSERT INTO wm_receipts(task_id,url,revision)
           SELECT ?,url,sent_revision FROM wm_queue WHERE url=? AND sent_revision=? AND state='in_flight' ''',
           [task_id,url,revision]))
    state='uncertain' if outcome=='uncertain' else 'pending' if outcome=='quota_exhausted' else 'done'
    batch.append(('''UPDATE wm_queue SET state=CASE WHEN ?='done' AND revision<>? THEN 'pending' ELSE ? END, task_id=?
      WHERE url=? AND sent_revision=? AND state='in_flight' RETURNING url,state''',
      [state,revision,state,task_id,url,revision]))
    return batch


def observe_receipt(task_id, url, revision, state):
    """Build one guarded observation update; prototype only, no network.

    Unknown reads never call this function and must not change stored state.
    Terminal states cannot be overwritten, including by a late concurrent poll.
    A zero-row result is ambiguous (missing, mismatch or already terminal) and
    callers must inspect the exact receipt rather than assume success.
    """
    allowed_urls([url])
    if not isinstance(revision,str) or not SHA.fullmatch(revision):
        raise D1QueueError('invalid revision')
    if not isinstance(task_id,str) or not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',task_id):
        raise D1QueueError('invalid task id')
    if state not in ('IN_PROGRESS','DONE','FAILED'):
        raise D1QueueError('invalid observation')
    return ('''UPDATE wm_receipts SET observed_state=?
      WHERE task_id=? AND url=? AND revision=?
      AND (observed_state IS NULL OR observed_state='IN_PROGRESS')
      RETURNING task_id,url,revision,observed_state''', [state,task_id,url,revision])
