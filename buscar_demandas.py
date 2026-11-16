"""Busca as demandas concluídas de um estagiário desde uma data e mostra a prévia do registro.

SOMENTE LEITURA: não grava nada no SharePoint.

Exemplo:
    python buscar_demandas.py --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026
Sem argumentos, o programa pergunta os dados.
"""
import argparse
import sys
import time
from datetime import datetime

import win32com.client

from automacao import config, destino, duplicidade, edicao, ia, previa
from automacao import roster as lista
from automacao.busca import buscar
from automacao.conversa import montar_conversa
from automacao.registro import construir_demanda


def ler_data(texto):
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), formato)
        except ValueError:
            pass
    raise ValueError(f"Data inválida: '{texto}'. Use dd/mm/aaaa.")


def fmt(dt):
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "—"


def analisar_demanda(ns, entrada, enviados, d, roster, provedor):
    """Devolve (demanda_registro | None, analise, mensagens, avisos)."""
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
    if analise.tipo == "demanda" and analise.sistema == "Consultas Públicas" and not any(p in texto_acao for p in ("ativ", "cadastr", "perfil", "gestor", "reuni", "login")):
        avisos.append("Consultas Públicas fora de ativação de conta/perfil: confirmar se não é encaminhamento")
    if analise.sistema == "Outro":
        avisos.append("sistema fora de Portal/Consultas Públicas: definir manualmente")
    if registro.data_conclusao < registro.data_abertura:
        avisos.append("conclusão anterior à abertura")
    return registro, analise, mensagens, avisos


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--email")
    ap.add_argument("--nome")
    ap.add_argument("--desde", help="data inicial (dd/mm/aaaa)")
    ap.add_argument("--margem-dias", type=int, default=90,
                    help="quanto antes da data inicial procurar o primeiro e-mail da conversa")
    ap.add_argument("--so-categoria", action="store_true",
                    help="não verificar pela assinatura as conversas sem a categoria do estagiário")
    ap.add_argument("--lista-csv", help="CSV exportado da lista do SharePoint (para checar duplicidade)")
    ap.add_argument("--so-previa", action="store_true",
                    help="gera e salva a prévia, mas não pergunta nem entrega (para testes)")
    args = ap.parse_args()

    faltando = config.configuracao_faltando()
    if faltando:
        raise ValueError("Faltam valores no arquivo .env (veja .env.example): " + ", ".join(faltando))

    email = args.email or input("Seu e-mail institucional: ")
    nome = args.nome or input("Seu nome completo: ")
    desde = ler_data(args.desde or input("Buscar demandas concluídas desde (dd/mm/aaaa): "))

    roster = lista.carregar()
    operador = lista.identificar_operador(nome, email, roster)
    provedor = ia.ProvedorGroq()  # falha cedo se a chave não estiver no .env
    print(f"\nOperador: {operador['nome']} | desde {desde:%d/%m/%Y}\n")

    ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    demandas, descartadas, entrada, enviados = buscar(
        ns, operador, desde, roster, args.margem_dias, verificar_todas=not args.so_categoria)
    print(f"\n{len(demandas)} conversa(s) de {operador['nome']} "
          f"({descartadas} descartada(s) por assinatura de outra pessoa). Analisando com IA...")

    registros, ignoradas, falhas = [], [], []
    for d in demandas:
        try:
            registro, analise, mensagens, avisos = analisar_demanda(
                ns, entrada, enviados, d, roster, provedor)
        except Exception as erro:
            falhas.append((d, str(erro)[:150]))
            continue
        finally:
            time.sleep(1.5)  # respeita o limite de requisições do plano gratuito
        if registro is None:
            ignoradas.append((d, analise, mensagens))
        else:
            registros.append({"demanda": registro, "analise": analise, "avisos": avisos})

    registros.sort(key=lambda i: i["demanda"].data_conclusao)

    # Duplicidade: compara com a lista exportada (CSV). Sem o CSV, avisa que não houve verificação.
    caminho_lista = args.lista_csv
    if not caminho_lista and not args.so_previa:
        caminho_lista = input("\nCaminho do CSV exportado da lista do SharePoint "
                              "(ENTER para pular, sem checar duplicidade): ").strip().strip('"')
    if caminho_lista:
        existentes = duplicidade.carregar_lista(caminho_lista)
        n_dup = duplicidade.marcar_duplicadas(registros, existentes)
        print(f"Verificação de duplicidade: {len(existentes)} registros na lista, {n_dup} já existente(s).")
    else:
        print("\nATENÇÃO: sem verificação de duplicidade (nenhum CSV da lista informado).")

    # A prévia é SEMPRE gerada e salva, antes de qualquer envio.
    txt, tsv = previa.salvar(registros, sufixo="_inicial")
    print("\n" + previa.texto_previa(registros))
    print(f"Prévia salva em: {txt}")

    if ignoradas:
        print(f"\n=== Ignoradas (encaminhamentos ou sem resposta útil): {len(ignoradas)} ===")
        for d, analise, mensagens in ignoradas:
            assunto = next((m.assunto for m in mensagens if m.direcao == "recebida"), "")
            print(f"  - {analise.tipo} | conclusão {fmt(d['conclusao'])} | {assunto[:70]} | {analise.motivo[:100]}")
    if falhas:
        print(f"\n=== Falhas: {len(falhas)} ===")
        for d, erro in falhas:
            print(f"  - conclusão {fmt(d['conclusao'])}: {erro}")
    print(f"\nResumo: {len(registros)} para registrar, {len(ignoradas)} ignoradas, {len(falhas)} com falha.")

    if args.so_previa or not registros:
        return
    confirmadas = edicao.conferir(registros)
    if confirmadas:
        print("\n" + destino.entregar(confirmadas))
    else:
        print("\nNada foi enviado.")


def executar():
    try:
        main()
        return 0
    except (ValueError, RuntimeError) as erro:
        print(f"\nErro: {erro}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrompido pelo operador. Nada foi enviado.")
        return 130
    except Exception as erro:
        print(f"\nFALHOU: {erro!r}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    codigo = executar()
    if getattr(sys, "frozen", False):          # no .exe, mantém a janela aberta para ler o resultado
        try:
            input("\nPressione ENTER para fechar...")
        except EOFError:
            pass
    sys.exit(codigo)
