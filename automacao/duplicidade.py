"""Verificação de duplicidade contra uma exportação CSV da lista do SharePoint.

Chave: Problema + Data de abertura (com horário) + Cliente. A Descrição fica de fora de propósito:
ela é resumida pela IA e muda a cada execução.
"""
import csv

from .previa import fmt
from .util import norm

COLUNAS_NECESSARIAS = {"Problema", "Data de Abertura", "Cliente"}


def chave(problema, abertura, cliente):
    return (norm(problema), " ".join(abertura.split()), norm(cliente))


def carregar_lista(caminho):
    """Lê o CSV exportado da lista e devolve o conjunto de chaves já registradas."""
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            with open(caminho, encoding=codificacao, newline="") as f:
                leitor = csv.DictReader(f)
                faltam = COLUNAS_NECESSARIAS - set(leitor.fieldnames or [])
                if faltam:
                    raise ValueError(f"O CSV não tem as colunas: {', '.join(sorted(faltam))}")
                return {chave(l["Problema"], l["Data de Abertura"], l["Cliente"]) for l in leitor}
        except UnicodeDecodeError:
            continue
    raise ValueError("Não consegui ler o CSV (codificação desconhecida).")


def chave_demanda(d):
    return chave(d.problema, fmt(d.data_abertura), d.cliente)


def marcar_duplicadas(itens, existentes):
    """Marca cada item com 'duplicada' e acrescenta um aviso. Devolve quantas são duplicadas."""
    total = 0
    for item in itens:
        item["duplicada"] = chave_demanda(item["demanda"]) in existentes
        if item["duplicada"]:
            total += 1
            item["avisos"].append("JÁ EXISTE na lista (mesmo Problema, abertura e Cliente)")
    return total
