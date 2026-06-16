# -*- coding: utf-8 -*-
"""
Base de conhecimento (KB) estática — Belgo Triagem TI.

Artigos curados, um por categoria auto-resolvível. O agente de triagem cita o
artigo que embasou a resolução do chamado — explicabilidade ("RAG leve" por
categoria, sem dependência de API/embeddings). Os IDs seguem o padrão KB00NN,
no estilo dos catálogos de conhecimento de ITSM (ServiceNow / I Am Smart).
"""

KB_ARTIGOS = {
    "RESET_SENHA": {
        "id": "KB0001",
        "titulo": "Reset de senha de rede / Windows",
        "passos": [
            "Confirmar a identidade do colaborador (matrícula + gestor).",
            "Redefinir a senha no Active Directory (conta do usuário).",
            "Enviar a senha temporária e exigir troca no primeiro acesso.",
        ],
    },
    "VPN_RECONEXAO": {
        "id": "KB0002",
        "titulo": "VPN não conecta / cai em home office",
        "passos": [
            "Reiniciar o cliente de VPN e limpar o cache de credenciais.",
            "Renovar o endereço IP e validar a rota corporativa.",
            "Reautenticar no MFA caso o token tenha expirado.",
        ],
    },
    "IMPRESSORA_OFFLINE": {
        "id": "KB0003",
        "titulo": "Impressora aparece offline",
        "passos": [
            "Verificar o cabo de rede / conexão Wi-Fi da impressora.",
            "Reiniciar o equipamento e limpar a fila de impressão.",
            "Reinstalar a fila no spooler caso permaneça offline.",
        ],
    },
    "EMAIL_SYNC_CELULAR": {
        "id": "KB0004",
        "titulo": "E-mail corporativo não sincroniza no celular",
        "passos": [
            "Remover a conta no aplicativo do dispositivo.",
            "Reinserir as credenciais corporativas (Microsoft 365).",
            "Aguardar a sincronização inicial e validar o recebimento.",
        ],
    },
    "TEAMS_AUDIO": {
        "id": "KB0005",
        "titulo": "Teams sem áudio em reunião",
        "passos": [
            "Abrir Configurações > Dispositivos no Teams.",
            "Selecionar microfone e alto-falante corretos.",
            "Executar a chamada de teste de áudio.",
        ],
    },
    "OUTLOOK_CAIXA_CHEIA": {
        "id": "KB0006",
        "titulo": "Outlook com caixa de correio cheia",
        "passos": [
            "Arquivar e-mails antigos e esvaziar Itens Excluídos.",
            "Configurar o arquivamento automático (AutoArquivar).",
            "Confirmar a liberação de espaço e o recebimento.",
        ],
    },
    "WIFI_RECONEXAO": {
        "id": "KB0007",
        "titulo": "Wi-Fi corporativo caindo / sem internet",
        "passos": [
            "Esquecer a rede atual e reiniciar o adaptador.",
            "Reconectar à rede correta com as credenciais válidas.",
            "Renovar o IP e validar o portal de autenticação.",
        ],
    },
    "SAP_LOGIN_LENTO": {
        "id": "KB0008",
        "titulo": "Login no SAP GUI lento",
        "passos": [
            "Limpar o cache do SAP GUI.",
            "Verificar atualizações do cliente SAP Logon.",
            "Reconectar e medir o tempo de autenticação.",
        ],
    },
    "EXCEL_TRAVA": {
        "id": "KB0009",
        "titulo": "Excel travando ao abrir planilhas",
        "passos": [
            "Abrir o Excel em modo seguro e desativar suplementos.",
            "Reparar a instalação do Office.",
            "Reabrir a planilha e validar a estabilidade.",
        ],
    },
    "WINDOWS_UPDATE_AVISO": {
        "id": "KB0010",
        "titulo": "Aviso de Windows Update pendente",
        "passos": [
            "Acessar o Windows Update e instalar as atualizações.",
            "Agendar o reinício fora do expediente.",
            "Confirmar que o aviso não reaparece.",
        ],
    },
}


def sugerir_artigo(categoria: str | None) -> dict | None:
    """Retorna o artigo de KB associado à categoria, ou None (ex.: OUTRO)."""
    if not categoria:
        return None
    return KB_ARTIGOS.get(categoria)
