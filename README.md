# Dark Studio

**Reúna referências, edite vídeos com seus templates e baixe criativos prontos para publicar.**

Informe um perfil, escolha a quantidade e acompanhe a coleta no painel. Os arquivos ficam no seu computador e podem ser exportados juntos em ZIP. Esta documentação cobre a **primeira versão com Biblioteca, Editor e Criativos**, disponível na branch `main`. Não há agendamento ou publicação automática: você baixa os resultados e faz as postagens.

## Biblioteca de referência

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

**No acervo significa que o vídeo já está salvo no computador.** O botão de download permite salvar uma cópia pelo navegador. As abas separam os perfis sem apagar os anteriores. Na aba Todos, o ZIP reúne o acervo; ao escolher um perfil, **Baixar perfil (.zip)** reúne os originais daquele perfil. O filtro de status não limita o ZIP.

## 6. Editor: crop e templates

Abra **Editor** na navegação ou **Abrir editor** em um vídeo da biblioteca. Desenhe um retângulo sobre a imagem, mova a seleção e ajuste os cantos. Os campos de posição e tamanho em pixels permitem ajustes precisos. A prévia mostra apenas a área selecionada, mantendo toda a duração do vídeo.

Use **Salvar seleção** para guardar um modelo neste navegador com o nome informado. Ao aplicar em outro vídeo, a área é adaptada proporcionalmente às dimensões da imagem; confira e ajuste antes de exportar. O modelo não identifica o gameplay automaticamente nem acompanha objetos em movimento.

**Salvar em Criativos** cria um MP4 novo, com áudio opcional, preservando o original. Os recortes ficam em `.data/clips/`, com histórico em `.data/library.sqlite`. A exportação usa dimensões e coordenadas pares, ajustando no máximo um pixel para compatibilidade. O ZIP da biblioteca contém os originais. Na seção **Templates de composição**, importe uma arte PNG, JPG ou WebP de até 20 MB. Ela é preparada em 1080 × 1920 sem distorção, com margens quando necessário. O gameplay ocupa o espaço retangular que você desenha, move e redimensiona. A ordem padrão é **Arte por cima · vídeo por trás**: preserve transparência no PNG para abrir a janela do vídeo. Assim a moldura pode cobrir as bordas do gameplay. Também há a opção de colocar o vídeo por cima da arte. Use **Preencher** para ocupar todo o espaço cortando sobras, ou **Mostrar tudo** para preservar o recorte inteiro com margens pretas.

**Salvar template** guarda nome, imagem e encaixe no computador, em `.data/templates/` e no SQLite. Escolha esse template nos próximos vídeos para reutilizá-lo. A prévia mostra a composição durante a reprodução; **Salvar em Criativos** gera o MP4 vertical completo. **Sem template** volta a exportar apenas o recorte. As configurações usadas ficam registradas em cada exportação. Não há integração de conta Canva: envie a imagem exportada de lá. Esta versão usa uma arte estática e um espaço retangular, sem deformação de perspectiva. O canal alfa da arte permite bordas e janelas de formatos irregulares.

## 7. Criativos e produção em lote

No Editor, configure a seleção do vídeo e, se desejar, um template. Use **Aplicar a outros vídeos** para abrir as prévias paginadas do acervo. Selecione vídeos individualmente ou todos de um perfil, dê um nome ao lote e confirme a produção. A seleção do vídeo é adaptada proporcionalmente às dimensões de cada original; as prévias mostram um quadro e não garantem o enquadramento em toda a duração.

A tela **Criativos** acompanha uma fila sequencial, com vídeos prontos, pendentes e falhas, agrupados por lote e pelo template usado. **Retomar pendentes** reutiliza os resultados concluídos e tenta os restantes novamente. A receita da edição fica registrada no lote, incluindo a arte e a ordem das camadas. Envios repetidos da mesma confirmação não criam lotes duplicados.

Abra **Revisar vídeo** para assistir e marcar o resultado como aprovado. A aprovação pode ser retirada. Baixe cada arquivo ou use **Baixar lote (.zip)** para reunir os concluídos. Os originais do acervo continuam preservados, e a biblioteca mantém seu ZIP separado. Se fechar o computador durante a produção, o lote pode ser retomado depois. Agendamento e publicação no Instagram ainda não estão implementados; aprovar não publica o vídeo.


### Corrigir um criativo individual

Em Criativos, clique em **Ajustar no editor**. A seleção, o template e o áudio usados são carregados para você corrigir. Clique em **Salvar nova versão**: o vídeo anterior continua disponível até a exportação terminar. Quando pronta, a nova versão substitui aquele item e volta para revisão; o arquivo anterior permanece no histórico de exportações. Os demais criativos não mudam.

Você também pode editar um único vídeo e clicar em **Salvar em Criativos**, sem criar um lote. Use os filtros de revisão e aprovação para organizar os resultados. Aprovar é apenas uma marca de revisão local.

### Onde ficam os arquivos?

Dentro da pasta `dark-studio`:

```text
.data/
├── media/             # Vídeos organizados por perfil
├── clips/             # Criativos e histórico de exportações
├── templates/         # Artes importadas
├── library.sqlite     # Biblioteca, templates e lotes
└── browsers/          # Chromium usado pelo coletor
```

A pasta `.data` é oculta. No gerenciador de arquivos do Linux, use **Ctrl+H** para mostrá-la. No Windows, execute no terminal Ubuntu:

```bash
cd ~/dark-studio
explorer.exe .data
```

Isso abre a pasta no Explorador do Windows. Vídeos, banco de dados e sessões ficam fora do Git. Com coletas e exportações encerradas, copie a pasta `.data/` para guardar o acervo, templates, criativos e histórico. As seleções rápidas salvas no navegador ficam no armazenamento local desse navegador.

## Limites e dúvidas frequentes

**Pedi 50, mas chegaram menos.** A página pode parar de carregar ou exigir login. O painel informa que a listagem ficou incompleta e mantém os arquivos obtidos. Uma nova coleta reaproveita os concluídos. Quantidades maiores não são garantidas.

**“Todos” baixa o perfil inteiro?** Significa todos os Reels que a página permitir acessar durante aquela coleta. Não há garantia do histórico completo. A ordem é a exibida pelo Instagram; vídeos colaborativos cujo link pertença a outro perfil ficam fora desta versão.

**Apareceu login, verificação ou limite de consultas.** Convites que permitem fechar são dispensados. Se o Instagram exigir autenticação ou bloquear o acesso, o coletor não contorna a restrição. Tente mais tarde; o fluxo atual do painel não configura uma sessão autenticada. O script antigo de login é experimental e não conecta uma sessão ao coletor do navegador.

**O Chromium não iniciou.** Repita o último comando da etapa 3 para instalar o navegador e as bibliotecas necessárias. Veja a [documentação do Playwright](https://playwright.dev/python/docs/browsers).

**O painel não abriu.** Confira se o terminal continua executando o servidor e qual endereço foi mostrado. Se a porta estiver ocupada, o Astro pode escolher outra. No WSL, veja o [guia de acesso pelo localhost](https://learn.microsoft.com/windows/wsl/networking).

**`nvm` ou `npm` não foi encontrado.** Abra um novo terminal Ubuntu, execute `source ~/.bashrc` e depois `nvm use 22`. No Windows, confirme que está usando o Ubuntu.

**Falhou ao salvar ou gerar ZIP.** Confira o espaço disponível em disco. O ZIP usa espaço adicional aos vídeos originais.

Use os vídeos respeitando as permissões de uso dos criadores.

## Atualizar o projeto

Pare o painel depois que as coletas e exportações terminarem e execute dentro do projeto:

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
