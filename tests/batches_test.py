import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import editor,batches

class BatchTest(unittest.TestCase):
    def test_queue_retry_idempotency_and_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=editor.DATA;editor.DATA=Path(tmp)
            try:
                media=editor.DATA/'media';media.mkdir()
                db=editor.connect();batches.initialize(db)
                db.execute('CREATE TABLE videos (id TEXT PRIMARY KEY,status TEXT,filename TEXT,profile TEXT)')
                for id in ['a','b']:
                    (media/(id+'.mp4')).write_bytes(b'fixture')
                    db.execute('INSERT INTO videos VALUES (?,?,?,?)',(id,'downloaded',id+'.mp4','perfil'))
                db.commit()
                payload={'requestId':'test-request','name':'Meu lote','sourceIds':['a','b','a'],'normalizedCrop':{'x':.1,'y':.2,'width':.8,'height':.5},'muted':False}
                with patch.object(batches,'launch'):
                    first=batches.create(db,payload)
                    self.assertEqual(batches.create(db,payload),first)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_items').fetchone()[0],2)
                meta={'width':160,'height':120,'duration':2,'hasAudio':True}
                self.assertEqual(batches.scaled_crop(payload['normalizedCrop'],meta),dict(x=16,y=24,width=128,height=60))
                def fail_second(db,id):
                    item=db.execute('SELECT * FROM clips WHERE id=?',(id,)).fetchone()
                    db.execute("UPDATE clips SET status=?,error=? WHERE id=?",('failed' if item['source_id']=='b' else 'completed','test failure' if item['source_id']=='b' else '',id));db.commit()
                with patch.object(editor,'probe',return_value=meta),patch.object(editor,'render',side_effect=fail_second):batches.run(db,first['id'])
                self.assertEqual(db.execute('SELECT status FROM batches').fetchone()[0],'partial')
                self.assertEqual(db.execute('SELECT COUNT(*) FROM clips').fetchone()[0],2)
                with self.assertRaises(ValueError):batches.approve(db,{'batchId':first['id'],'sourceId':'b','approved':True})
                batches.approve(db,{'batchId':first['id'],'sourceId':'a','approved':True})
                with patch.object(batches,'launch'):batches.retry(db,{'id':first['id']})
                calls=[]
                def finish(db,id):
                    calls.append(id);db.execute("UPDATE clips SET status='completed',error='' WHERE id=?",(id,));db.commit()
                with patch.object(editor,'render',side_effect=finish):batches.run(db,first['id'])
                self.assertEqual(len(calls),1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM clips').fetchone()[0],2)
                state=batches.state(db)['batches'][0]
                self.assertEqual(state['status'],'completed');self.assertEqual(sum(i['approved'] for i in state['items']),1)
                db.close()
            finally:editor.DATA=old

    def test_scaled_crop_rejects_too_small(self):
        with self.assertRaises(ValueError):batches.scaled_crop({'x':0,'y':0,'width':.001,'height':.001},{'width':100,'height':100})
