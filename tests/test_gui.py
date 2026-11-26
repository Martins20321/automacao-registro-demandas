"""Testes da interface (precisam de um ambiente gráfico; são pulados se não houver)."""
import datetime
import tkinter as tk

import pytest

from automacao import gui


def test_texto_resultado_vazio_explica_a_data_e_o_que_foi_lido():
    linhas = ["Lendo o Outlook (pode levar alguns minutos)...",
              "  entrada: 471 mensagens desde 27/08/2026, 290 conversas, 0 erros",
              "  enviados: 0 mensagens desde 25/11/2026, 0 conversas, 0 erros",
              "Conversas 'Feito' com resposta desde 25/11/2026: 0 (0 com a categoria, 0 a verificar)"]
    texto = gui.App.texto_resultado_vazio("25/11/2026", linhas)
    assert "desde 25/11/2026" in texto
    assert "entrada: 471 mensagens" in texto and "enviados: 0 mensagens" in texto
    assert "data inicial anterior" in texto
    assert "veio vazia" not in texto


def test_texto_resultado_vazio_avisa_quando_a_caixa_de_entrada_veio_vazia():
    texto = gui.App.texto_resultado_vazio("01/11/2026", ["  entrada: 0 mensagens desde 01/08/2026, 0 conversas, 0 erros"])
    assert "Caixa de Entrada veio vazia" in texto


@pytest.fixture(scope="module")
def _janela():
    """Uma única janela para o módulo todo: criar/destruir várias raízes Tk no mesmo processo é instável."""
    try:
        janela = gui.App()
    except tk.TclError as erro:
        pytest.skip(f"sem ambiente gráfico: {erro}")
    janela.withdraw()
    janela.data_padrao_inicial = janela.var_desde.get()
    yield janela
    janela.destroy()


@pytest.fixture
def app(_janela):
    for w in list(_janela.winfo_children()):          # fecha diálogos deixados por testes anteriores
        if isinstance(w, tk.Toplevel):
            w.destroy()
    return _janela


def _dialogo_do_calendario(app):
    dialogos = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]
    assert dialogos, "o calendário não abriu"
    cal = next(w for w in dialogos[0].winfo_children() if isinstance(w, gui.Calendar))
    return dialogos[0], cal


def test_data_padrao_e_hoje(app):
    assert app.data_padrao_inicial == datetime.datetime.now().strftime("%d/%m/%Y")


def test_calendario_continua_aberto_ao_trocar_de_mes(app):
    app.var_desde.set("15/10/2026")
    app._escolher_data()
    app.update()
    janela, cal = _dialogo_do_calendario(app)
    assert cal.get_displayed_month() == (10, 2026)
    cal._l_month.invoke()                     # seta de mês anterior
    app.update()
    assert janela.winfo_exists() and cal.get_displayed_month() == (9, 2026)
    cal._r_month.invoke()                     # seta de próximo mês
    cal._r_month.invoke()
    app.update()
    assert janela.winfo_exists() and cal.get_displayed_month() == (11, 2026)


def test_clicar_num_dia_preenche_o_campo_e_fecha(app):
    app.var_desde.set("15/10/2026")
    app._escolher_data()
    app.update()
    janela, cal = _dialogo_do_calendario(app)
    cal.selection_set(datetime.date(2026, 10, 7))
    cal.event_generate("<<CalendarSelected>>")
    app.update()
    assert app.var_desde.get() == "07/10/2026"
    assert not janela.winfo_exists()
