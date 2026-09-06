"""Local template assets and editable video placement, independent from source crop."""
import json, re, subprocess, uuid
from pathlib import Path

def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, filename TEXT NOT NULL,
    width INTEGER NOT NULL, height INTEGER NOT NULL,
    x INTEGER NOT NULL,y INTEGER NOT NULL,slot_w INTEGER NOT NULL,slot_h INTEGER NOT NULL,
    fit TEXT NOT NULL DEFAULT 'cover')''');db.commit()
    if 'layer' not in {r[1] for r in db.execute('PRAGMA table_info(templates)')}:
        db.execute("ALTER TABLE templates ADD COLUMN layer TEXT NOT NULL DEFAULT 'behind'");db.commit()

def as_dict(row):
    return dict(row)

def validate(payload, width=1080,height=1920):
    name=payload.get('name') if isinstance(payload,dict) else None
    if not isinstance(name,str) or not name.strip() or len(name)>100: raise ValueError('Informe um nome de até 100 caracteres para o template.')
    values=[payload.get(k) for k in ('x','y','slot_w','slot_h')]
    if any(type(v) is not int for v in values): raise ValueError('Informe posição e tamanho em pixels inteiros.')
    x,y,w,h=values
    if x<0 or y<0 or w<2 or h<2 or x+w>width or y+h>height: raise ValueError('O espaço do vídeo deve ficar dentro da arte.')
    if payload.get('layer','behind') not in ('behind','front'): raise ValueError('Ordem de camadas inválida.')
    fit=payload.get('fit','cover')
    if fit not in ('cover','contain'): raise ValueError('Modo de encaixe inválido.')
    return name.strip(),x-x%2,y-y%2,w-w%2,h-h%2,fit

def asset(data,filename):
    root=(data/'templates').resolve();file=(root/filename).resolve()
    if not file.is_relative_to(root) or not file.is_file(): raise ValueError('A arte do template não está disponível.')
    return file

def get(db,template_id):
    row=db.execute('SELECT * FROM templates WHERE id=?',(template_id,)).fetchone()
    if not row: raise ValueError('Template não encontrado.')
    return dict(row)

def upload(db,data,payload):
    token=payload.get('token','')
    if not isinstance(token,str) or not re.fullmatch(r'[0-9a-f]{32}',token): raise ValueError('Arquivo de template inválido.')
    name=payload.get('name','Meu template')
    if not isinstance(name,str) or not name.strip() or len(name)>100: raise ValueError('Informe um nome de até 100 caracteres.')
    incoming=data/'template-inbox'/token
    folder=data/'templates';folder.mkdir(exist_ok=True)
    template_id=uuid.uuid4().hex;output=folder/(template_id+'.png')
    try:
        with incoming.open('rb') as f: header=f.read(12)
        if not (header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'\xff\xd8\xff') or (header[:4]==b'RIFF' and header[8:]==b'WEBP')):
            raise ValueError('Envie uma imagem PNG, JPG ou WebP.')
        result=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(incoming)],capture_output=True,text=True,timeout=10)
        if result.returncode: raise ValueError('Não foi possível ler a imagem.')
        stream=json.loads(result.stdout)['streams'][0]
        if stream.get('width',0)*stream.get('height',0)>25000000: raise ValueError('Use uma imagem de até 25 megapixels.')
        args=['ffmpeg','-v','error','-i',str(incoming),'-vf','format=rgba,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x00000000','-frames:v','1','-threads','1',str(output)]
        result=subprocess.run(args,capture_output=True,timeout=20)
        if result.returncode: raise ValueError('Não foi possível preparar essa imagem.')
        db.execute('INSERT INTO templates (id,name,filename,width,height,x,y,slot_w,slot_h,fit) VALUES (?,?,?,?,?,?,?,?,?,?)',(template_id,name.strip(),output.name,1080,1920,108,600,864,648,'cover'));db.commit()
        return get(db,template_id)
    except Exception:
        output.unlink(missing_ok=True);raise
    finally: incoming.unlink(missing_ok=True)

def save(db,payload):
    current=get(db,payload.get('id'))
    name,x,y,w,h,fit=validate(payload,current['width'],current['height'])
    db.execute('UPDATE templates SET name=?,x=?,y=?,slot_w=?,slot_h=?,fit=?,layer=? WHERE id=?',(name,x,y,w,h,fit,payload.get('layer',current['layer']),current['id']));db.commit()
    return get(db,current['id'])

def snapshot(db,data,payload):
    current=get(db,payload.get('id'))
    _,x,y,w,h,fit=validate({**current,**payload},current['width'],current['height'])
    asset(data,current['filename'])
    return {**current,'x':x,'y':y,'slot_w':w,'slot_h':h,'fit':fit,'layer':payload.get('layer',current['layer'])}
