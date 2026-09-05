import unittest, tempfile, shutil, subprocess, sys, json, os
from pathlib import Path

class CollectorTest(unittest.TestCase):
    def test_download_resume_and_carousel(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); scripts=root/'scripts'; scripts.mkdir()
            shutil.copy('scripts/collector.py',scripts/'collector.py')
            shutil.copy('scripts/errors.py',scripts/'errors.py')
            (scripts/'instaloader.py').write_text('''
from datetime import datetime
from pathlib import Path
class Response:
 def iter_content(self,chunk_size): yield b'video-content'
 def close(self): pass
class Instaloader:
 def __init__(self,**kwargs): self.context=self
 def get_raw(self,url):
  with open(Path(__file__).parent/'requests','a') as f: f.write(url+'\\n')
  return Response()
class Node:
 is_video=True
 video_url='https://example.test/video'
class Post:
 typename='GraphSidecar'
 shortcode='ABC_123'
 caption='Teste'
 date_utc=datetime(2026,1,1)
 def get_sidecar_nodes(self): return [Node(),Node()]
class Profile:
 @staticmethod
 def from_username(context,profile): return Profile()
 def get_posts(self): return iter([Post()])
 def get_reels(self): return iter([Post()])
''')
            def run(command): return subprocess.check_output([sys.executable,str(scripts/'collector.py'),command,'teste'],text=True)
            run('scan'); first=json.loads(run('state'))
            self.assertEqual(len(first['videos']),2,first)
            self.assertTrue(all(v['status']=='downloaded' for v in first['videos']))
            self.assertEqual(first['jobs'][0]['status'],'completed')
            run('scan')
            self.assertEqual(len((scripts/'requests').read_text().splitlines()),2)
            video=root/'.data/media'/first['videos'][0]['filename']; video.unlink()
            run('scan')
            self.assertTrue(video.exists())
            self.assertEqual(len((scripts/'requests').read_text().splitlines()),3)
if __name__=='__main__': unittest.main()
