import io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_private_workbook as w
try:from openpyxl import load_workbook
except ImportError:load_workbook=None
@unittest.skipUnless(load_workbook,'openpyxl not installed')
class Tests(unittest.TestCase):
 def test_workbook_and_missing_data(self):
  doc={'schema':1,'created_at':'2026-01-01T00:00:00Z','ga4':{'totals':{'active_users':1,'sessions':2,'page_views':3},'totals_metadata':{'sampled':False,'thresholded':False},'events_metadata':{'sampled':False,'thresholded':False},'events':{w.GOALS[0]:4}},'search_console':[{'start':'2025-12-01','end':'2025-12-28','metrics':{'clicks':5,'impressions':10,'ctr':.5,'position':2}},{'start':'2025-11-03','end':'2025-11-30','metrics':None}]}
  data=w.build(doc);book=load_workbook(io.BytesIO(data));self.assertEqual(book['GA4']['B2'].value,1);self.assertEqual(book['Цели']['B2'].value,4);self.assertIsNone(book['Цели']['B3'].value);self.assertIsNone(book['Поиск Google']['C2'].value);self.assertTrue(book['Поиск Google']['D2'].value.startswith('=IF'))
 def test_reject_bad_goal(self):
  with self.assertRaises(ValueError):w.build({'schema':1,'ga4':{'events':{'=private':1}},'search_console':[{},{}]})
if __name__=='__main__':unittest.main()
