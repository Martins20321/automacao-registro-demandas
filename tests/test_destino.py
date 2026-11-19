from datetime import datetime

from automacao import destino, previa
from automacao.registro import Demanda


def _item():
    d = Demanda(problema="P", descricao="Desc", complexidade="Baixa", sistema="Portal",
                atribuido_a="Jose", data_abertura=datetime(2026, 11, 3, 11, 49),
                data_conclusao=datetime(2026, 11, 3, 11, 54), cliente="Cliente Portal Teste")
    return {"demanda": d, "analise": None, "avisos": []}


def test_entrega_copia_linhas_e_orienta_o_operador(tmp_path, monkeypatch):
    monkeypatch.setattr(previa, "SAIDA", tmp_path)
    copiado = {}
    monkeypatch.setattr(destino, "copiar_para_area_de_transferencia",
                        lambda texto: copiado.setdefault("texto", texto) or True)
    monkeypatch.setattr(destino, "abrir_lista", lambda: True)
    msg = destino.entregar([_item(), _item()])
    assert copiado["texto"].count("\r\n") == 1          # 2 linhas, sem quebra no fim
    assert "Concluído" in copiado["texto"] and "03/11/2026 11:49" in copiado["texto"]
    assert "JÁ ESTÃO COPIADAS" in msg and "Ctrl+V" in msg and "aberta no navegador" in msg


def test_entrega_sem_area_de_transferencia_orienta_pelo_arquivo(tmp_path, monkeypatch):
    monkeypatch.setattr(previa, "SAIDA", tmp_path)
    monkeypatch.setattr(destino, "copiar_para_area_de_transferencia", lambda texto: False)
    monkeypatch.setattr(destino, "abrir_lista", lambda: False)
    msg = destino.entregar([_item()])
    assert "Não consegui copiar" in msg and "Bloco de Notas" in msg
