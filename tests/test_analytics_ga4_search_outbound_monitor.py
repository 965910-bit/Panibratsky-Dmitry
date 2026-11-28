import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_search_outbound_monitor as m
class Tests(unittest.TestCase):
 def test_states(self):
  for data,expected in [({'search':False,'outbound':False},'success'),({'search':True,'outbound':False},'failure'),({'search':False,'outbound':True},'failure'),({'search':False},'failure'),({'search':'false','outbound':False},'failure')]:
   seen=[];status,_=m.monitor((),'r','1','t',read=lambda c:data,alert=lambda *args,**kw:seen.append(args[3]) or 'ok')
   self.assertEqual(status,expected);self.assertEqual(seen,[expected])
 def test_read_error(self):
  def fail(c):raise RuntimeError()
  self.assertEqual(m.monitor((),'r','1','t',read=fail,alert=lambda *a,**k:'ok')[0],'failure')
