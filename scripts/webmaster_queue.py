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
            for url in urls:
                self.db.execute('''INSERT INTO recrawl(url,revision,state) VALUES (?,?,'pending')
                    ON CONFLICT(url) DO UPDATE SET revision=excluded.revision,
                    state=CASE WHEN recrawl.revision=excluded.revision THEN recrawl.state
                      WHEN recrawl.state IN ('in_flight','uncertain') THEN recrawl.state
                      ELSE 'pending' END,
                    updated_at=CURRENT_TIMESTAMP''', (url, revision))

    def claim(self):
        """Atomically reserve one item before a network call; return URL and revision."""
        with self.transaction():
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
            state = ('uncertain' if outcome == 'uncertain' else
                     'pending' if outcome == 'quota_exhausted' or row[0] != revision else 'done')
            self.db.execute('UPDATE recrawl SET state=?,task_id=?,updated_at=CURRENT_TIMESTAMP WHERE url=?', (state,task_id,url))

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

    def items(self):
        return self.db.execute('SELECT url,revision,sent_revision,state,task_id FROM recrawl ORDER BY url').fetchall()
