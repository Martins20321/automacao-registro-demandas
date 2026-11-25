"""Acesso ao Outlook clássico (COM), somente leitura.

O Exchange limita quantos itens ficam abertos ao mesmo tempo. Por isso o índice guarda
apenas metadados (EntryID, data, categorias) e cada mensagem é aberta sob demanda.
"""
from .config import CAIXA_EMAIL, LOJA, PASTA_ENTRADA, PASTA_ENVIADOS
from .progresso import emitir
from .util import local

NOMES_ENVIADOS = {"itens enviados", "sent items", "enviados", "sent"}


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


def nomes_das_caixas(ns):
    """Nomes de todas as caixas/armazenamentos visíveis no perfil do Outlook (para diagnóstico)."""
    return [loja.DisplayName for loja in ns.Stores]


def localizar_loja(ns, nome):
    """Acha o armazenamento pelo nome: primeiro exato, depois ignorando maiúsculas/espaços nas pontas."""
    lojas = list(ns.Stores)
    for loja in lojas:
        if loja.DisplayName == nome:
            return loja
    alvo = nome.strip().lower()
    for loja in lojas:
        if loja.DisplayName.strip().lower() == alvo:
            return loja
    return None


def _pasta_enviados_irma(pasta_entrada):
    """A partir da Caixa de Entrada, acha os Itens Enviados na mesma caixa (nome em PT ou EN)."""
    raiz = pasta_entrada.Parent
    for pasta in raiz.Folders:
        if pasta.Name.strip().lower() in NOMES_ENVIADOS:
            return pasta
    return None


def _por_caixa_compartilhada(ns):
    """Caixa aberta por PERMISSÃO (sem aparecer como conta própria no Outlook): usa o e-mail dela."""
    if not CAIXA_EMAIL:
        return None
    try:
        destinatario = ns.CreateRecipient(CAIXA_EMAIL)
        destinatario.Resolve()
        if not destinatario.Resolved:
            return None
        entrada = ns.GetSharedDefaultFolder(destinatario, PASTA_ENTRADA)
        enviados = _pasta_enviados_irma(entrada)
        return (entrada, enviados) if enviados is not None else None
    except Exception:
        return None


def abrir_pastas(ns):
    loja = localizar_loja(ns, LOJA)
    if loja is not None:
        return loja.GetDefaultFolder(PASTA_ENTRADA), loja.GetDefaultFolder(PASTA_ENVIADOS)
    alternativa = _por_caixa_compartilhada(ns)
    if alternativa is not None:
        return alternativa
    encontradas = nomes_das_caixas(ns)
    raise RuntimeError(
        f"Armazenamento '{LOJA}' não encontrado no perfil do Outlook. "
        f"Caixas encontradas: {', '.join(encontradas) if encontradas else '(nenhuma)'}. "
        "Confira o nome exato em Configurações (copie como aparece no painel esquerdo do Outlook). "
        "Se a caixa estiver aberta só por permissão (sem aparecer como conta própria), preencha também "
        "o e-mail dela em Configurações.")


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
