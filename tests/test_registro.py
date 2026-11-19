from datetime import datetime

from automacao.modelos import AnaliseIA, MensagemConversa
from automacao.registro import construir_demanda


def _mensagens(interno):
    return [
        MensagemConversa(indice=0, direcao="recebida", data=datetime(2026, 11, 3, 11, 49),
                         texto="x", assunto="RE: Atualização da página", remetente_nome="Fabio Skaf",
                         remetente_interno=interno),
        MensagemConversa(indice=1, direcao="enviada", data=datetime(2026, 11, 3, 11, 54), texto="y"),
    ]


def _analise():
    return AnaliseIA(tipo="demanda", sistema="Portal", complexidade="Baixa", indice_solicitacao=0,
                     indice_conclusao=1, solicitacao="Atualização da página do Quem é Quem.",
                     providencia="A demanda foi devidamente atendida", confianca="alta", motivo="m")


def test_cliente_interno_usa_nome():
    d = construir_demanda(_analise(), _mensagens(True), "Maria Exemplo da Silva")
    assert d.cliente == "Fabio Skaf"
    assert d.descricao == "Fabio Skaf solicitou atualização da página do Quem é Quem. A demanda foi devidamente atendida."
    assert d.problema == "Atualização da página"
    assert d.status == "Concluído" and d.origem == "E-mail"


def test_corrige_sujeito_repetido_e_capitaliza_providencia():
    a = _analise().model_copy(update={
        "solicitacao": "o usuário solicitou a inclusão do nome [PESSOA_1].",
        "providencia": "ativou a conta do usuário"})
    from automacao.anonimizar import Mascara
    m = Mascara()
    m.token("Gustavo Assis")
    d = construir_demanda(a, _mensagens(True), "Maria Exemplo da Silva", m)
    assert d.descricao == "Fabio Skaf solicitou a inclusão do nome Gustavo Assis. Ativou a conta do usuário."


def test_cliente_externo_vira_portal_e_usuario_externo():
    d = construir_demanda(_analise(), _mensagens(False), "Maria Exemplo da Silva")
    assert d.cliente == "Cliente Portal Teste"
    assert d.descricao.startswith("Usuário externo solicitou ")
