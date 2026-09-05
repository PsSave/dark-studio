# Dark Studio — biblioteca local

Painel Astro para cadastrar um perfil do Instagram e coletar Reels públicos pelo navegador. O coletor usa Chromium/Playwright sem modificar a identidade do navegador ou contornar verificações. Fecha convites dispensáveis de cadastro e baixa a mídia acessível no player. A consulta antiga do Instaloader continua no código como alternativa experimental, mas não é usada pelo botão do painel.

## Instalação no Linux

Requer Python 3.10+, ffmpeg/ffprobe e bibliotecas de sistema do Chromium. O Node compatível fica instalado no projeto.

```sh
npm install
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.data/browsers .venv/bin/python -m playwright install chromium --no-shell
npm run dev -- --port 4321
```

Abra http://127.0.0.1:4321. O servidor é local, sem autenticação; não o exponha à internet.

## Uso

Informe o @ ou link do perfil e escolha 5, 10, 25, 50 ou todos. O padrão é 5. Os links são coletados da página visível e precisam apontar para Reels do perfil informado; publicações colaborativas cujo link pertença a outro perfil não entram nesta versão. A seleção segue a ordem exibida, não uma ordenação garantida por data. Para avançar, o coletor chega ao último Reel carregado e aguarda novos links, em vez de encerrar após pequenos deslocamentos de rolagem. Se a listagem realmente parar, preserva os arquivos e informa quantos foram selecionados em relação ao pedido. Arquivos já concluídos são reutilizados. “No acervo” indica que o arquivo já existe no armazenamento do projeto. Use “Baixar todos (.zip)” para exportar todos os vídeos disponíveis da biblioteca juntos, organizados em pastas por perfil.

O Chromium abre em segundo plano. A coleta fecha convites de login que tenham botão de fechar. Caso o Instagram imponha login, verificação ou limite de consultas, ela não tenta contornar a restrição. “Todos” significa os Reels acessíveis na página; não garante o histórico completo. O resultado é marcado como parcial quando não se confirma a listagem completa.

Os arquivos ficam em `.data/media/`, e o histórico em `.data/library.sqlite`. Tracks de áudio e vídeo separados são reunidos pelo ffmpeg sem recodificação. O ffprobe verifica o vídeo recebido antes de marcá-lo como concluído. Downloads e sessões nunca entram no Git.

## Testes

```sh
npm test
python3 -m unittest discover -s tests -p '*_test.py'
npm run build
```

O teste real com Instagram é separado dos testes locais: disponibilidade e exigências da plataforma podem mudar. Edição, recorte e publicação não fazem parte deste módulo.

Documentação: https://playwright.dev/python/docs/network e https://docs.astro.build/en/guides/integrations-guide/node/
