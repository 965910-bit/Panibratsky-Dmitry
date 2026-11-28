import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_queue_sql as d
from webmaster_actions import BASE
A='a'*40;B='b'*40;C='c'*40;U=BASE+'wiki.html';V=BASE+'about.html';TASK='00000000-1111-2222-3333-444444444444'

def execute(db,batch):
    out=[]
    with db:
        for sql,args in batch:
            cur=db.execute(sql,args);out.append(cur.fetchall())
    return out

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=os.path.join(self.tmp.name,'q.db');self.db=sqlite3.connect(self.path)
        for sql in d.SCHEMA:self.db.execute(sql)
        self.db.execute('INSERT INTO wm_cursor VALUES (1,?)',(A,));self.db.commit()
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_atomic_enqueue_cursor_and_duplicate_event(self):
        result=execute(self.db,d.deployment_batch(A,B,[U,V]));self.assertEqual(result[-1],[(B,)])
        self.assertEqual(self.db.execute('SELECT count(*) FROM wm_queue').fetchone()[0],2)
        result=execute(self.db,d.deployment_batch(A,B,[U,V]));self.assertEqual(result[-1],[])
        self.assertEqual(self.db.execute('SELECT revision FROM wm_cursor').fetchone()[0],B)
    def test_cas_stale_does_not_enqueue(self):
        execute(self.db,d.deployment_batch(A,B,[U]));result=execute(self.db,d.deployment_batch(A,C,[V]))
        self.assertEqual(result[-1],[]);self.assertEqual(self.db.execute('SELECT url FROM wm_queue').fetchall(),[(U,)])
    def test_concurrent_claim_only_one(self):
        execute(self.db,d.deployment_batch(A,B,[U,V]));barrier=threading.Barrier(2);out=[]
        def run():
            db=sqlite3.connect(self.path,timeout=5);barrier.wait()
            try:
                with db:out.extend(db.execute(d.CLAIM).fetchall())
            finally:db.close()
        ts=[threading.Thread(target=run) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(len(out),1);self.assertEqual(self.db.execute("SELECT count(*) FROM wm_queue WHERE state='in_flight'").fetchone()[0],1)
    def test_uncertainty_blocks_and_new_revision_is_not_lost(self):
        execute(self.db,d.deployment_batch(A,B,[U,V]));claim=self.db.execute(d.CLAIM).fetchone();self.db.commit();url,revision=claim
        execute(self.db,d.deployment_batch(B,C,[url]));execute(self.db,d.finish_batch(url,revision,'uncertain'))
        self.assertEqual(self.db.execute(d.CLAIM).fetchall(),[])
        self.assertEqual(self.db.execute('SELECT revision,state FROM wm_queue WHERE url=?',(url,)).fetchone(),(C,'uncertain'))
    def test_receipt_and_finish_atomic(self):
        execute(self.db,d.deployment_batch(A,B,[U]));self.db.execute(d.CLAIM).fetchall();self.db.commit()
        execute(self.db,d.finish_batch(U,B,'accepted',TASK))
        self.assertEqual(self.db.execute('SELECT state FROM wm_queue').fetchone()[0],'done')
        self.assertEqual(self.db.execute('SELECT task_id,url,revision FROM wm_receipts').fetchone(),(TASK,U,B))
    def test_quota_exhaustion_keeps_pending(self):
        execute(self.db,d.deployment_batch(A,B,[U]));self.db.execute(d.CLAIM).fetchall();self.db.commit()
        execute(self.db,d.finish_batch(U,B,'quota_exhausted'))
        self.assertEqual(self.db.execute('SELECT state FROM wm_queue').fetchone()[0],'pending')
    def test_invalid_inputs_never_make_sql(self):
        for fn in (lambda:d.deployment_batch(A,B,['https://evil/']),lambda:d.deployment_batch(A,B,[U,U]),lambda:d.finish_batch(U,B,'accepted','bad')):
            with self.assertRaises(Exception):fn()
    def test_wrong_revision_does_not_create_receipt_or_finish(self):
        execute(self.db,d.deployment_batch(A,B,[U]));self.db.execute(d.CLAIM).fetchall();self.db.commit()
        result=execute(self.db,d.finish_batch(U,C,'accepted',TASK))
        self.assertEqual(result,[[],[]]);self.assertEqual(self.db.execute('SELECT state FROM wm_queue').fetchone()[0],'in_flight')
        self.assertEqual(self.db.execute('SELECT count(*) FROM wm_receipts').fetchone()[0],0)
    def test_duplicate_task_rolls_back_batch(self):
        execute(self.db,d.deployment_batch(A,B,[U]));self.db.execute(d.CLAIM).fetchall();self.db.execute('INSERT INTO wm_receipts(task_id,url,revision) VALUES(?,?,?)',(TASK,V,A));self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):execute(self.db,d.finish_batch(U,B,'accepted',TASK))
        self.assertEqual(self.db.execute('SELECT state FROM wm_queue').fetchone()[0],'in_flight')
    def test_concurrent_deployment_cas_local_sqlite(self):
        barrier=threading.Barrier(2); results=[]; errors=[]
        def run(target,url):
            db=sqlite3.connect(self.path,timeout=10)
            try:
                barrier.wait(timeout=5)
                results.append((target,url,execute(db,d.deployment_batch(A,target,[url]))[-1]))
            except Exception as exc:errors.append(exc)
            finally:db.close()
        threads=[threading.Thread(target=run,args=(B,U)),threading.Thread(target=run,args=(C,V))]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads));self.assertEqual(errors,[])
        self.assertEqual(len(results),2)
        winner=[(revision,url) for revision,url,rows in results if rows==[(revision,)]]
        self.assertEqual(len(winner),1)
        self.assertEqual(self.db.execute('SELECT revision FROM wm_cursor').fetchone()[0],winner[0][0])
        self.assertEqual(self.db.execute('SELECT url,revision FROM wm_queue').fetchall(),[(winner[0][1],winner[0][0])])
    def test_receipt_observation_exact_and_terminal(self):
        self.db.execute('INSERT INTO wm_receipts(task_id,url,revision) VALUES(?,?,?)',(TASK,U,B));self.db.commit()
        def observe(url,revision,state):
            sql,args=d.observe_receipt(TASK,url,revision,state)
            return execute(self.db,[(sql,args)])[0]
        self.assertEqual(observe(V,B,'DONE'),[])
        self.assertEqual(observe(U,C,'DONE'),[])
        self.assertEqual(observe(U,B,'IN_PROGRESS'),[(TASK,U,B,'IN_PROGRESS')])
        self.assertEqual(observe(U,B,'DONE'),[(TASK,U,B,'DONE')])
        self.assertEqual(observe(U,B,'FAILED'),[])
        self.assertEqual(self.db.execute('SELECT observed_state FROM wm_receipts').fetchone()[0],'DONE')
    def test_receipt_observation_rejects_unknown_or_invalid(self):
        for task,url,revision,state in ((TASK,U,B,None),(TASK,U,B,'UNKNOWN'),('bad',U,B,'DONE'),(TASK,'https://evil/',B,'DONE'),(TASK,U,'bad','DONE')):
            with self.assertRaises(Exception):d.observe_receipt(task,url,revision,state)
    def test_release_only_matching_unattempted_claim(self):
        execute(self.db,d.deployment_batch(A,B,[U,V]));url,revision=self.db.execute(d.CLAIM).fetchone();self.db.commit()
        self.assertEqual(execute(self.db,[d.release_unattempted(url,C)]),[[]])
        self.assertEqual(self.db.execute('SELECT state FROM wm_queue WHERE url=?',(url,)).fetchone()[0],'in_flight')
        self.assertEqual(execute(self.db,[d.release_unattempted(url,revision)]),[[(url,B,'pending')]])
        self.assertEqual(execute(self.db,[d.release_unattempted(url,revision)]),[[]])
    def test_release_preserves_newer_revision(self):
        execute(self.db,d.deployment_batch(A,B,[U]));self.db.execute(d.CLAIM).fetchall();self.db.commit()
        execute(self.db,d.deployment_batch(B,C,[U]))
        self.assertEqual(execute(self.db,[d.release_unattempted(U,B)]),[[(U,C,'pending')]])
        self.assertEqual(self.db.execute(d.CLAIM).fetchall(),[(U,C)])
    def test_stopped_worker_recovery_blocks_further_claims(self):
        execute(self.db,d.deployment_batch(A,B,[U,V]));claimed=self.db.execute(d.CLAIM).fetchone();self.db.commit()
        self.assertEqual(execute(self.db,[d.recover_stopped_worker()]),[[claimed]])
        self.assertEqual(execute(self.db,[d.recover_stopped_worker()]),[[]])
        self.assertEqual(self.db.execute(d.CLAIM).fetchall(),[])
        self.assertEqual(self.db.execute('SELECT state FROM wm_queue WHERE url=?',(claimed[0],)).fetchone()[0],'uncertain')
    def test_invalid_release_is_rejected(self):
        for url,revision in ((U,'bad'),('https://evil/',B)):
            with self.assertRaises(Exception):d.release_unattempted(url,revision)
if __name__=='__main__':unittest.main()
