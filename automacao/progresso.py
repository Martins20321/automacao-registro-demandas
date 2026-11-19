"""Mensagens de andamento. No terminal vão para a tela; na interface, para o painel de progresso."""

_destino = print


def definir(funcao=None):
    """Troca o destino das mensagens (None volta a imprimir no terminal)."""
    global _destino
    _destino = funcao or print


def emitir(mensagem):
    _destino(mensagem)
