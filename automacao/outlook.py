"""Acesso ao Outlook clássico (COM), somente leitura.

O Exchange limita quantos itens ficam abertos ao mesmo tempo. Por isso o índice guarda
apenas metadados (EntryID, data, categorias) e cada mensagem é aberta sob demanda.
"""
from .config import LOJA, PASTA_ENTRADA, PASTA_ENVIADOS
from .progresso import emitir
from .util import local


def categorias(item):
    texto = item.Categories or ""
    return [c.strip() for c in texto.replace(",", ";").split(";") if c.strip()]


def smtp_remetente(msg):
    try:
        if msg.SenderEmailType == "EX":
            usuario = msg.Sender.GetExchangeUser()
            if usuario:
                return (usuario.PrimarySmtpAddress or "").lower()
        return (msg.SenderEmailAddress or "").lower()
    except Exception:
        return ""


def abrir_pastas(ns):
    for loja in ns.Stores:
        if loja.DisplayName == LOJA:
            return loja.GetDefaultFolder(PASTA_ENTRADA), loja.GetDefaultFolder(PASTA_ENVIADOS)
    raise RuntimeError(f"Armazenamento '{LOJA}' não encontrado no perfil do Outlook")


def indexar(pasta, rotulo, corte):
    """Mapeia ConversationID -> metadados das mensagens com data >= corte."""
    itens = pasta.Items
    campo = "ReceivedTime" if rotulo == "entrada" else "SentOn"
    itens.Sort(f"[{campo}]", True)
    indice, lidos, erros = {}, 0, 0
    for item in itens:
        try:
            if item.Class != 43:
                continue
            data = local(getattr(item, campo))
            if data < corte:
                break
            lidos += 1
            registro = {"id": item.EntryID, "data": data, "cats": categorias(item)}
            indice.setdefault(item.ConversationID, []).append(registro)
        except Exception:
            erros += 1
    emitir(f"  {rotulo}: {lidos} mensagens desde {corte:%d/%m/%Y}, "
          f"{len(indice)} conversas, {erros} erros")
    return indice


def abrir_mensagem(ns, pasta, registro):
    return ns.GetItemFromID(registro["id"], pasta.StoreID)
