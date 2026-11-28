"""End-to-end offline SQLite simulation of the D1 SQL prototype and worker.

This deliberately does not contact D1, GitHub or Yandex and is not a D1 client.
SQLite transactions below do not prove the remote REST batch isolation contract.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_queue_sql as sql
from webmaster_queue_worker import drain
from webmaster_actions import BASE

A='a'*40; B='b'*40; C='c'*40
U=BASE+'wiki.html'; V=BASE+'about.html'
TASK='c7fe80c0-36e3-11e6-8b2d-df96aa592c0a'

class LocalOnlyQueue:
    """Adapter solely for exercising worker against SQL in a temporary SQLite DB."""
    def __init__(self,path):
        self.db=sqlite3.connect(path, isolation_level=None)
    def close(self):self.db.close()
    def batch(self,statements):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            result=[self.db.execute(query,params).fetchall() for query,params in statements]
            self.db.execute('COMMIT');return result
        except BaseException:
            self.db.execute('ROLLBACK');raise
    def claim(self):
        rows=self.batch([(sql.CLAIM,[])])[0]
        if len(rows)>1:raise AssertionError('multiple claims')
        return rows[0] if rows else None
    def items(self):
        return self.db.execute('SELECT url,revision,sent_revision,state,task_id FROM wm_queue ORDER BY url').fetchall()
    def release_unattempted(self,url,revision):
        rows=self.batch([sql.release_unattempted(url,revision)])[0]
        if len(rows)!=1:raise AssertionError('release conflict')
    def finish(self,url,revision,outcome,task_id=None):
        result=self.batch(sql.finish_batch(url,revision,outcome,task_id))
        if len(result[-1])!=1:raise AssertionError('finish conflict')

class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=os.path.join(self.temp.name,'offline.sqlite')
        self.q=LocalOnlyQueue(self.path)
        for statement in sql.SCHEMA:self.q.db.execute(statement)
        self.q.db.execute('INSERT INTO wm_cursor VALUES (1,?)',(A,))
        self.q.batch(sql.deployment_batch(A,B,[U,V]))
    def tearDown(self):self.q.close();self.temp.cleanup()
    def accepted(self,t,urls,apply):return {'recrawl':[{'url':urls[0],'status':'accepted','task_id':TASK}]}
    def test_accept_persist_receipt_and_terminal_observation(self):
        result=drain(self.q,'fake',limit=1,validate=lambda urls:None,action=self.accepted)
        self.assertEqual(result['status'],'ok')
        url=result['results'][0]['url'];self.q.close();self.q=LocalOnlyQueue(self.path)
        self.assertEqual(self.q.db.execute('SELECT task_id,url,revision FROM wm_receipts').fetchall(),[(TASK,url,B)])
        self.assertEqual(self.q.batch([sql.observe_receipt(TASK,url,B,'DONE')])[0],[(TASK,url,B,'DONE')])
        self.assertEqual(self.q.batch([sql.observe_receipt(TASK,url,B,'IN_PROGRESS')])[0],[])
        self.assertEqual(self.q.db.execute('SELECT observed_state FROM wm_receipts').fetchone()[0],'DONE')
    def test_duplicate_blocks_across_restart(self):
        def duplicate(t,urls,apply):return {'recrawl':[{'url':urls[0],'status':'already_added'}]}
        self.assertEqual(drain(self.q,'fake',validate=lambda urls:None,action=duplicate)['status'],'uncertain')
        self.q.close();self.q=LocalOnlyQueue(self.path)
        self.assertEqual(drain(self.q,'fake',validate=lambda urls:None,action=lambda *args:self.fail('retry'))['status'],'blocked')
        self.assertEqual(sum(row[3]=='uncertain' for row in self.q.items()),1)
    def test_preflight_failure_releases_and_never_calls_provider(self):
        def invalid(urls):raise ValueError('invalid live bytes')
        self.assertEqual(drain(self.q,'fake',validate=invalid,action=lambda *args:self.fail('sent'))['status'],'preflight_failed')
        self.assertTrue(all(row[3]=='pending' for row in self.q.items()))
    def test_crash_after_claim_is_not_retried_after_restart(self):
        claim=self.q.claim();self.q.close();self.q=LocalOnlyQueue(self.path)
        self.assertEqual(drain(self.q,'fake',validate=lambda urls:None,action=lambda *args:self.fail('retry'))['status'],'blocked')
        self.assertEqual(self.q.batch([sql.recover_stopped_worker()])[0],[claim])
        self.assertEqual(drain(self.q,'fake',validate=lambda urls:None,action=lambda *args:self.fail('retry'))['status'],'blocked')
    def test_new_revision_during_request_stays_pending(self):
        def action(t,urls,apply):
            self.q.batch(sql.deployment_batch(B,C,[urls[0]]))
            return self.accepted(t,urls,apply)
        result=drain(self.q,'fake',limit=1,validate=lambda urls:None,action=action)
        url=result['results'][0]['url']
        self.assertEqual(self.q.db.execute('SELECT revision,state FROM wm_queue WHERE url=?',(url,)).fetchone(),(C,'pending'))
        self.assertEqual(self.q.db.execute('SELECT revision FROM wm_receipts WHERE task_id=?',(TASK,)).fetchone()[0],B)
    def test_quota_stops_without_losing_queue(self):
        def quota(t,urls,apply):return {'recrawl':[{'url':urls[0],'status':'quota_exhausted'}]}
        self.assertEqual(drain(self.q,'fake',validate=lambda urls:None,action=quota)['status'],'quota_exhausted')
        self.assertTrue(all(row[3]=='pending' for row in self.q.items()))
    def test_receipt_collision_rolls_back_leaving_claim_blocked(self):
        self.q.db.execute('INSERT INTO wm_receipts(task_id,url,revision) VALUES (?,?,?)',(TASK,U,A))
        with self.assertRaises(sqlite3.IntegrityError):drain(self.q,'fake',limit=1,validate=lambda urls:None,action=self.accepted)
        self.assertEqual(sum(row[3]=='in_flight' for row in self.q.items()),1)
        self.assertEqual(drain(self.q,'fake',validate=lambda urls:None,action=lambda *args:self.fail('retry'))['status'],'blocked')
if __name__=='__main__':unittest.main()
