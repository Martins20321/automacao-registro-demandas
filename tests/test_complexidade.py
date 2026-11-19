import pytest

from automacao.registro import complexidade_por_regra


def test_esclarecimento_e_sempre_baixa():
    from datetime import datetime
    from automacao.modelos import AnaliseIA, MensagemConversa
    from automacao.registro import construir_demanda
    msgs = [MensagemConversa(indice=0, direcao="recebida", data=datetime(2026, 11, 1, 9), texto="x",
                             remetente_nome="Ana Souza", remetente_interno=True),
            MensagemConversa(indice=1, direcao="enviada", data=datetime(2026, 11, 1, 10), texto="y")]
    a = AnaliseIA(tipo="esclarecimento", sistema="Portal", tarefa="outra", indice_solicitacao=0,
                  indice_conclusao=1, solicitacao="esclarecimento sobre como alterar a página",
                  providencia="A equipe orientou o procedimento.", confianca="alta", motivo="m")
    assert construir_demanda(a, msgs, "Jose").complexidade == "Baixa"


@pytest.mark.parametrize("tarefa,esperado", [
    ("ativacao_conta_cp", "Baixa"),
    ("alteracao_perfil_cp", "Baixa"),
    ("troca_quem_e_quem", "Baixa"),
    ("outra", "Normal"),
    ("qualquer coisa", "Normal"),
])
def test_complexidade_por_regra(tarefa, esperado):
    assert complexidade_por_regra(tarefa) == esperado
