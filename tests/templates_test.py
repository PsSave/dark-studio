import json,sys,tempfile,unittest,subprocess,shutil,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editor,templates

class TemplateValidationTest(unittest.TestCase):
    def test_bounds_and_fit(self):
        good={'name':'TV','x':20,'y':30,'slot_w':100,'slot_h':80,'fit':'cover'}
        self.assertEqual(templates.validate(good,320,480),('TV',20,30,100,80,'cover'))
        for bad in [{'x':-1},{'slot_w':400},{'slot_h':0},{'y':float('nan')},{'fit':'stretch'},{'name':''}]:
            with self.assertRaises(ValueError):templates.validate({**good,**bad},320,480)

@unittest.skipUnless(shutil.which('ffmpeg'),'ffmpeg necessário')
class CompositionTest(unittest.TestCase):
    def test_composition_pixels_audio_duration_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=editor.DATA;editor.DATA=Path(tmp)
            try:
                media=editor.DATA/'media';media.mkdir();art=editor.DATA/'templates';art.mkdir()
                subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=160x120:r=30','-f','lavfi','-i','sine=frequency=440','-t','1','-c:v','libx264','-threads','1','-c:a','aac',str(media/'video.mp4')],check=True)
                subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=blue:s=320x480','-frames:v','1','-threads','1',str(art/'art.png')],check=True)
                original_hash=hashlib.sha256((media/'video.mp4').read_bytes()).hexdigest()
                db=editor.connect();db.execute('CREATE TABLE videos (id TEXT,status TEXT,filename TEXT)');db.execute("INSERT INTO videos VALUES ('v','downloaded','video.mp4')")
                db.execute("INSERT INTO templates (id,name,filename,width,height,x,y,slot_w,slot_h,fit) VALUES ('t','TV','art.png',320,480,40,100,200,100,'cover')");db.commit()
                snapshot=templates.snapshot(db,editor.DATA,{'id':'t','layer':'front'})
                templates.save(db,{**snapshot,'x':80})
                self.assertEqual(snapshot['x'],40)
                for fit in ['cover','contain']:
                    snapshot['fit']=fit
                    db.execute('INSERT INTO clips (id,source_id,title,start,end,muted,status,filename,created,crop_x,crop_y,crop_w,crop_h,template_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(fit,'v','TV',0,1,0,'rendering',fit+'.mp4','today',0,0,160,120,json.dumps(snapshot)));db.commit()
                    editor.render(db,fit)
                    row=db.execute('SELECT * FROM clips WHERE id=?',(fit,)).fetchone();self.assertEqual(row['status'],'completed',row['error'])
                    file=editor.DATA/'clips'/row['filename'];meta=editor.probe(file)
                    self.assertEqual((meta['width'],meta['height']),(320,480));self.assertTrue(meta['hasAudio']);self.assertAlmostEqual(meta['duration'],1,delta=.08)
                    frame=subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
                    def pixel(x,y):return frame[(y*320+x)*3:(y*320+x)*3+3]
                    self.assertGreater(pixel(10,10)[2],200)
                    self.assertGreater(pixel(140,150)[0],200)
                    if fit=='contain':self.assertLess(max(pixel(45,150)),25)
                    else:self.assertGreater(pixel(45,150)[0],200)
                # Transparent hole reveals the video; opaque frame stays on top even inside its placement.
                import struct,zlib
                def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
                pixels=b''.join(b'\0'+b''.join(bytes((0,0,255,0 if 80<=x<220 and 120<=y<190 else 255)) for x in range(320)) for y in range(480))
                png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,480,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
                (art/'transparent.png').write_bytes(png)
                snapshot.update(filename='transparent.png',x=20,y=80,slot_w=260,slot_h=160,fit='cover',layer='behind')
                db.execute('INSERT INTO clips (id,source_id,title,start,end,muted,status,filename,created,crop_x,crop_y,crop_w,crop_h,template_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('behind','v','Layers',0,1,0,'rendering','behind.mp4','today',0,0,160,120,json.dumps(snapshot)));db.commit()
                editor.render(db,'behind')
                row=db.execute("SELECT * FROM clips WHERE id='behind'").fetchone();self.assertEqual(row['status'],'completed',row['error'])
                frame=subprocess.check_output(['ffmpeg','-v','error','-i',str(editor.DATA/'clips/behind.mp4'),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
                self.assertGreater(pixel(140,150)[0],200)
                self.assertGreater(pixel(40,100)[2],200)
                self.assertEqual(hashlib.sha256((media/'video.mp4').read_bytes()).hexdigest(),original_hash)
                with self.assertRaises(ValueError):templates.asset(editor.DATA,'../media/video.mp4')
                db.close()
            finally:editor.DATA=old
