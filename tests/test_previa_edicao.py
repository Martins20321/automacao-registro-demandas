from datetime import datetime

import pytest

from automacao import previa
from automacao.edicao import _valor
from automacao.registro import Demanda


def _demanda():
    return Demanda(problema="P", descricao="Fulano solicitou algo.\nOutra linha", complexidade="Normal",
                   sistema="Portal", atribuido_a="Maria Exemplo da Silva",
                   data_abertura=datetime(2026, 11, 3, 11, 49), data_conclusao=datetime(2026, 11, 3, 11, 54),
                   cliente="Portal")


def test_tsv_tem_colunas_da_lista_e_uma_linha_por_demanda(tmp_path, monkeypatch):
    monkeypatch.setattr(previa, "SAIDA", tmp_path)
    txt, tsv = previa.salvar([{"demanda": _demanda(), "analise": None, "avisos": []}])
    linhas = tsv.read_text(encoding="utf-8-sig").splitlines()
    assert len(linhas) == 1                      # só dados, sem cabeçalho
    campos = linhas[0].split("\t")
    assert len(campos) == len(previa.COLUNAS)
    assert campos[previa.COLUNAS.index("Data de Abertura")] == "03/11/2026 11:49"
    assert campos[previa.COLUNAS.index("Status")] == "Concluído"
    assert "Demanda 1 [OK]" in txt.read_text(encoding="utf-8")


def test_validacao_de_edicao():
    assert _valor("complexidade", "baixa") == "Baixa"
    assert _valor("data_abertura", "05/11/2026 09:30") == datetime(2026, 11, 5, 9, 30)
    with pytest.raises(ValueError):
        _valor("complexidade", "média")
    with pytest.raises(ValueError):
        _valor("data_abertura", "05/11/2026")
