"""Persistent local clip exports, with validated ranges and accurate re-encoding."""
import json, math, os, re, signal, sqlite3, subprocess, sys, uuid, time
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'.data'
DATA.mkdir(exist_ok=True)
def connect():
    db=sqlite3.connect(DATA/'library.sqlite',timeout=10);db.row_factory=sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS clips (
        id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL,
        start REAL NOT NULL, end REAL NOT NULL, muted INTEGER NOT NULL,
        status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
        filename TEXT, error TEXT NOT NULL DEFAULT '', pid INTEGER,
        created TEXT NOT NULL, duration REAL, size INTEGER)''');db.commit()
    return db

def probe(file):
    p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)],capture_output=True,text=True,timeout=20)
    if p.returncode: raise ValueError('Não foi possível ler o vídeo de origem.')
    data=json.loads(p.stdout);video=next((s for s in data['streams'] if s['codec_type']=='video'),None)
    if not video: raise ValueError('O arquivo de origem não contém vídeo.')
    return {'duration':float(data['format'].get('duration',0)), 'width':video.get('width',0),'height':video.get('height',0),'hasAudio':any(s['codec_type']=='audio' for s in data['streams'])}

def source(db, source_id):
    row=db.execute("SELECT * FROM videos WHERE id=? AND status='downloaded'",(source_id,)).fetchone()
    if not row: raise ValueError('Selecione um vídeo disponível no acervo.')
    file=(DATA/'media'/row['filename']).resolve()
    if not file.is_relative_to((DATA/'media').resolve()) or not file.is_file(): raise ValueError('O vídeo de origem não está mais na pasta do acervo.')
    return row,file

def validate(payload,duration):
    if not isinstance(payload,dict): raise ValueError('Configuração de recorte inválida.')
    start,end=payload.get('start'),payload.get('end')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end)):
        raise ValueError('Informe início e fim em segundos.')
    if start<0 or end>duration+0.02 or end-start<0.2-1e-8:
        raise ValueError('O trecho deve ter pelo menos 0,2 segundo e ficar dentro da duração do vídeo.')
    title=payload.get('title','Recorte')
    if not isinstance(title,str) or not title.strip() or len(title)>100: raise ValueError('Use um nome de 1 a 100 caracteres para o recorte.')
    muted=payload.get('muted',False)
    if type(muted) is not bool: raise ValueError('Opção de áudio inválida.')
    return max(0,start),min(end,duration),title.strip(),muted

def recover(db):
    for row in db.execute("SELECT id,pid FROM clips WHERE status='rendering'").fetchall():
        if row['pid']:
            try: os.kill(row['pid'],0)
            except ProcessLookupError:
                db.execute("UPDATE clips SET status='interrupted',error='A exportação foi interrompida. Abra este recorte e exporte novamente.' WHERE id=?",(row['id'],))
    db.commit()

def create(db,payload):
    import fcntl
    with open(DATA/'editor-create.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        recover(db)
        if db.execute("SELECT 1 FROM clips WHERE status='rendering'").fetchone(): raise ValueError('Aguarde a exportação em andamento terminar.')
        if not isinstance(payload,dict) or not isinstance(payload.get('sourceId'),str): raise ValueError('Selecione um vídeo do acervo.')
        row,file=source(db,payload['sourceId']);meta=probe(file)
        start,end,title,muted=validate(payload,meta['duration'])
        clip_id=uuid.uuid4().hex
        db.execute('INSERT INTO clips (id,source_id,title,start,end,muted,status,filename,created) VALUES (?,?,?,?,?,?,?,?,?)',(clip_id,row['id'],title,start,end,int(muted),'rendering',f'{clip_id}.mp4',datetime.now(timezone.utc).isoformat()));db.commit()
        try:
            child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'render',clip_id],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            db.execute('UPDATE clips SET pid=? WHERE id=?',(child.pid,clip_id));db.commit()
        except Exception:
            db.execute("UPDATE clips SET status='failed',error='Não foi possível iniciar a exportação.' WHERE id=?",(clip_id,));db.commit();raise
        return dict(db.execute('SELECT * FROM clips WHERE id=?',(clip_id,)).fetchone())

def render(db,clip_id):
    row=db.execute('SELECT * FROM clips WHERE id=?',(clip_id,)).fetchone()
    if not row or row['status']!='rendering': return
    folder=DATA/'clips';folder.mkdir(exist_ok=True)
    file=folder/row['filename'];partial=file.with_suffix('.part.mp4')
    encoder=None
    def stop(*_):
        if encoder: encoder.terminate()
        db.execute("UPDATE clips SET status='interrupted',error='Exportação interrompida. Os vídeos originais foram preservados.' WHERE id=?",(clip_id,));db.commit()
        partial.unlink(missing_ok=True);raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop)
    try:
        original,input_file=source(db,row['source_id']);meta=probe(input_file)
        start,end,_,muted=validate({'start':row['start'],'end':row['end'],'title':row['title'],'muted':bool(row['muted'])},meta['duration'])
        length=end-start
        args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-ss',str(start),'-i',str(input_file),'-t',str(length),'-map','0:v:0']
        args+=['-an'] if muted or not meta['hasAudio'] else ['-map','0:a:0?','-c:a','aac','-b:a','192k']
        args+=['-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2','-threads','2','-map_metadata','-1','-movflags','+faststart','-progress','pipe:1',str(partial)]
        encoder=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        last=-1
        for line in encoder.stdout:
            if line.startswith('out_time_us='):
                try: progress=min(99,max(0,int(float(line.split('=',1)[1])/1000000/length*100)))
                except ValueError: continue
                if progress!=last:
                    db.execute('UPDATE clips SET progress=? WHERE id=?',(progress,clip_id));db.commit();last=progress
        if encoder.wait()!=0: raise ValueError('O processamento do recorte falhou. Confira o espaço em disco e tente novamente.')
        output=probe(partial)
        if abs(output['duration']-length)>0.25: raise ValueError('A duração exportada não corresponde ao trecho selecionado.')
        if not muted and meta['hasAudio'] and not output['hasAudio']: raise ValueError('O áudio não foi preservado na exportação.')
        partial.replace(file)
        db.execute("UPDATE clips SET status='completed',progress=100,duration=?,size=?,error='' WHERE id=?",(output['duration'],file.stat().st_size,clip_id));db.commit()
    except Exception as error:
        partial.unlink(missing_ok=True)
        message=str(error) if isinstance(error,ValueError) else 'Não foi possível exportar o recorte. O vídeo original foi preservado.'
        db.execute("UPDATE clips SET status='failed',error=? WHERE id=?",(message,clip_id));db.commit()
    finally:
        if encoder and encoder.poll() is None: encoder.kill();encoder.wait()
        if encoder and encoder.stdout: encoder.stdout.close()

if __name__=='__main__':
    db=connect()
    try:
        command=sys.argv[1]
        if command=='state':
            recover(db);print(json.dumps({'clips':[dict(r) for r in db.execute('SELECT * FROM clips ORDER BY created DESC')]}))
        elif command=='source':
            row,file=source(db,sys.argv[2]);print(json.dumps({**dict(row),**probe(file)}))
        elif command=='create': print(json.dumps(create(db,json.load(sys.stdin))))
        elif command=='render': render(db,sys.argv[2])
    except ValueError as error:
        print(json.dumps({'error':str(error)}));raise SystemExit(2)
