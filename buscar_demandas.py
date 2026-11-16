"""Versão em linha de comando: busca as demandas de um estagiário desde uma data e mostra a prévia.

A versão com janelas é registro_demandas.py. Esta é útil para quem prefere o terminal ou para testes.

Exemplo:
    python buscar_demandas.py --email maria.silva@orgao.gov.br --nome "Maria Exemplo da Silva" --desde 01/11/2026
Sem argumentos, o programa pergunta os dados.
"""
import argparse
import sys
from automacao import config, destino, edicao, fluxo, ia, previa
from automacao import roster as lista
from automacao.util import ler_data


def fmt(dt):
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "—"


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

    caminho_lista = args.lista_csv
    if not caminho_lista and not args.so_previa:
        caminho_lista = input("\nCaminho do CSV exportado da lista do SharePoint "
                              "(ENTER para pular, sem checar duplicidade): ").strip().strip('"')

    print(f"\nOperador: {operador['nome']} | desde {desde:%d/%m/%Y}\n")
    resultado = fluxo.processar(operador, desde, roster, provedor, caminho_lista or "",
                                args.margem_dias, verificar_todas=not args.so_categoria)

    if resultado.existentes is not None:
        n_dup = sum(1 for i in resultado.registros if i["duplicada"])
        print(f"Verificação de duplicidade: {resultado.existentes} registros na lista, {n_dup} já existente(s).")
    else:
        print("\nATENÇÃO: sem verificação de duplicidade (nenhum CSV da lista informado).")

    # A prévia é SEMPRE gerada e salva, antes de qualquer envio.
    txt, _ = previa.salvar(resultado.registros, sufixo="_inicial")
    print("\n" + previa.texto_previa(resultado.registros))
    print(f"Prévia salva em: {txt}")

    if resultado.ignoradas:
        print(f"\n=== Ignoradas (encaminhamentos ou sem resposta útil): {len(resultado.ignoradas)} ===")
        for i in resultado.ignoradas:
            print(f"  - {i['tipo']} | conclusão {fmt(i['conclusao'])} | {i['assunto'][:70]} | {i['motivo'][:100]}")
    if resultado.falhas:
        print(f"\n=== Falhas: {len(resultado.falhas)} ===")
        for f in resultado.falhas:
            print(f"  - conclusão {fmt(f['conclusao'])}: {f['erro']}")
    print(f"\nResumo: {len(resultado.registros)} para registrar, {len(resultado.ignoradas)} ignoradas, "
          f"{len(resultado.falhas)} com falha.")

    if args.so_previa or not resultado.registros:
        return
    confirmadas = edicao.conferir(resultado.registros)
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
    sys.exit(executar())
