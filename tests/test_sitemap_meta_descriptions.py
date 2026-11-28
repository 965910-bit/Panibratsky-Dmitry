"""Regression guard for descriptions on the explicitly published sitemap pages."""
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_sitemap import PAGES, ROOT

class HeadDescriptions(HTMLParser):
    def __init__(self):super().__init__();self.in_head=False;self.values=[]
    def handle_starttag(self,tag,attrs):
        if tag=='head':self.in_head=True
        attributes=dict(attrs)
        if self.in_head and tag=='meta' and attributes.get('name','').lower()=='description':
            self.values.append(attributes.get('content','').strip())
    def handle_endtag(self,tag):
        if tag=='head':self.in_head=False

class Tests(unittest.TestCase):
    def test_sitemap_pages_have_one_nonempty_unique_description(self):
        seen={}
        for page in PAGES:
            name=page or 'index.html'; parser=HeadDescriptions();parser.feed((ROOT/name).read_text(encoding='utf-8'))
            self.assertEqual(len(parser.values),1,name)
            self.assertTrue(parser.values[0],name)
            self.assertNotIn(parser.values[0],seen,name+' duplicates '+seen.get(parser.values[0],''))
            seen[parser.values[0]]=name

if __name__=='__main__':unittest.main()
