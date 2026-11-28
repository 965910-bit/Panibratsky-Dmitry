import io,json,sys,unittest,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_bigquery_dataset_probe as p
class Response:
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self,*a):return json.dumps({'datasetReference':{'datasetId':'analytics_123'}}).encode()
class Tests(unittest.TestCase):
 def run_probe(self,project='projects/456',opener=lambda req,timeout:Response()):
  return p.probe(('a','b','c'),identify=lambda *a,**k:{'property':'properties/123','domain_matches':True,'token':'safe'},read_pages=lambda *a,**k:[{'project':project}],open_url=opener)
 def test_get_target(self):
  def get(req,timeout):
   self.assertEqual(req.get_method(),'GET');self.assertEqual(req.full_url,'https://bigquery.googleapis.com/bigquery/v2/projects/456/datasets/analytics_123');return Response()
  self.assertEqual(self.run_probe(opener=get),'metadata_accessible')
 def test_denial_is_inconclusive(self):
  def deny(req,timeout):raise urllib.error.HTTPError(req.full_url,403,'private',{},io.BytesIO(b'private'))
  self.assertEqual(self.run_probe(opener=deny),'access_or_scope_or_service_denied')
 def test_host_injection_blocked(self):
  with self.assertRaises(p.ProbeError):self.run_probe('projects/456@evil.example')
if __name__=='__main__':unittest.main()
