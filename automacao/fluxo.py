"""Fluxo completo (Outlook -> IA -> registros), independente de terminal ou janela.

A linha de comando (buscar_demandas.py) e a interface gráfica (gui.py) usam esta mesma função.
"""
import time
from dataclasses import dataclass, field

import pythoncom
import win32com.client

from . import duplicidade, ia, progresso
from .busca import buscar
from .conversa import montar_conversa
from .registro import construir_demanda

PAUSA_ENTRE_CHAMADAS = 1.5   # respeita o limite de requisições do plano gratuito


@dataclass
class Resultado:
    registros: list = field(default_factory=list)   # {'demanda', 'analise', 'avisos', 'duplicada'}
    ignoradas: list = field(default_factory=list)   # {'tipo', 'conclusao', 'assunto', 'motivo'}
    falhas: list = field(default_factory=list)      # {'conclusao', 'erro'}
    descartadas: int = 0                            # conversas assinadas por outra pessoa
    existentes: int | None = None                   # registros no CSV da lista (None = sem checagem)


def analisar_demanda(ns, entrada, enviados, d, roster, provedor):
    """Devolve (registro | None, analise, mensagens, avisos)."""
    mensagens, mascara = montar_conversa(
        ns, entrada, enviados, d["recebidas_regs"], d["enviadas_regs"], roster)
    analise = ia.analisar(mensagens, provedor)
    if analise.tipo in ia.NAO_REGISTRADOS:   # esclarecimento também é registrado
        return None, analise, mensagens, []
    registro = construir_demanda(analise, mensagens, d["responsavel"], mascara)
    avisos = list(d["motivos"])
    if analise.confianca == "baixa":
        avisos.append("IA com confiança baixa")
    if analise.sistema == "Consultas Públicas" and registro.descricao.startswith("Usuário externo"):
        avisos.append("nome do usuário não encontrado no e-mail: preencher na descrição")
    texto_acao = f"{analise.solicitacao} {analise.providencia}".lower()
    if analise.tipo == "demanda" and analise.sistema == "Consultas Públicas" and not any(
            p in texto_acao for p in ("ativ", "cadastr", "perfil", "gestor", "reuni", "login")):
        avisos.append("Consultas Públicas fora de ativação de conta/perfil: confirmar se não é encaminhamento")
    if analise.sistema == "Outro":
        avisos.append("sistema fora de Portal/Consultas Públicas: definir manualmente")
    if registro.data_conclusao < registro.data_abertura:
        avisos.append("conclusão anterior à abertura")
    return registro, analise, mensagens, avisos


def processar(operador, desde, roster, provedor, lista_csv="", margem_dias=90, verificar_todas=True):
    """Busca as demandas do operador desde `desde` e as analisa. Não grava nada em lugar nenhum."""
    pythoncom.CoInitialize()      # necessário quando roda fora da thread principal (interface)
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        demandas, descartadas, entrada, enviados = buscar(
            ns, operador, desde, roster, margem_dias, verificar_todas)
        resultado = Resultado(descartadas=descartadas)
        total = len(demandas)
        progresso.emitir(f"{total} conversa(s) de {operador['nome']} "
                         f"({descartadas} descartada(s) por assinatura de outra pessoa). Analisando com IA...")

        for n, d in enumerate(demandas, 1):
            progresso.emitir(f"Analisando com IA: {n} de {total}")
            try:
                registro, analise, mensagens, avisos = analisar_demanda(
                    ns, entrada, enviados, d, roster, provedor)
            except Exception as erro:
                resultado.falhas.append({"conclusao": d["conclusao"], "erro": str(erro)[:150]})
                continue
            finally:
                time.sleep(PAUSA_ENTRE_CHAMADAS)
            if registro is None:
                assunto = next((m.assunto for m in mensagens if m.direcao == "recebida"), "")
                resultado.ignoradas.append({"tipo": analise.tipo, "conclusao": d["conclusao"],
                                            "assunto": assunto, "motivo": analise.motivo})
            else:
                resultado.registros.append({"demanda": registro, "analise": analise,
                                            "avisos": avisos, "duplicada": False})

        resultado.registros.sort(key=lambda i: i["demanda"].data_conclusao)
        if lista_csv:
            existentes = duplicidade.carregar_lista(lista_csv)
            duplicidade.marcar_duplicadas(resultado.registros, existentes)
            resultado.existentes = len(existentes)
        return resultado
    finally:
        pythoncom.CoUninitialize()
