import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_ga4_form_privacy_monitor as m
class Tests(unittest.TestCase):
 def test_states(self):
  for value,expected in [(False,'success'),(True,'failure'),('false','failure')]:
   seen=[]
   result=m.monitor((), 'r','1','t',read=lambda c:{'forms':value},alert=lambda *args,**kw:seen.append(args[3]) or 'ok')
   self.assertEqual(result[0],expected);self.assertEqual(seen,[expected])
 def test_read_error(self):
  def fail(c):raise RuntimeError()
  self.assertEqual(m.monitor((),'r','1','t',read=fail,alert=lambda *a,**k:'ok')[0],'failure')
if __name__=='__main__':unittest.main()
