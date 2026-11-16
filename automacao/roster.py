"""Lista oficial de estagiários e identificação do operador."""
import csv

from rapidfuzz import fuzz, process

from .config import CATEGORIAS_NAO_PESSOA, ROSTER
from .util import norm


def carregar():
    with open(ROSTER, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def identificar_operador(nome, email, roster):
    """Confere e-mail e nome informados com a lista oficial. Levanta ValueError se não bater."""
    email = (email or "").strip().lower()
    por_email = [r for r in roster if r["email"] and r["email"].lower() == email]
    if por_email:
        escolhido = por_email[0]
        if nome and fuzz.token_set_ratio(norm(nome), norm(escolhido["nome"])) < 85:
            raise ValueError(
                f"O nome '{nome}' não confere com o e-mail {email} "
                f"(na lista, esse e-mail é de outra pessoa)."
            )
        return escolhido
    if not nome:
        raise ValueError(f"E-mail {email} não está na lista oficial de estagiários.")
    achado = process.extractOne(norm(nome), [norm(r["nome"]) for r in roster],
                                scorer=fuzz.token_sort_ratio)
    if achado[1] < 90:
        raise ValueError(f"'{nome}' não foi encontrado na lista oficial de estagiários.")
    raise ValueError(
        f"O nome existe na lista, mas o e-mail informado ({email}) não confere com o cadastrado."
    )


def categoria_do_operador(operador, categorias):
    """True se alguma categoria é o nome (ou primeiro nome) do operador."""
    nome = norm(operador["nome"])
    for cat in categorias:
        c = norm(cat)
        if c and c not in CATEGORIAS_NAO_PESSOA and (nome == c or nome.startswith(c + " ")):
            return True
    return False
