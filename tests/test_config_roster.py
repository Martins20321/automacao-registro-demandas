import pytest

from automacao import config


def test_importar_roster_copia_e_valida(tmp_path, monkeypatch):
    destino = tmp_path / "estagiarios.csv"
    monkeypatch.setattr(config, "ROSTER", destino)
    origem = tmp_path / "entrada.csv"
    origem.write_text("nome,email\nFulano de Tal,fulano@orgao.gov.br\n", encoding="utf-8")
    resultado = config.importar_roster(origem)
    assert resultado == destino
    assert "Fulano de Tal" in destino.read_text(encoding="utf-8")


def test_importar_roster_rejeita_csv_sem_colunas_certas(tmp_path):
    origem = tmp_path / "entrada.csv"
    origem.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        config.importar_roster(origem)
