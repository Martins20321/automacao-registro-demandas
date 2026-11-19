"""Seleção das demandas de um estagiário desde uma data (opção A).

Fase 1: conversas "Feito" que têm a categoria do estagiário.
Fase 2 (opcional): demais conversas "Feito" da janela, decididas só pela assinatura.
O dono de verdade da demanda é sempre quem assina a resposta de conclusão.
"""
from datetime import timedelta

from . import assinatura, outlook
from .config import CATEGORIA_FEITO, DOMINIO_INTERNO
from .progresso import emitir
from .roster import categoria_do_operador


def buscar(ns, operador, desde, roster, margem_dias=90, verificar_todas=True):
    entrada, enviados = outlook.abrir_pastas(ns)
    emitir("Lendo o Outlook (pode levar alguns minutos)...")
    idx_in = outlook.indexar(entrada, "entrada", desde - timedelta(days=margem_dias))
    idx_out = outlook.indexar(enviados, "enviados", desde)
    cache = assinatura.carregar_cache()

    candidatas = []
    for conv, enviadas in idx_out.items():
        recebidas = idx_in.get(conv, [])
        todas = recebidas + enviadas
        if not any(CATEGORIA_FEITO in r["cats"] for r in todas):
            continue
        cats = sorted({c for r in todas for c in r["cats"]})
        candidatas.append((conv, recebidas, enviadas, cats, categoria_do_operador(operador, cats)))

    fase1 = [c for c in candidatas if c[4]]
    fase2 = [c for c in candidatas if not c[4]] if verificar_todas else []
    emitir(f"Conversas 'Feito' com resposta desde {desde:%d/%m/%Y}: {len(candidatas)} "
          f"({len(fase1)} com a categoria do estagiário, {len(fase2)} a verificar pela assinatura)")

    demandas, descartadas = [], 0
    for fase, lista in ((1, fase1), (2, fase2)):
        for conv, recebidas, enviadas, cats, _ in lista:
            reg_conclusao = max(enviadas, key=lambda r: r["data"])
            conclusao = outlook.abrir_mensagem(ns, enviados, reg_conclusao)
            resp = assinatura.identificar_responsavel(conclusao, roster, cache)
            do_operador = resp["registro"] is not None and resp["registro"]["nome"] == operador["nome"]
            if resp["ok"] and not do_operador:
                descartadas += 1          # assinatura clara de outro estagiário
                continue
            if not resp["ok"] and fase == 2:
                # fase 2 não tem a categoria como indício: só entra se a assinatura confirmar
                descartadas += 1
                continue
            motivos = [] if resp["ok"] else [resp["motivo"]]
            if not recebidas:
                motivos.append("primeiro e-mail fora da janela lida")
                abertura, cliente = None, "?"
            else:
                reg_primeiro = min(recebidas, key=lambda r: r["data"])
                primeiro = outlook.abrir_mensagem(ns, entrada, reg_primeiro)
                abertura = reg_primeiro["data"]
                cliente = ("interno" if outlook.smtp_remetente(primeiro).endswith(DOMINIO_INTERNO)
                           else "externo")
            demandas.append({
                "fase": fase, "abertura": abertura, "conclusao": reg_conclusao["data"],
                "cliente": cliente, "categorias": cats,
                "recebidas": len(recebidas), "enviadas": len(enviadas),
                "recebidas_regs": recebidas, "enviadas_regs": enviadas,
                "responsavel": resp["registro"]["nome"] if resp["registro"] else "?",
                "nota": f"{resp['nota_nome']:.0f}/{resp['nota_email']:.0f}",
                "status": "OK" if not motivos else "REVISAR", "motivos": motivos,
            })
    assinatura.salvar_cache(cache)
    demandas.sort(key=lambda d: d["conclusao"])
    return demandas, descartadas, entrada, enviados
