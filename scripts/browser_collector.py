"""Collect publicly visible Instagram videos using ordinary browser navigation."""
import sys, os, re, json, signal, subprocess, time
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from collector import DATA, db, now, update
from errors import explain

def dismiss(page):
    for _ in range(3):
        button = page.get_by_role('button', name=re.compile(r'^(Close|Fechar)$',re.I))
        if not button.count() or not button.first.is_visible(): break
        button.first.click(timeout=2000)
        page.wait_for_timeout(350)

def inspect_file(path):
    result = subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,timeout=20)
    if result.returncode: return None
    return json.loads(result.stdout)

def whole_url(url):
    parsed=urlparse(url)
    return urlunparse(parsed._replace(query=urlencode([(k,v) for k,v in parse_qsl(parsed.query,keep_blank_values=True) if k.lower() not in ('bytestart','byteend')])))

def collect(profile, limit):
    import fcntl
    lock=open(DATA/'collector.lock','w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: return
    job=db.execute('INSERT INTO jobs(profile,status,message,pid,created) VALUES (?,?,?,?,?)',(profile,'scanning','Abrindo o perfil no navegador…',os.getpid(),now())).lastrowid;db.commit()
    browser=None
    def stop(*_):
        update(job,'interrupted','Coleta interrompida. Vídeos concluídos foram preservados.')
        if browser: browser.close()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,channel="chromium")
            context=browser.new_context(locale='en-US')
            page=context.new_page()
            page.set_default_timeout(20000)
            result=page.goto(f'https://www.instagram.com/{profile}/',wait_until='domcontentloaded')
            if result and result.status in (401,403,429): raise RuntimeError(f'Instagram HTTP {result.status}')
            page.wait_for_timeout(1800); dismiss(page)
            if '/accounts/login' in page.url: raise RuntimeError('401 LoginRequired')
            links=[]; unchanged=0; exhausted=False
            for _ in range(200):
                found=page.locator('a[href]').evaluate_all('(anchors) => anchors.map(a=>a.href)')
                old=len(links)
                update(job,'scanning',f'Listando vídeos: {len(links)} encontrados; aguardando novas publicações…')
                for href in found:
                    parsed=urlparse(href)
                    if parsed.hostname not in ('www.instagram.com','instagram.com'): continue
                    if not re.fullmatch(r'/'+re.escape(profile)+r'/reel/[A-Za-z0-9_-]+/?',parsed.path,re.I): continue
                    clean='https://www.instagram.com'+parsed.path
                    if clean not in links: links.append(clean)
                checkpoint=DATA/'collections'/f'{profile}.json'
                checkpoint.parent.mkdir(exist_ok=True)
                checkpoint.with_suffix('.tmp').write_text(json.dumps({'profile':profile,'links':links,'requested':limit,'updated':now()}))
                checkpoint.with_suffix('.tmp').replace(checkpoint)
                if limit and len(links)>=limit: links=links[:limit];break
                unchanged=unchanged+1 if len(links)==old else 0
                if unchanged>=4: exhausted=True;break
                more=page.get_by_role('button',name=re.compile(r'Show more posts|Mostrar mais publica',re.I))
                if more.count() and more.first.is_visible(): more.first.click()
                else:
                    # A fixed wheel step can stop above the end of a growing grid.
                    # Reach the last loaded Reel before waiting for the next page.
                    last_reel=page.locator('a[href*="/reel/"]').last
                    if last_reel.count(): last_reel.scroll_into_view_if_needed(timeout=5000)
                    page.mouse.wheel(0,1000)
                dismiss(page)
                try:
                    page.wait_for_function('''({profile, known}) => {
                        const seen = new Set(known);
                        return Array.from(document.querySelectorAll('a[href]')).some(a => {
                            const u = new URL(a.href);
                            return u.pathname.toLowerCase().startsWith('/' + profile + '/reel/') && !seen.has('https://www.instagram.com' + u.pathname);
                        });
                    }''', arg={'profile':profile,'known':links}, timeout=15000)
                except Exception:
                    dismiss(page)
                dismiss(page)
            else:
                exhausted=True
            if not links:
                update(job,'failed','Nenhum Reel acessível foi encontrado na página. O Instagram pode exigir login ou o perfil pode não ter Reels públicos.');return
            update(job,'downloading',f'{len(links)} vídeos encontrados. Preparando downloads…')
            errors=0
            for index,link in enumerate(links):
                code=urlparse(link).path.rstrip('/').split('/')[-1]; video_id=f'{code}_0'
                filename=f'{profile}/{video_id}.mp4'; target=DATA/'media'/filename
                db.execute('INSERT OR IGNORE INTO videos VALUES (?,?,?,?,?,?,?,?)',(video_id,profile,'',now(),link,'pending',filename,'')); db.commit()
                existing=db.execute('SELECT status FROM videos WHERE id=?',(video_id,)).fetchone()
                if existing['status']=='downloaded' and target.exists(): continue
                update(job,'downloading',f'Baixando {index+1} de {len(links)} vídeos…')
                db.execute("UPDATE videos SET status='downloading',error='' WHERE id=?",(video_id,));db.commit()
                video_page=context.new_page(); media=[]
                def received(response):
                    try:
                        kind=response.headers.get('content-type','').lower()
                        if response.status in (200,206) and ('video/mp4' in kind or 'audio/mp4' in kind):
                            url=whole_url(response.url)
                            if url not in media: media.append(url)
                    except Exception: pass
                video_page.on('response',received)
                parts=[]
                try:
                    response=video_page.goto(link,wait_until='domcontentloaded')
                    if response and response.status in (401,403,429): raise RuntimeError(f'Instagram HTTP {response.status}')
                    video_page.wait_for_timeout(1600);dismiss(video_page)
                    player=video_page.locator('video').first
                    player.wait_for(state='attached',timeout=12000)
                    player.evaluate('(v)=>{v.muted=true;v.play().catch(()=>{});}')
                    video_page.wait_for_timeout(3500)
                    duration=player.evaluate('(v)=>Number.isFinite(v.duration)?v.duration:0')
                    caption=video_page.locator('meta[property="og:description"]').get_attribute('content') or ''
                    published=video_page.locator('time[datetime]').first.get_attribute('datetime') if video_page.locator('time[datetime]').count() else now()
                    target.parent.mkdir(parents=True,exist_ok=True)
                    for number,url in enumerate(media[:6]):
                        host=urlparse(url).hostname or ''
                        if not (host.endswith('.cdninstagram.com') or host.endswith('.fbcdn.net')): continue
                        response=context.request.get(url,timeout=30000)
                        if not response.ok: continue
                        part=target.with_suffix(f'.track{number}.mp4');part.write_bytes(response.body());response.dispose();parts.append(part)
                    info=[(file,inspect_file(file)) for file in parts]
                    videos=[(file,data) for file,data in info if data and any(s['codec_type']=='video' for s in data['streams'])]
                    audios=[(file,data) for file,data in info if data and any(s['codec_type']=='audio' for s in data['streams'])]
                    if not videos: raise RuntimeError('Mídia incompleta: nenhum arquivo de vídeo válido foi recebido.')
                    source,details=max(videos,key=lambda item:max((s.get('width',0)*s.get('height',0) for s in item[1]['streams']),default=0))
                    actual=float(details['format'].get('duration',0))
                    if duration and actual<duration-1: raise RuntimeError('O arquivo recebido está incompleto.')
                    partial=target.with_suffix('.part.mp4')
                    if any(s['codec_type']=='audio' for s in details['streams']) or not audios:
                        source.replace(partial)
                    else:
                        subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-i',str(audios[0][0]),'-map','0:v:0','-map','1:a:0','-c','copy',str(partial)],check=True,timeout=45,capture_output=True)
                    verified=inspect_file(partial)
                    if not verified: raise RuntimeError('Não foi possível validar o arquivo final.')
                    partial.replace(target)
                    db.execute("UPDATE videos SET status='downloaded',error='',caption=?,published=? WHERE id=?",(caption[:10000],published,video_id));db.commit()
                except Exception as error:
                    errors+=1
                    message=explain(error)
                    if isinstance(error,RuntimeError) and str(error).startswith(('Mídia','O arquivo','Não foi')): message=str(error)
                    db.execute("UPDATE videos SET status='failed',error=? WHERE id=?",(message,video_id));db.commit()
                    if '429' in str(error):
                        update(job,'partial',message);return
                finally:
                    video_page.close()
                    for part in parts: part.unlink(missing_ok=True)
            status='partial' if errors or exhausted else 'completed'
            message=f'Coleta encerrada: {len(links)-errors} vídeos disponíveis, {errors} falhas.'
            if limit: message+=f' Selecionados {len(links)} de {limit} solicitados.'
            if exhausted: message+=' A página não carregou mais Reels durante a espera. A listagem ficou incompleta; isso não confirma exigência de login.'
            update(job,status,message)
            browser.close();browser=None
    except Exception as error:
        message=explain(error)
        if 'Executable doesn' in str(error): message='O navegador do coletor precisa ser instalado. Execute a preparação indicada no README.'
        (DATA/'browser-error.json').write_text(json.dumps({'type':type(error).__name__,'message':str(error)[:2000]}))
        update(job,'failed',message)
    finally:
        if browser:
            try: browser.close()
            except Exception: pass

if __name__=='__main__':
    profile=sys.argv[1].lower();limit=int(sys.argv[2])
    if not re.fullmatch(r'[a-z0-9_][a-z0-9_.]{0,29}',profile) or limit not in (0,5,10,25,50): raise SystemExit('Entrada inválida')
    collect(profile,limit)
