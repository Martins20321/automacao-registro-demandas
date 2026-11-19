"""Prévia exata do que será enviado à lista do SharePoint, e arquivos de saída."""
from datetime import datetime

from .config import SAIDA

# Ordem de saída definida pela equipe (a vista da lista deve ter as colunas nesta ordem)
COLUNAS = ["Problema", "Descrição do problema", "Complexidade", "Status", "Atribuído a",
           "Data de Abertura", "Cliente", "Sistema", "Origem do chamado", "Data de Conclusão"]


def fmt(dt):
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "—"


def linha(d):
    return [d.problema, d.descricao, d.complexidade, d.status, d.atribuido_a,
            fmt(d.data_abertura), d.cliente, d.sistema, d.origem, fmt(d.data_conclusao)]


def texto_previa(itens):
    """itens: lista de {'demanda', 'analise', 'avisos'}. Texto que o operador confere."""
    if not itens:
        return "Nenhuma demanda para registrar."
    partes = [f"PRÉVIA: {len(itens)} demanda(s) que serão registradas na lista do SharePoint\n"]
    for n, item in enumerate(itens, 1):
        d, a, avisos = item["demanda"], item["analise"], item["avisos"]
        partes.append(f"--- Demanda {n} [{'REVISAR' if avisos else 'OK'}] ---")
        partes.append(f"  Problema:       {d.problema}")
        partes.append(f"  Descrição:      {d.descricao}")
        partes.append(f"  Complexidade:   {d.complexidade}   Status: {d.status}   Origem: {d.origem}")
        partes.append(f"  Sistema:        {d.sistema}")
        partes.append(f"  Atribuído a:    {d.atribuido_a}")
        partes.append(f"  Abertura:       {fmt(d.data_abertura)}   Conclusão: {fmt(d.data_conclusao)}")
        partes.append(f"  Cliente:        {d.cliente}")
        if a is not None:
            partes.append(f"  IA: tipo {a.tipo}, confiança {a.confianca} | {a.motivo}")
        partes.extend(f"  ! {aviso}" for aviso in avisos)
        partes.append("")
    return "\n".join(partes)


def salvar(itens, sufixo=""):
    """Grava a prévia legível (.txt) e a tabela para colar na lista (.tsv). Devolve os caminhos."""
    SAIDA.mkdir(exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S") + sufixo
    txt, tsv = SAIDA / f"previa_{carimbo}.txt", SAIDA / f"para_colar_{carimbo}.tsv"
    txt.write_text(texto_previa(itens), encoding="utf-8")
    limpa = lambda v: " ".join(str(v).split())
    # Sem linha de cabeçalho: a grade do SharePoint recebe só os dados. A ordem está em COLUNAS.
    linhas = ["\t".join(limpa(c) for c in linha(i["demanda"])) for i in itens]
    tsv.write_text("\n".join(linhas) + "\n", encoding="utf-8-sig")
    return txt, tsv
