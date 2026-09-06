import hashlib, json, math, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editor

class ValidationTest(unittest.TestCase):
    def test_rejects_invalid_ranges(self):
        for start,end in [(2,1),(-1,1),(0,11),(True,2),(0,float('inf')),(float('nan'),2),(0,.1)]:
            with self.assertRaises(ValueError):editor.validate({'start':start,'end':end,'title':'Teste'},10)
    def test_crop_bounds(self):
        meta={'width':160,'height':120}
        for crop in [{}, {'x':-1,'y':0,'width':20,'height':20}, {'x':0,'y':0,'width':200,'height':20}, {'x':True,'y':0,'width':20,'height':20}, {'x':0,'y':0,'width':1,'height':20}]:
            with self.assertRaises(ValueError):editor.validate_crop(crop,meta)
        self.assertEqual(editor.validate_crop({'x':11,'y':13,'width':81,'height':61},meta),(10,12,80,60))
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
                db.execute("INSERT INTO clips (id,source_id,title,start,end,muted,status,filename,created,crop_x,crop_y,crop_w,crop_h) VALUES ('crop','source','Crop',0,3,0,'rendering','crop.mp4','today',20,30,80,60)");db.commit()
                editor.render(db,'crop')
                row=db.execute("SELECT * FROM clips WHERE id='crop'").fetchone()
                self.assertEqual(row['status'],'completed',row['error'])
                meta=editor.probe(editor.DATA/'clips/crop.mp4')
                self.assertEqual((meta['width'],meta['height']),(80,60))
                self.assertAlmostEqual(meta['duration'],3,delta=.08)
                self.assertTrue(meta['hasAudio'])
                def frame(path,filters):
                    return subprocess.check_output(['ffmpeg','-v','error','-ss','1','-i',str(path),'-vf',filters,'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
                expected=frame(source,'crop=80:60:20:30')
                actual=frame(editor.DATA/'clips/crop.mp4','null')
                self.assertLess(sum(abs(a-b) for a,b in zip(expected,actual))/len(expected),12)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original_hash)
                db.close()
            finally:editor.DATA=old
