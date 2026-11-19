from datetime import datetime

from automacao import duplicidade
from automacao.anonimizar import Mascara
from automacao.modelos import AnaliseIA, MensagemConversa
from automacao.registro import CLIENTE_CP, construir_demanda


def _msgs(interno):
    return [
        MensagemConversa(indice=0, direcao="recebida", data=datetime(2026, 11, 3, 11, 49), texto="x",
                         assunto="Acesso", remetente_nome="Alguém", remetente_interno=interno),
        MensagemConversa(indice=1, direcao="enviada", data=datetime(2026, 11, 3, 11, 54), texto="y"),
    ]


def _analise(sistema, token=""):
    return AnaliseIA(tipo="demanda", sistema=sistema, complexidade="Baixa", indice_solicitacao=0,
                     indice_conclusao=1, solicitacao="o cadastro como gestor", providencia="A equipe alterou o perfil.",
                     solicitante_token=token, confianca="alta", motivo="m")


def test_cp_externo_usa_cliente_cp_e_nome_do_corpo():
    m = Mascara()
    token = m.token("Maria das Dores")
    d = construir_demanda(_analise("Consultas Públicas", token), _msgs(False), "Jose", m)
    assert d.cliente == CLIENTE_CP
    assert d.descricao.startswith("Maria das Dores solicitou o cadastro como gestor.")


def test_cp_externo_sem_nome_no_corpo_usa_nome_do_remetente():
    msgs = _msgs(False)
    msgs[0].remetente_nome = "Ana Paula Souza"
    d = construir_demanda(_analise("Consultas Públicas"), msgs, "Jose", Mascara())
    assert d.cliente == CLIENTE_CP and d.descricao.startswith("Ana Paula Souza solicitou")


def test_cp_externo_sem_nome_nenhum_cai_em_usuario_externo():
    msgs = _msgs(False)
    msgs[0].remetente_nome = "Contribuições Consultas Públicas"   # nome de caixa, não de pessoa
    d = construir_demanda(_analise("Consultas Públicas"), msgs, "Jose", Mascara())
    assert d.descricao.startswith("Usuário externo solicitou")


def test_cp_interno_usa_nome_do_servidor():
    d = construir_demanda(_analise("Consultas Públicas"), _msgs(True), "Jose", Mascara())
    assert d.cliente == "Alguém"


def test_portal_externo_usa_cliente_do_portal():
    d = construir_demanda(_analise("Portal"), _msgs(False), "Jose", Mascara())
    assert d.cliente == "Cliente Portal Teste"


def test_duplicidade_por_chave(tmp_path):
    csv_lista = tmp_path / "lista.csv"
    csv_lista.write_text(
        '"Problema","Descrição do problema","Data de Abertura","Cliente"\n'
        '"Acesso ","texto","03/11/2026 11:49","Cliente Portal Teste"\n', encoding="utf-8")
    existentes = duplicidade.carregar_lista(csv_lista)
    d = construir_demanda(_analise("Portal"), _msgs(False), "Jose", Mascara())
    itens = [{"demanda": d, "analise": None, "avisos": []}]
    assert duplicidade.marcar_duplicadas(itens, existentes) == 1
    assert itens[0]["duplicada"] and "JÁ EXISTE" in itens[0]["avisos"][0]
