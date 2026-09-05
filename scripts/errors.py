def explain(error):
    """Classify wrapped provider errors without exposing URLs, cookies or credentials."""
    chain = []
    current = error
    while current and len(chain) < 8:
        chain.append(type(current).__name__ + ' ' + str(current))
        current = current.__cause__ or current.__context__
    detail = ' '.join(chain).lower()
    if '429' in detail or 'toomanyrequests' in detail:
        return 'O Instagram limitou temporariamente as consultas a este perfil. Aguarde antes de tentar novamente. Fazer login não garante a liberação.'
    if 'profilenotexists' in detail:
        return 'Perfil não encontrado. Confira o nome informado.'
    if 'loginrequired' in detail or '401' in detail:
        return 'O Instagram exige uma sessão de login para esta consulta. Configure sua sessão local e tente novamente.'
    if 'challenge' in detail or 'checkpoint' in detail:
        return 'O Instagram pediu uma verificação da conta. Conclua a verificação diretamente no Instagram antes de retomar.'
    if '403' in detail or 'privateprofilenotfollowed' in detail:
        return 'O Instagram recusou o acesso ao perfil com a sessão atual.'
    if any(term in detail for term in ['name resolution','getaddrinfo','connection','timeout']):
        return 'Não foi possível conectar ao Instagram. Verifique a conexão e tente novamente mais tarde.'
    if isinstance(error, FileNotFoundError):
        return 'Um arquivo local necessário não foi encontrado. Confira a configuração da sessão e do coletor.'
    return 'O coletor encontrou um erro interno. Os arquivos concluídos foram preservados; é necessário revisar o processamento.'
