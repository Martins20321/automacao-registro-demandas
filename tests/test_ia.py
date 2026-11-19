import json
from datetime import datetime

import pytest

from automacao import ia
from automacao.modelos import MensagemConversa


class Falso:
    def __init__(self, **campos):
        base = {"tipo": "demanda", "sistema": "Portal", "complexidade": "Normal", "indice_solicitacao": 0,
                "indice_conclusao": 1, "solicitacao": "x", "providencia": "y", "solicitante_token": "",
                "confianca": "alta", "motivo": "m"}
        base.update(campos)
        self.resposta = json.dumps(base)

    def completar_json(self, instrucoes, conteudo):
        return self.resposta


def _msgs(enviadas=1):
    base = [MensagemConversa(indice=0, direcao="recebida", data=datetime(2026, 11, 1, 9), texto="a")]
    for i in range(enviadas):
        base.append(MensagemConversa(indice=i + 1, direcao="enviada", data=datetime(2026, 11, 1, 10 + i), texto="b"))
    return base


def test_resposta_valida_passa():
    assert ia.analisar(_msgs(), Falso()).tipo == "demanda"


def test_indices_ruins_em_conversa_simples_usam_regra_fixa():
    a = ia.analisar(_msgs(), Falso(indice_conclusao=0))
    assert (a.indice_solicitacao, a.indice_conclusao, a.confianca) == (0, 1, "baixa")


def test_indices_ruins_em_conversa_com_varias_respostas_falham():
    with pytest.raises(ValueError):
        ia.analisar(_msgs(enviadas=2), Falso(indice_conclusao=0))


def test_encaminhamento_ignora_indices():
    a = ia.analisar(_msgs(), Falso(tipo="encaminhamento", indice_conclusao=0))
    assert a.tipo == "encaminhamento"


def test_conclusao_e_sempre_a_ultima_resposta_enviada():
    # a IA apontou a 1ª resposta (índice 1), mas existe uma 2ª resposta enviada (índice 2)
    a = ia.analisar(_msgs(enviadas=2), Falso(indice_conclusao=1))
    assert a.indice_conclusao == 2


def test_sem_resposta_util_nao_e_registrado():
    a = ia.analisar(_msgs(), Falso(tipo="sem_resposta_util", indice_conclusao=0))
    assert a.tipo in ia.NAO_REGISTRADOS


def test_esclarecimento_tambem_valida_indices():
    a = ia.analisar(_msgs(), Falso(tipo="esclarecimento", indice_conclusao=0))
    assert (a.tipo, a.indice_conclusao, a.confianca) == ("esclarecimento", 1, "baixa")
