import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_disable_search_outbound as m
class Tests(unittest.TestCase):
 def ident(self,*a,**kw):return {'property':'properties/531336422','stream':'properties/531336422/dataStreams/123','token':'t','domain_matches':True,'can_edit':True}
 def test_one_write_then_idempotent(self):
  state={'name':'properties/531336422/dataStreams/123/enhancedMeasurementSettings','streamEnabled':True,'siteSearchEnabled':True,'outboundClicksEnabled':True,'formInteractionsEnabled':False};calls=[]
  def read(*a):return dict(state)
  def write(path,token):calls.append(path);state.update(siteSearchEnabled=False,outboundClicksEnabled=False);return dict(state)
  self.assertEqual(m.change(('a','b','c'),identify=self.ident,read=read,write=write),'disabled_and_read_back');self.assertEqual(len(calls),1)
  self.assertEqual(m.change(('a','b','c'),identify=self.ident,read=read,write=write),'already_disabled');self.assertEqual(len(calls),1)
 def test_identity_and_unrelated_change(self):
  with self.assertRaises(m.GuardError):m.change((),identify=lambda *a,**k:{'property':'properties/99'})
  state={'name':'properties/531336422/dataStreams/123/enhancedMeasurementSettings','streamEnabled':True,'siteSearchEnabled':True,'outboundClicksEnabled':True,'formInteractionsEnabled':False}
  def read(*a):return dict(state)
  def write(*a):state.update(siteSearchEnabled=False,outboundClicksEnabled=False,formInteractionsEnabled=True);return dict(state)
  with self.assertRaises(m.GuardError):m.change((),identify=self.ident,read=read,write=write)
 def test_malformed_setting_no_write(self):
  state={'name':'properties/531336422/dataStreams/123/enhancedMeasurementSettings','streamEnabled':True,'siteSearchEnabled':True,'outboundClicksEnabled':'false'}
  def write(*a):self.fail('must not write')
  with self.assertRaises(m.GuardError):m.change((),identify=self.ident,read=lambda *a:state,write=write)
