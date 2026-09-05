import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from browser_collector import whole_url, dismiss
class BrowserTest(unittest.TestCase):
    def test_remove_only_byte_range_preserving_signature(self):
        from urllib.parse import urlparse,parse_qs
        result=whole_url('https://video.cdninstagram.com/a.mp4?token=a%2Bb&bytestart=0&byteend=999&other=ok')
        self.assertEqual(parse_qs(urlparse(result).query),{'token':['a+b'],'other':['ok']})
    def test_dismiss_only_visible_close_controls(self):
        class Button:
            first=None
            def __init__(self): self.first=self;self.clicks=0
            def count(self): return 1
            def is_visible(self): return self.clicks<2
            def click(self,**kwargs): self.clicks+=1
        class Page:
            button=Button()
            def get_by_role(self,*args,**kwargs): return self.button
            def wait_for_timeout(self,*args): pass
        page=Page();dismiss(page);self.assertEqual(page.button.clicks,2)
if __name__=='__main__': unittest.main()
