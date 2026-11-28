import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_disable_form_measurement as m
class Tests(unittest.TestCase):
 def ident(self,*a,**kw):return {'property':'properties/531336422','stream':'properties/531336422/dataStreams/123','token':'t','domain_matches':True,'can_edit':True}
 def test_single_write_and_readback(self):
  state={'name':'properties/531336422/dataStreams/123/enhancedMeasurementSettings','streamEnabled':True,'formInteractionsEnabled':True,'siteSearchEnabled':True};calls=[]
  def read(*a):return dict(state)
  def write(path,token):calls.append(path);state['formInteractionsEnabled']=False;return dict(state)
  self.assertEqual(m.change(('a','b','c'),identify=self.ident,read=read,write=write),'disabled_and_read_back');self.assertEqual(len(calls),1)
  self.assertEqual(m.change(('a','b','c'),identify=self.ident,read=read,write=write),'already_disabled');self.assertEqual(len(calls),1)
 def test_identity_guard(self):
  with self.assertRaises(m.GuardError):m.change((),identify=lambda *a,**k:{'property':'properties/99'})
 def test_detect_concurrent_setting_change(self):
  state={'name':'properties/531336422/dataStreams/123/enhancedMeasurementSettings','streamEnabled':True,'formInteractionsEnabled':True,'siteSearchEnabled':True}
  def read(*a):return dict(state)
  def write(*a):state.update(formInteractionsEnabled=False,siteSearchEnabled=False);return dict(state)
  with self.assertRaises(m.GuardError):m.change((),identify=self.ident,read=read,write=write)
if __name__=='__main__':unittest.main()
