"""Persistent local clip exports, with validated ranges and accurate re-encoding."""
import json, math, os, re, signal, sqlite3, subprocess, sys, uuid, time
from pathlib import Path
import templates
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
    columns={r[1] for r in db.execute('PRAGMA table_info(clips)')}
    for name in ('crop_x','crop_y','crop_w','crop_h'):
        if name not in columns: db.execute(f'ALTER TABLE clips ADD COLUMN {name} INTEGER')
    if 'template_json' not in columns: db.execute('ALTER TABLE clips ADD COLUMN template_json TEXT')
    db.commit()
    templates.initialize(db)
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

def validate_crop(crop,meta):
    if not isinstance(crop,dict): raise ValueError('Selecione uma área da imagem.')
    values=[crop.get(k) for k in ('x','y','width','height')]
    if any(type(v) is not int for v in values): raise ValueError('As medidas da seleção devem ser números inteiros.')
    x,y,w,h=values
    if x<0 or y<0 or w<2 or h<2 or x+w>meta['width'] or y+h>meta['height']:
        raise ValueError('A seleção deve ficar dentro da imagem e ter pelo menos 2 pixels por lado.')
    return x-x%2,y-y%2,w-w%2,h-h%2

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
        crop=validate_crop(payload['crop'],meta) if 'crop' in payload else None
        if crop: payload={**payload,'start':0,'end':meta['duration']}
        start,end,title,muted=validate(payload,meta['duration'])
        template=templates.snapshot(db,DATA,payload['template']) if payload.get('template') else None
        if template and not crop: raise ValueError('Selecione a área do vídeo antes de aplicar um template.')
        clip_id=uuid.uuid4().hex
        db.execute('INSERT INTO clips (id,source_id,title,start,end,muted,status,filename,created) VALUES (?,?,?,?,?,?,?,?,?)',(clip_id,row['id'],title,start,end,int(muted),'rendering',f'{clip_id}.mp4',datetime.now(timezone.utc).isoformat()));db.commit()
        if template:
            db.execute('UPDATE clips SET template_json=? WHERE id=?',(json.dumps(template),clip_id));db.commit()
        if crop:
            db.execute('UPDATE clips SET crop_x=?,crop_y=?,crop_w=?,crop_h=? WHERE id=?',(*crop,clip_id));db.commit()
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
        template=json.loads(row['template_json']) if row['template_json'] else None
        args=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-ss',str(start),'-i',str(input_file)]
        if template: args+=['-loop','1','-framerate','30','-i',str(templates.asset(DATA,template['filename']))]
        args+=['-t',str(length),'-map','[composed]' if template else '0:v:0']
        args+=['-an'] if muted or not meta['hasAudio'] else ['-map','0:a:0?','-c:a','aac','-b:a','192k']
        crop=validate_crop({'x':row['crop_x'],'y':row['crop_y'],'width':row['crop_w'],'height':row['crop_h']},meta) if row['crop_w'] is not None else None
        video_filter=f'crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},setsar=1' if crop else 'scale=trunc(iw/2)*2:trunc(ih/2)*2'
        if template:
            templates.validate(template,template['width'],template['height'])
            w,h=template['slot_w'],template['slot_h']
            sizing=f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}' if template['fit']=='cover' else f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black'
            graph=f'[0:v]{video_filter},{sizing},setsar=1,setpts=PTS-STARTPTS[game];[1:v]format=rgba,setsar=1,setpts=PTS-STARTPTS[art];'
            if template.get('layer','front')=='behind':
                graph+=f'[game]pad={template["width"]}:{template["height"]}:{template["x"]}:{template["y"]}:black[base];[base][art]overlay=0:0:shortest=1,format=yuv420p[composed]'
            else: graph+=f'[art][game]overlay={template["x"]}:{template["y"]}:shortest=1,format=yuv420p[composed]'
            args+=['-filter_complex_threads','2','-filter_complex',graph,'-r','30']
        else: args+=['-vf',video_filter]
        args+=['-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','2','-map_metadata','-1','-movflags','+faststart','-progress','pipe:1',str(partial)]
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
        if crop and (output['width'],output['height'])!=((template['width'],template['height']) if template else (crop[2],crop[3])): raise ValueError('A imagem exportada não corresponde à área selecionada.')
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
        elif command=='templates': print(json.dumps({'templates':[dict(r) for r in db.execute('SELECT * FROM templates ORDER BY rowid DESC')]}))
        elif command=='template-upload': print(json.dumps(templates.upload(db,DATA,json.load(sys.stdin))))
        elif command=='template-save': print(json.dumps(templates.save(db,json.load(sys.stdin))))
        elif command=='source':
            row,file=source(db,sys.argv[2]);print(json.dumps({**dict(row),**probe(file)}))
        elif command=='create': print(json.dumps(create(db,json.load(sys.stdin))))
        elif command=='render': render(db,sys.argv[2])
    except ValueError as error:
        print(json.dumps({'error':str(error)}));raise SystemExit(2)
