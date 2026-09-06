# Dark Studio

**Uma biblioteca local para reunir Reels públicos do Instagram e baixar os vídeos pelo navegador.**

Informe um perfil, escolha a quantidade e acompanhe a coleta no painel. Os arquivos ficam no seu computador e podem ser exportados juntos em ZIP. Esta documentação cobre a **primeira versão — módulo 1**, disponível na branch `main`.

## O que o módulo 1 faz

- Recebe um @ ou link de perfil do Instagram.
- Permite solicitar 5, 10, 25, 50 vídeos ou todos os acessíveis.
- Lista Reels públicos pelo Chromium em segundo plano.
- Mostra progresso, histórico, falhas e resultados parciais.
- Salva vídeos no acervo local e reaproveita arquivos já concluídos.
- Reúne áudio e imagem quando chegam separados e verifica os arquivos.
- Oferece download individual e **Baixar todos (.zip)**.

O projeto roda localmente. Não precisa de hospedagem, Docker ou chave de API para esse fluxo. A disponibilidade dos vídeos depende do Instagram.

## Escolha seu sistema

| Sistema | Como executar esta versão |
| --- | --- |
| Linux | Diretamente no terminal. O passo a passo abaixo usa Ubuntu 24.04. |
| Windows 10/11 | Dentro do Ubuntu pelo WSL 2, com o painel aberto no navegador do Windows. |

**Windows nativo (PowerShell/CMD) ainda não é suportado:** o coletor utiliza recursos do Linux. O caminho pelo WSL evita alterar o código. A execução foi testada em Linux; o roteiro WSL segue a documentação oficial, mas ainda não foi testado em uma máquina Windows neste projeto.

## 1. Preparar o Windows (somente para Windows)

Se você usa Linux, vá para a etapa 2.

1. Abra **PowerShell como administrador** pelo menu Iniciar.
2. Execute:

```powershell
wsl --install -d Ubuntu-24.04
```

3. Reinicie o computador se solicitado.
4. Abra **Ubuntu 24.04** pelo menu Iniciar e crie o usuário e a senha pedidos. A senha não aparece enquanto você digita; isso é normal.
5. Execute todas as próximas etapas **no terminal Ubuntu**, não no PowerShell.

Se já tem Ubuntu 24.04 no WSL 2, use sua instalação existente. Consulte o [guia oficial de instalação do WSL](https://learn.microsoft.com/windows/wsl/install) se o comando não funcionar. Ele informa também os requisitos de versão do Windows.

## 2. Instalar os requisitos (Linux ou Ubuntu no WSL)

No terminal Ubuntu, execute um bloco por vez. Se algum comando falhar, resolva o erro antes de continuar.

```bash
sudo apt update
sudo apt install -y git curl ca-certificates python3 python3-venv ffmpeg
```

Instale o Node.js 22 usando o [nvm oficial](https://github.com/nvm-sh/nvm#installing-and-updating). O comando abaixo baixa e executa o instalador do nvm:

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.7/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
```

Confira os programas:

```bash
node --version
npm --version
python3 --version
ffmpeg -version
ffprobe -version
```

Use Node 22.22 ou posterior da linha 22 e Python 3.10 ou posterior. O projeto também instala sua versão compatível do Node nas dependências. Em outras distribuições Linux, instale os pacotes equivalentes pelo gerenciador da distribuição; os comandos `apt` acima são para Ubuntu/Debian. As dependências do Chromium podem variar.

## 3. Baixar e instalar o projeto

```bash
cd ~
git clone --branch main --single-branch https://github.com/PsSave/dark-studio.git
cd dark-studio
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.data/browsers .venv/bin/python -m playwright install --with-deps chromium --no-shell
```

O último comando instala o navegador e suas bibliotecas de sistema, podendo pedir sua senha. Reserve espaço para as dependências, o navegador e os vídeos; a primeira instalação baixa centenas de megabytes. No WSL, mantenha o projeto nessa pasta do Ubuntu para evitar problemas de desempenho e permissões.

## 4. Abrir o painel

Dentro da pasta do projeto:

```bash
npm run dev -- --port 4321
```

Abra **[http://localhost:4321](http://localhost:4321)** no navegador. No Windows, pode usar seu Chrome ou Edge normalmente. Mantenha o terminal aberto enquanto utiliza o painel.

Para parar o painel, pressione **Ctrl+C** nesse terminal. Aguarde a coleta terminar antes de encerrar: o coletor trabalha como um processo separado. Para abrir novamente em outro momento:

```bash
cd ~/dark-studio
npm run dev -- --port 4321
```

O servidor é local e não tem autenticação. Mantenha-o acessível apenas no próprio computador.

## 5. Fazer a primeira coleta

1. Informe o @ ou o link de um perfil público.
2. Escolha **5 vídeos** para começar.
3. Clique em **Buscar e baixar** e acompanhe o resultado.
4. Confira os vídeos que aparecem **No acervo**.
5. Use o download individual ou **Baixar todos (.zip)**.

**No acervo significa que o vídeo já está salvo no computador.** O botão de download permite salvar uma cópia pelo navegador. O ZIP inclui todos os vídeos disponíveis da biblioteca, organizados por perfil, e não somente os da última coleta ou do filtro visível. Adicionar outro perfil mantém os anteriores no acervo. Nesta versão, os perfis aparecem juntos no painel e ficam separados por pastas no disco.

### Onde ficam os arquivos?

Dentro da pasta `dark-studio`:

```text
.data/
├── media/             # Vídeos organizados por perfil
├── library.sqlite     # Histórico da biblioteca
└── browsers/          # Chromium usado pelo coletor
```

A pasta `.data` é oculta. No gerenciador de arquivos do Linux, use **Ctrl+H** para mostrá-la. No Windows, execute no terminal Ubuntu:

```bash
cd ~/dark-studio
explorer.exe .data
```

Isso abre a pasta no Explorador do Windows. Vídeos, banco de dados e sessões ficam fora do Git. Faça uma cópia de `.data/media/` e `.data/library.sqlite` se quiser guardar um backup do acervo e histórico.

## Limites e dúvidas frequentes

**Pedi 50, mas chegaram menos.** A página pode parar de carregar ou exigir login. O painel informa que a listagem ficou incompleta e mantém os arquivos obtidos. Uma nova coleta reaproveita os concluídos. Quantidades maiores não são garantidas.

**“Todos” baixa o perfil inteiro?** Significa todos os Reels que a página permitir acessar durante aquela coleta. Não há garantia do histórico completo. A ordem é a exibida pelo Instagram; vídeos colaborativos cujo link pertença a outro perfil ficam fora desta versão.

**Apareceu login, verificação ou limite de consultas.** Convites que permitem fechar são dispensados. Se o Instagram exigir autenticação ou bloquear o acesso, o coletor não contorna a restrição. Tente mais tarde; o fluxo atual do painel não configura uma sessão autenticada. O script antigo de login é experimental e não conecta uma sessão ao coletor do navegador.

**O Chromium não iniciou.** Repita o último comando da etapa 3 para instalar o navegador e as bibliotecas necessárias. Veja a [documentação do Playwright](https://playwright.dev/python/docs/browsers).

**O painel não abriu.** Confira se o terminal continua executando o servidor e qual endereço foi mostrado. Se a porta estiver ocupada, o Astro pode escolher outra. No WSL, veja o [guia de acesso pelo localhost](https://learn.microsoft.com/windows/wsl/networking).

**`nvm` ou `npm` não foi encontrado.** Abra um novo terminal Ubuntu, execute `source ~/.bashrc` e depois `nvm use 22`. No Windows, confirme que está usando o Ubuntu.

**Falhou ao salvar ou gerar ZIP.** Confira o espaço disponível em disco. O ZIP usa espaço adicional aos vídeos originais.

Use os vídeos respeitando as permissões de uso dos criadores.

## Atualizar a primeira versão

Pare o painel depois que a coleta terminar e execute dentro do projeto:

```bash
git pull --ff-only
npm ci
.venv/bin/python -m pip install -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.data/browsers .venv/bin/python -m playwright install --with-deps chromium --no-shell
npm run dev -- --port 4321
```

## Para quem desenvolve

O painel usa Astro; a coleta usa Python, Playwright e Chromium; os arquivos são verificados com FFmpeg/ffprobe e o histórico fica em SQLite.

```bash
npm test
.venv/bin/python -m unittest discover -s tests -p '*_test.py'
npm run build
```

Os testes locais não dependem de uma coleta real no Instagram. Nesta primeira versão, foram verificados lotes de até 50 vídeos em um perfil público; isso não garante o mesmo acesso em todos os perfis.
