#!/usr/bin/env python3
"""Local persistent recrawl queue primitives; not wired to GitHub Actions.

An in-flight item is deliberately never requeued automatically after a crash:
its remote outcome can be unknown. This module performs no network operations.
"""
import re
import sqlite3
from contextlib import contextmanager
from webmaster_actions import allowed_urls


class QueueError(Exception):
    pass


class Queue:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=30000')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS recrawl (
            url TEXT PRIMARY KEY, revision TEXT NOT NULL,
            sent_revision TEXT, state TEXT NOT NULL
              CHECK(state IN ('pending','in_flight','done','uncertain')),
            task_id TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')

        with self.transaction():
            self.db.execute('''CREATE TABLE IF NOT EXISTS recrawl_receipts (
                task_id TEXT PRIMARY KEY, url TEXT NOT NULL, revision TEXT NOT NULL,
                observed_state TEXT CHECK(observed_state IN ('IN_PROGRESS','DONE','FAILED')),
                last_checked TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS deployment_cursor (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision TEXT NOT NULL)''')
            # Older queue databases retained only the latest task per URL.
            self.db.execute('''INSERT OR IGNORE INTO recrawl_receipts(task_id,url,revision)
                SELECT task_id,url,sent_revision FROM recrawl
                WHERE task_id IS NOT NULL AND sent_revision IS NOT NULL''')

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def enqueue(self, urls, revision):
        # Avoid the per-operation five-URL cap while enforcing the exact allowlist.
        urls = list(urls)
        if not re.fullmatch(r'[a-f0-9]{40}', revision) or len(set(urls)) != len(urls):
            raise QueueError('invalid revision or duplicate URLs')
        for url in urls:
            allowed_urls([url])
        with self.transaction():
            self._enqueue_validated(urls, revision)

    def _enqueue_validated(self, urls, revision):
        for url in urls:
            self.db.execute('''INSERT INTO recrawl(url,revision,state) VALUES (?,?,'pending')
                ON CONFLICT(url) DO UPDATE SET revision=excluded.revision,
                state=CASE WHEN recrawl.revision=excluded.revision THEN recrawl.state
                  WHEN recrawl.state IN ('in_flight','uncertain') THEN recrawl.state
                  ELSE 'pending' END,
                updated_at=CURRENT_TIMESTAMP''', (url, revision))

    def enqueue_deployment(self, target, baseline, *, ancestor, changed):
        """Advance a caller-verified deployment cursor and enqueue its diff atomically.

        Initial baseline must be explicitly selected by the caller. The caller
        must verify target was successfully deployed and is still current main.
        Callbacks must inspect immutable git SHAs and raise on operational errors.
        """
        if not isinstance(target,str) or not re.fullmatch(r'[a-f0-9]{40}',target):
            raise QueueError('invalid target')
        with self.transaction():
            row = self.db.execute('SELECT revision FROM deployment_cursor WHERE singleton=1').fetchone()
            previous = row[0] if row else baseline
            if not isinstance(previous,str) or not re.fullmatch(r'[a-f0-9]{40}',previous):
                raise QueueError('explicit initial baseline required')
            if previous != target and not ancestor(previous,target):
                if row and ancestor(target,previous):
                    return {'status':'stale', 'previous':previous, 'target':target, 'count':0}
                raise QueueError('deployment history diverged')
            urls = list(changed(previous,target)) if previous != target else []
            if len(urls) != len(set(urls)):
                raise QueueError('duplicate URLs')
            for url in urls:
                allowed_urls([url])
            self._enqueue_validated(urls,target)
            self.db.execute('''INSERT INTO deployment_cursor(singleton,revision) VALUES(1,?)
                ON CONFLICT(singleton) DO UPDATE SET revision=excluded.revision''',(target,))
            return {'status':'recorded', 'previous':previous, 'target':target, 'count':len(urls)}

    def cursor(self):
        row = self.db.execute('SELECT revision FROM deployment_cursor WHERE singleton=1').fetchone()
        return row[0] if row else None

    def claim(self):
        """Atomically reserve one item before a network call; return URL and revision."""
        with self.transaction():
            # Pause the entire queue until the outstanding write is resolved.
            if self.db.execute("SELECT 1 FROM recrawl WHERE state IN ('in_flight','uncertain') LIMIT 1").fetchone():
                return None
            row = self.db.execute("SELECT url,revision FROM recrawl WHERE state='pending' ORDER BY updated_at,url LIMIT 1").fetchone()
            if row:
                self.db.execute("UPDATE recrawl SET state='in_flight',sent_revision=revision,task_id=NULL,updated_at=CURRENT_TIMESTAMP WHERE url=?", (row[0],))
            return row

    def finish(self, url, revision, outcome, task_id=None):
        """Resolve only the exact claim. Unknown outcomes require manual reconciliation."""
        if outcome not in ('accepted','already_added','quota_exhausted','uncertain'):
            raise QueueError('invalid outcome')
        if outcome == 'accepted' and (not isinstance(task_id, str) or not task_id or len(task_id) > 512):
            raise QueueError('accepted requires a task id')
        if outcome != 'accepted' and task_id is not None:
            raise QueueError('unexpected task id')
        with self.transaction():
            row = self.db.execute('SELECT revision,sent_revision,state FROM recrawl WHERE url=?',(url,)).fetchone()
            if not row or row[1] != revision or row[2] != 'in_flight':
                raise QueueError('claim mismatch')
            if outcome == 'accepted':
                existing = self.db.execute('SELECT url,revision FROM recrawl_receipts WHERE task_id=?',(task_id,)).fetchone()
                if existing and existing != (url, revision):
                    raise QueueError('task id already associated with another submission')
                self.db.execute('INSERT OR IGNORE INTO recrawl_receipts(task_id,url,revision) VALUES (?,?,?)',(task_id,url,revision))
            state = ('uncertain' if outcome == 'uncertain' else
                     'pending' if outcome == 'quota_exhausted' or row[0] != revision else 'done')
            self.db.execute('UPDATE recrawl SET state=?,task_id=?,updated_at=CURRENT_TIMESTAMP WHERE url=?', (state,task_id,url))

    def release_unattempted(self, url, revision):
        """Return a claim to pending only if no provider write was attempted."""
        with self.transaction():
            row = self.db.execute('SELECT sent_revision,state FROM recrawl WHERE url=?',(url,)).fetchone()
            if not row or row != (revision, 'in_flight'):
                raise QueueError('claim mismatch')
            self.db.execute("UPDATE recrawl SET state='pending',updated_at=CURRENT_TIMESTAMP WHERE url=?",(url,))

    def recover_after_stop(self):
        """Call only when the single worker is known to have stopped."""
        with self.transaction():
            self.db.execute("UPDATE recrawl SET state='uncertain',updated_at=CURRENT_TIMESTAMP WHERE state='in_flight'")

    def reconcile(self, url, revision, accepted):
        """An operator resolves an uncertain claim after inspecting the provider."""
        if type(accepted) is not bool:
            raise QueueError('explicit resolution required')
        with self.transaction():
            row = self.db.execute('SELECT revision,sent_revision,state FROM recrawl WHERE url=?',(url,)).fetchone()
            if not row or row[1] != revision or row[2] != 'uncertain':
                raise QueueError('claim mismatch')
            state = 'done' if accepted and row[0] == revision else 'pending'
            self.db.execute('UPDATE recrawl SET state=?,updated_at=CURRENT_TIMESTAMP WHERE url=?',(state,url))

    def unchecked_receipts(self, limit):
        if type(limit) is not int or not 1 <= limit <= 50:
            raise QueueError('invalid receipt limit')
        return self.db.execute('''SELECT task_id,url,revision FROM recrawl_receipts
            WHERE observed_state IS NULL OR observed_state='IN_PROGRESS'
            ORDER BY last_checked IS NOT NULL, last_checked, task_id LIMIT ?''',(limit,)).fetchall()

    def record_observation(self, task_id, url, revision, state):
        # None denotes a failed check, never evidence of remote state.
        if state not in (None, 'IN_PROGRESS', 'DONE', 'FAILED'):
            raise QueueError('invalid observation')
        with self.transaction():
            current = self.db.execute('SELECT url,revision,observed_state FROM recrawl_receipts WHERE task_id=?',(task_id,)).fetchone()
            if not current or current[:2] != (url,revision):
                raise QueueError('receipt mismatch')
            if current[2] in ('DONE','FAILED'):
                raise QueueError('terminal observation already recorded')
            self.db.execute('''UPDATE recrawl_receipts SET observed_state=COALESCE(?,observed_state),
                last_checked=STRFTIME('%Y-%m-%dT%H:%M:%fZ','now') WHERE task_id=?''',(state,task_id))

    def receipts(self):
        return self.db.execute('SELECT task_id,url,revision,observed_state,last_checked FROM recrawl_receipts ORDER BY task_id').fetchall()

    def items(self):
        return self.db.execute('SELECT url,revision,sent_revision,state,task_id FROM recrawl ORDER BY url').fetchall()
