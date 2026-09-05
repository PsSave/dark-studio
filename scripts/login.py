"""Interactive login; credentials are entered only in the local terminal."""
import getpass, json, os
from pathlib import Path
import instaloader
from errors import explain
root = Path(__file__).resolve().parents[1] / '.data'
root.mkdir(exist_ok=True)
os.chmod(root,0o700)
username=input('Seu usuário do Instagram (conta de acesso): ').strip().lstrip('@')
loader=instaloader.Instaloader(quiet=True,max_connection_attempts=1,request_timeout=30)
try:
    try:
        loader.login(username,getpass.getpass('Senha (não será exibida nem salva): '))
    except instaloader.TwoFactorAuthRequiredException:
        loader.two_factor_login(input('Código de autenticação em duas etapas: ').strip())
    session=root/'instagram.session'
    loader.save_session_to_file(str(session))
    os.chmod(session,0o600)
    (root/'instagram.json').write_text(json.dumps({'username':username}))
    os.chmod(root/'instagram.json',0o600)
    print('Sessão salva localmente. Volte ao painel; não é necessário reiniciar o servidor.')
except Exception as error:
    print(explain(error))
    raise SystemExit(1)
