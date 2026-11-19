"""Entrega das demandas confirmadas.

Hoje a entrega é: (1) copiar as linhas para a área de transferência, (2) abrir a lista do SharePoint
no navegador e (3) guardar o mesmo conteúdo em um arquivo .tsv. O operador só abre a grade da lista
e cola (Ctrl+V). Não exige permissão no Azure.
A gravação direta via Microsoft Graph poderá entrar aqui, atrás da mesma função `entregar`,
sem alterar o restante do programa.
"""
import os
import webbrowser

from dotenv import load_dotenv

from .config import RAIZ
from .previa import COLUNAS, salvar


def copiar_para_area_de_transferencia(texto):
    """Coloca o texto na área de transferência do Windows. Devolve True se conseguiu."""
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, texto)
        finally:
            win32clipboard.CloseClipboard()
        return True
    except Exception:
        return False


def abrir_lista():
    """Abre a lista do SharePoint no navegador, se LISTA_URL estiver definida no .env."""
    load_dotenv(RAIZ / ".env")
    url = os.getenv("LISTA_URL", "").strip()
    if not url:
        return False
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def entregar(itens, abrir_navegador=True):
    """Grava os arquivos da versão confirmada, copia as linhas e devolve a mensagem ao operador."""
    txt, tsv = salvar(itens, sufixo="_confirmada")
    linhas = tsv.read_text(encoding="utf-8-sig").splitlines()
    copiado = copiar_para_area_de_transferencia("\r\n".join(linhas))
    aberto = abrir_lista() if abrir_navegador else False

    mensagem = [f"{len(itens)} demanda(s) confirmada(s)."]
    if copiado:
        mensagem += [
            "",
            "As linhas JÁ ESTÃO COPIADAS. Agora, na lista do SharePoint:",
            "  1. Clique em 'Editar no modo de exibição de grade'.",
            "  2. Clique na 1ª célula vazia da coluna Problema.",
            "  3. Pressione Ctrl+V.",
            "  4. Confira e clique em 'Sair do modo de grade' para salvar.",
        ]
        if aberto:
            mensagem.append("(A lista foi aberta no navegador.)")
    else:
        mensagem += ["", "Não consegui copiar automaticamente. Abra o arquivo abaixo no Bloco de Notas, "
                         "copie tudo (Ctrl+A, Ctrl+C) e cole na grade da lista."]
    mensagem += [
        "",
        f"Arquivo para colar: {tsv}",
        f"Prévia confirmada:  {txt}",
        f"Ordem das colunas (o arquivo não tem cabeçalho): {' | '.join(COLUNAS)}",
    ]
    return "\n".join(mensagem)
