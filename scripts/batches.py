"""Durable, sequential creative production from a frozen editing recipe."""
import json,math,os,subprocess,sys,time,uuid
from datetime import datetime,timezone
import editor,templates

def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL, recipe TEXT NOT NULL,status TEXT NOT NULL,pid INTEGER,created TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS batch_items (batch_id TEXT NOT NULL,source_id TEXT NOT NULL,
    clip_id TEXT,status TEXT NOT NULL,error TEXT NOT NULL DEFAULT '',approved INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(batch_id,source_id))''');db.commit()

def recover(db):
    for row in db.execute("SELECT id,pid FROM batches WHERE status='running'").fetchall():
        if row['pid']:
            try:os.kill(row['pid'],0)
            except ProcessLookupError:db.execute("UPDATE batches SET status='interrupted' WHERE id=?",(row['id'],))
    db.commit()

def state(db):
    recover(db)
    batches=[dict(r) for r in db.execute('SELECT * FROM batches ORDER BY created DESC')]
    for b in batches:
        b['recipe']=json.loads(b['recipe'])
        b['items']=[dict(r) for r in db.execute('''SELECT i.*,v.profile,c.title,c.filename,c.progress,c.duration,c.status AS clip_status
            FROM batch_items i LEFT JOIN videos v ON v.id=i.source_id LEFT JOIN clips c ON c.id=i.clip_id WHERE batch_id=? ORDER BY i.rowid''',(b['id'],))]
    return {'batches':batches}

def launch(db,batch_id):
    db.execute("UPDATE batches SET status='running',pid=? WHERE id=?",(os.getpid(),batch_id));db.commit()
    try:
        child=subprocess.Popen([sys.executable,str(editor.ROOT/'scripts/editor.py'),'batch-run',batch_id],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        db.execute('UPDATE batches SET pid=? WHERE id=?',(child.pid,batch_id));db.commit()
    except Exception:
        db.execute("UPDATE batches SET status='interrupted' WHERE id=?",(batch_id,));db.commit();raise

def scaled_crop(normalized,meta):
    c={k:int(normalized[k]*meta['width' if k in ('x','width') else 'height']) for k in ('x','y','width','height')}
    c['width']=min(c['width'],meta['width']-c['x']);c['height']=min(c['height'],meta['height']-c['y'])
    x,y,w,h=editor.validate_crop(c,meta)
    return dict(x=x,y=y,width=w,height=h)

def create(db,payload):
    import fcntl
    with open(editor.DATA/'editor-create.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not isinstance(payload,dict):raise ValueError('Lote inválido.')
        request_id=payload.get('requestId')
        if not isinstance(request_id,str) or len(request_id)>80 or not request_id:raise ValueError('Identificador do lote inválido.')
        existing=db.execute('SELECT id FROM batches WHERE request_id=?',(request_id,)).fetchone()
        if existing:return {'id':existing['id']}
        recover(db);editor.recover(db)
        if db.execute("SELECT 1 FROM batches WHERE status='running'").fetchone() or db.execute("SELECT 1 FROM clips WHERE status='rendering'").fetchone():raise ValueError('Aguarde a produção atual terminar antes de iniciar outro lote.')
        ids=payload.get('sourceIds');name=payload.get('name','')
        if not isinstance(ids,list) or not 1<=len(ids)<=500 or any(not isinstance(i,str) for i in ids):raise ValueError('Selecione de 1 a 500 vídeos.')
        ids=list(dict.fromkeys(ids))
        if not isinstance(name,str) or not name.strip() or len(name)>100:raise ValueError('Dê um nome ao lote, com até 100 caracteres.')
        norm=payload.get('normalizedCrop')
        if not isinstance(norm,dict) or any(type(norm.get(k)) not in (int,float) or not math.isfinite(norm[k]) for k in ('x','y','width','height')):raise ValueError('Área de referência inválida.')
        if norm['x']<0 or norm['y']<0 or norm['width']<=0 or norm['height']<=0 or norm['x']+norm['width']>1.000001 or norm['y']+norm['height']>1.000001:raise ValueError('A seleção ultrapassa a imagem de referência.')
        if type(payload.get('muted',False)) is not bool:raise ValueError('Opção de áudio inválida.')
        template=templates.snapshot(db,editor.DATA,payload['template']) if payload.get('template') else None
        for id in ids:editor.source(db,id)
        recipe={'normalizedCrop':norm,'muted':payload.get('muted',False),'template':template}
        id=uuid.uuid4().hex
        db.execute('INSERT INTO batches VALUES (?,?,?,?,?,?,?)',(id,request_id,name.strip(),json.dumps(recipe),'running',os.getpid(),datetime.now(timezone.utc).isoformat()))
        db.executemany("INSERT INTO batch_items (batch_id,source_id,status) VALUES (?,?,'queued')",[(id,v) for v in ids]);db.commit();launch(db,id)
        return {'id':id}

def retry(db,payload):
    import fcntl
    with open(editor.DATA/'editor-create.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);recover(db);editor.recover(db)
        if db.execute("SELECT 1 FROM batches WHERE status='running'").fetchone() or db.execute("SELECT 1 FROM clips WHERE status='rendering'").fetchone():raise ValueError('Aguarde a produção em andamento terminar.')
        id=payload.get('id');b=db.execute('SELECT * FROM batches WHERE id=?',(id,)).fetchone()
        if not b:raise ValueError('Lote não encontrado.')
        db.execute("UPDATE batch_items SET status='queued',error='' WHERE batch_id=? AND status!='completed'",(id,));db.commit();launch(db,id);return {'id':id}

def approve(db,payload):
    if type(payload.get('approved')) is not bool:raise ValueError('Aprovação inválida.')
    row=db.execute('''SELECT i.*,c.status AS clip_status FROM batch_items i JOIN clips c ON c.id=i.clip_id WHERE i.batch_id=? AND i.source_id=?''',(payload.get('batchId'),payload.get('sourceId'))).fetchone()
    if not row or row['clip_status']!='completed':raise ValueError('O vídeo precisa estar pronto antes da revisão.')
    db.execute('UPDATE batch_items SET approved=? WHERE batch_id=? AND source_id=?',(int(payload['approved']),row['batch_id'],row['source_id']));db.commit();return {'ok':True}

def run(db,id):
    import fcntl
    with open(editor.DATA/'batch-worker.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        b=db.execute('SELECT * FROM batches WHERE id=?',(id,)).fetchone()
        if not b:return
        recipe=json.loads(b['recipe'])
        db.execute("UPDATE batches SET status='running',pid=? WHERE id=?",(os.getpid(),id));db.commit()
        for item in db.execute('SELECT * FROM batch_items WHERE batch_id=? ORDER BY rowid',(id,)).fetchall():
            if item['status']=='completed':continue
            try:
                clip=db.execute('SELECT * FROM clips WHERE id=?',(item['clip_id'],)).fetchone() if item['clip_id'] else None
                if clip and clip['status']=='completed':
                    db.execute("UPDATE batch_items SET status='completed',error='' WHERE batch_id=? AND source_id=?",(id,item['source_id']));db.commit();continue
                if not clip:
                    original,file=editor.source(db,item['source_id']);meta=editor.probe(file)
                    crop=scaled_crop(recipe['normalizedCrop'],meta)
                    payload={'sourceId':item['source_id'],'title':(b['name']+' · @'+original['profile'])[:100],'crop':crop,'muted':recipe['muted']}
                    clip=editor.create(db,payload,batch_context=id)
                    if recipe['template']:db.execute('UPDATE clips SET template_json=? WHERE id=?',(json.dumps(recipe['template']),clip['id']))
                    db.execute('UPDATE batch_items SET clip_id=? WHERE batch_id=? AND source_id=?',(clip['id'],id,item['source_id']))
                db.execute("UPDATE clips SET status='rendering',progress=0,error='',pid=? WHERE id=?",(os.getpid(),clip['id']))
                db.execute("UPDATE batch_items SET status='rendering',error='' WHERE batch_id=? AND source_id=?",(id,item['source_id']));db.commit()
                editor.render(db,clip['id'])
                result=db.execute('SELECT * FROM clips WHERE id=?',(clip['id'],)).fetchone()
                if result['status']!='completed':raise ValueError(result['error'] or 'Exportação não concluída.')
                db.execute("UPDATE batch_items SET status='completed',error='' WHERE batch_id=? AND source_id=?",(id,item['source_id']));db.commit()
            except Exception as e:
                error=str(e) if isinstance(e,ValueError) else 'Não foi possível processar este vídeo. Tente retomar o lote.'
                db.execute("UPDATE batch_items SET status='failed',error=? WHERE batch_id=? AND source_id=?",(error,id,item['source_id']));db.commit()
        failed=db.execute("SELECT COUNT(*) FROM batch_items WHERE batch_id=? AND status!='completed'",(id,)).fetchone()[0]
        db.execute('UPDATE batches SET status=? WHERE id=?',('partial' if failed else 'completed',id));db.commit()
