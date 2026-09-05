"""Local collector. SQLite is the source of truth; media never enters the public directory."""
import sys, os, json, sqlite3, re, signal
from pathlib import Path
from errors import explain
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.data'
DATA.mkdir(exist_ok=True)
db = sqlite3.connect(DATA / 'library.sqlite', timeout=10)
db.row_factory = sqlite3.Row
db.executescript('''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, profile TEXT, status TEXT, message TEXT, pid INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS videos (id TEXT PRIMARY KEY, profile TEXT, caption TEXT, published TEXT, source TEXT, status TEXT, filename TEXT, error TEXT);
''')
def now(): return datetime.now(timezone.utc).isoformat()
def update(job, status, message):
    db.execute('UPDATE jobs SET status=?,message=? WHERE id=?', (status,message,job)); db.commit()
def state():
    for job in db.execute("SELECT * FROM jobs WHERE status IN ('scanning','downloading')").fetchall():
        try: os.kill(job['pid'], 0)
        except ProcessLookupError: update(job['id'], 'interrupted', 'Processo interrompido. Você pode retomar a coleta.')
    return {'jobs':[dict(r) for r in db.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 25')], 'videos':[dict(r) for r in db.execute('SELECT * FROM videos ORDER BY published DESC')]}
def run(profile, limit=10):
    import fcntl
    lock = open(DATA/'collector.lock','w')
    try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: return
    job = db.execute('INSERT INTO jobs(profile,status,message,pid,created) VALUES (?,?,?,?,?)',(profile,'scanning','Conectando ao perfil…',os.getpid(),now())).lastrowid
    db.commit()
    def stop(*_):
        update(job,'interrupted','Coleta interrompida. Os arquivos concluídos foram preservados.'); sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    try:
        import instaloader
        loader = instaloader.Instaloader(quiet=True, request_timeout=25, max_connection_attempts=1, download_comments=False, save_metadata=False)
        login, session = os.environ.get('INSTAGRAM_LOGIN'), os.environ.get('INSTAGRAM_SESSION_FILE')
        config = DATA/'instagram.json'
        if not login and config.exists():
            login = json.loads(config.read_text())['username']
            session = str(DATA/'instagram.session')
        if login and session: loader.load_session_from_file(login, session)
        account = instaloader.Profile.from_username(loader.context, profile)
        count = 0
        selected = set()
        listing_errors = []
        def posts():
            for get_items in (account.get_posts, account.get_reels):
                try:
                    yield from get_items()
                except Exception as error:
                    listing_errors.append(error)
        for post in posts():
            nodes = list(post.get_sidecar_nodes()) if post.typename == 'GraphSidecar' else [post]
            for index, node in enumerate(nodes):
                if not node.is_video: continue
                video_id = f'{post.shortcode}_{index}'
                if video_id in selected: continue
                if limit and len(selected) >= limit: break
                selected.add(video_id)
                filename = f'{profile}/{video_id}.mp4'
                target = DATA/'media'/filename
                db.execute('INSERT OR IGNORE INTO videos VALUES (?,?,?,?,?,?,?,?)',(video_id,profile,(post.caption or '')[:10000],post.date_utc.isoformat(),f'https://www.instagram.com/p/{post.shortcode}/','pending',filename,'')); db.commit()
                previous = db.execute('SELECT status FROM videos WHERE id=?',(video_id,)).fetchone()
                if previous['status']=='downloaded' and target.exists(): continue
                count += 1
                update(job,'downloading',f'Baixando vídeo {count}. A varredura continua…')
                db.execute("UPDATE videos SET status='downloading',error='' WHERE id=?",(video_id,)); db.commit()
                try:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    partial = target.with_suffix('.part')
                    response = loader.context.get_raw(node.video_url)
                    try:
                        with open(partial,'wb') as output:
                            for chunk in response.iter_content(chunk_size=262144): output.write(chunk)
                    finally: response.close()
                    if partial.stat().st_size == 0: raise ValueError('Arquivo vazio')
                    partial.replace(target)
                    db.execute("UPDATE videos SET status='downloaded',error='' WHERE id=?",(video_id,))
                except Exception:
                    db.execute("UPDATE videos SET status='failed',error='Não foi possível baixar este vídeo. Retome a coleta para tentar novamente.' WHERE id=?",(video_id,))
                db.commit()
            if limit and len(selected) >= limit: break
        failed = db.execute("SELECT count(*) FROM videos WHERE profile=? AND status!='downloaded'",(profile,)).fetchone()[0]
        if listing_errors:
            update(job,'partial',explain(listing_errors[0]) + ' A listagem ficou incompleta.')
            return
        update(job,'partial' if failed else 'completed',f'Varredura concluída. {failed} vídeo(s) pendente(s).' if failed else (f'Coleta concluída: {len(selected)} vídeo(s). Limite desta coleta: {limit}.' if limit else 'Varredura concluída. Vídeos disponíveis na biblioteca.'))
    except ImportError:
        update(job,'failed','O coletor precisa ser instalado. Consulte a preparação no README.')
    except Exception as error:
        update(job,'failed',explain(error))
if __name__ == '__main__':
    command = sys.argv[1]
    if command=='state': print(json.dumps(state()))
    elif command=='scan':
        profile = sys.argv[2]
        if not re.fullmatch(r'[a-zA-Z0-9_][a-zA-Z0-9_.]{0,29}',profile): raise ValueError('Perfil inválido')
        limit = int(sys.argv[3]) if len(sys.argv)>3 else 10
        if limit not in (0,5,10,25,50): raise ValueError('Limite inválido')
        run(profile.lower(),limit)
