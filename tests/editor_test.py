import hashlib, json, math, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editor

class ValidationTest(unittest.TestCase):
    def test_rejects_invalid_ranges(self):
        for start,end in [(2,1),(-1,1),(0,11),(True,2),(0,float('inf')),(float('nan'),2),(0,.1)]:
            with self.assertRaises(ValueError):editor.validate({'start':start,'end':end,'title':'Teste'},10)
    def test_frame_boundary_and_literal_title(self):
        self.assertEqual(editor.validate({'start':1,'end':1.2,'title':' ../nome ','muted':True},10),(1,1.2,'../nome',True))

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg necessário')
class ExportTest(unittest.TestCase):
    def test_accurate_trim_audio_option_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            old=editor.DATA;editor.DATA=Path(folder)
            try:
                source=editor.DATA/'media/perfil/source.mp4';source.parent.mkdir(parents=True)
                subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x120:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','3','-c:v','libx264','-threads','1','-c:a','aac',str(source)],check=True)
                original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
                db=editor.connect();db.execute('CREATE TABLE videos (id TEXT,status TEXT,filename TEXT)');db.execute("INSERT INTO videos VALUES ('source','downloaded','perfil/source.mp4')");db.commit()
                for clip_id,muted in [('with-audio',False),('silent',True)]:
                    db.execute('INSERT INTO clips (id,source_id,title,start,end,muted,status,filename,created) VALUES (?,?,?,?,?,?,?,?,?)',(clip_id,'source','Teste',.7,1.8,int(muted),'rendering',f'{clip_id}.mp4','today'));db.commit()
                    editor.render(db,clip_id)
                    row=db.execute('SELECT * FROM clips WHERE id=?',(clip_id,)).fetchone()
                    self.assertEqual(row['status'],'completed',row['error'])
                    meta=editor.probe(editor.DATA/'clips'/row['filename'])
                    self.assertAlmostEqual(meta['duration'],1.1,delta=.08)
                    self.assertEqual(meta['hasAudio'],not muted)
                    self.assertEqual((meta['width'],meta['height']),(160,120))
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original_hash)
                db.close()
            finally:editor.DATA=old
