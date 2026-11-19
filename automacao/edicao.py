"""Conferência pelo operador: mostrar a prévia, aceitar alterações e pedir confirmação."""
from datetime import datetime

from .previa import texto_previa

COMPLEXIDADES = {"baixa": "Baixa", "normal": "Normal", "alta": "Alta", "crítico": "Crítico", "critico": "Crítico"}
CAMPOS = [  # (rótulo, atributo); Status e Origem são fixos e não aparecem aqui
    ("Problema", "problema"), ("Descrição", "descricao"), ("Complexidade", "complexidade"),
    ("Sistema", "sistema"), ("Atribuído a", "atribuido_a"), ("Data de abertura", "data_abertura"),
    ("Data de conclusão", "data_conclusao"), ("Cliente", "cliente"),
]


def _valor(atributo, texto):
    texto = texto.strip()
    if not texto:
        raise ValueError("valor vazio")
    if atributo == "complexidade":
        if texto.lower() not in COMPLEXIDADES:
            raise ValueError("use Baixa, Normal, Alta ou Crítico")
        return COMPLEXIDADES[texto.lower()]
    if atributo in ("data_abertura", "data_conclusao"):
        return datetime.strptime(texto, "%d/%m/%Y %H:%M")
    return texto


def _editar(item):
    d = item["demanda"]
    print("\nQual campo alterar?")
    for n, (rotulo, _) in enumerate(CAMPOS, 1):
        print(f"  {n}. {rotulo}")
    escolha = input("Número do campo (ENTER para cancelar): ").strip()
    if not escolha.isdigit() or not 1 <= int(escolha) <= len(CAMPOS):
        return
    rotulo, atributo = CAMPOS[int(escolha) - 1]
    dica = " (dd/mm/aaaa hh:mm)" if atributo.startswith("data_") else ""
    novo = input(f"Novo valor de '{rotulo}'{dica}: ")
    try:
        item["demanda"] = d.model_copy(update={atributo: _valor(atributo, novo)})
        item["avisos"] = [a for a in item["avisos"] if "conclusão anterior" not in a
                          or item["demanda"].data_conclusao < item["demanda"].data_abertura]
        print("Alterado.")
    except ValueError as erro:
        print(f"Valor inválido: {erro}. Nada foi alterado.")


def resolver_duplicadas(itens):
    """Pergunta, caso a caso, se uma demanda que já existe na lista deve ser registrada mesmo assim."""
    mantidas = []
    for item in itens:
        if not item.get("duplicada"):
            mantidas.append(item)
            continue
        d = item["demanda"]
        print(f"\nJá existe na lista: '{d.problema}' | abertura {d.data_abertura:%d/%m/%Y %H:%M} | cliente {d.cliente}")
        if input("Registrar mesmo assim? (s/n): ").strip().lower() == "s":
            mantidas.append(item)
        else:
            print("Removida da prévia.")
    return mantidas


def conferir(itens):
    """Laço de conferência. Devolve a lista final confirmada, ou [] se o operador cancelar."""
    itens = resolver_duplicadas(list(itens))
    while True:
        print("\n" + texto_previa(itens))
        if not itens:
            return []
        resp = input("Há alguma alteração? Digite o número da demanda para editar, "
                     "'x N' para remover, ou ENTER para confirmar: ").strip().lower()
        if not resp:
            pendentes = sum(1 for i in itens if i["avisos"])
            if pendentes:
                print(f"\nAtenção: {pendentes} demanda(s) com aviso REVISAR.")
            final = input(f"Confirmar o envio de {len(itens)} demanda(s) ao SharePoint? "
                          f"Digite 'sim' para confirmar: ").strip().lower()
            if final == "sim":
                return itens
            print("Envio não confirmado. Voltando à conferência.")
        elif resp.startswith("x ") and resp[2:].strip().isdigit():
            n = int(resp[2:].strip())
            if 1 <= n <= len(itens):
                itens.pop(n - 1)
                print(f"Demanda {n} removida.")
        elif resp.isdigit() and 1 <= int(resp) <= len(itens):
            _editar(itens[int(resp) - 1])
        else:
            print("Opção não reconhecida.")
