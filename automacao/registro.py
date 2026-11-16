"""Monta os campos da lista do SharePoint a partir da análise da IA e das regras fixas."""
import re
from datetime import datetime

from pydantic import BaseModel

from .config import CLIENTE_CP, CLIENTE_PORTAL
from .modelos import AnaliseIA, MensagemConversa

PREFIXOS_ASSUNTO = re.compile(r"^\s*((re|res|enc|fw|fwd|encaminhado)\s*:\s*)+", re.IGNORECASE)


# CLIENTE_CP e CLIENTE_PORTAL vêm do .env (pessoa/grupo que o SharePoint reconhece pelo nome)


class Demanda(BaseModel):
    problema: str
    descricao: str
    complexidade: str
    status: str = "Concluído"
    sistema: str
    atribuido_a: str
    data_abertura: datetime
    data_conclusao: datetime
    cliente: str
    origem: str = "E-mail"


def _frase(texto):
    texto = " ".join(texto.split()).strip().rstrip(".")
    return texto + "." if texto else ""


SUJEITO_REPETIDO = re.compile(
    r"^\s*((o|a)\s+)?(usu[aá]rio|solicitante|cliente)(\s+externo)?\s+(solicitou|pediu|requisitou|relatou)\s+"
    r"|^\s*(solicitou|pediu|requisitou)\s+", re.IGNORECASE)


TAREFAS_BAIXA = {"ativacao_conta_cp", "alteracao_perfil_cp", "troca_quem_e_quem"}


def complexidade_por_regra(tarefa):
    """Regra definida pela equipe: tarefas rápidas = Baixa; o resto = Normal. 'Alta' e 'Crítico' são manuais."""
    return "Baixa" if tarefa in TAREFAS_BAIXA else "Normal"


def _nome_de_pessoa(nome_exibicao):
    """Usa o nome de exibição do remetente como reserva, se parecer nome de pessoa e não de caixa/sistema."""
    nome = (nome_exibicao or "").strip()
    if "@" in nome or len(nome.split()) < 2:
        return ""
    if any(p in nome.lower() for p in ("consulta", "contribui", "portal", "mme", "suporte", "noreply")):
        return ""
    return nome


def _maiuscula(texto):
    return texto[:1].upper() + texto[1:]


def construir_demanda(analise: AnaliseIA, mensagens: list[MensagemConversa], responsavel: str,
                      mascara=None) -> Demanda:
    por_indice = {m.indice: m for m in mensagens}
    pedido, conclusao = por_indice[analise.indice_solicitacao], por_indice[analise.indice_conclusao]
    restaurar = mascara.restaurar if mascara else (lambda t: t)  # recoloca nomes reais, só localmente
    # Cliente: nome do remetente se for interno; externo = cliente de Consultas Públicas (CP) ou do portal
    if pedido.remetente_interno:
        cliente = quem = pedido.remetente_nome
    elif analise.sistema == "Consultas Públicas":
        cliente = CLIENTE_CP
        # em Consultas Públicas a descrição usa o nome que o usuário informa no corpo do e-mail
        nome_no_corpo = mascara.mapa.get(analise.solicitante_token, "") if mascara else ""
        quem = nome_no_corpo or _nome_de_pessoa(pedido.remetente_nome) or "Usuário externo"
    else:
        cliente, quem = CLIENTE_PORTAL, "Usuário externo"
    solicitacao = SUJEITO_REPETIDO.sub("", restaurar(analise.solicitacao)).strip().rstrip(".")
    providencia = _maiuscula(_frase(restaurar(analise.providencia)))
    descricao = f"{quem} solicitou {solicitacao[:1].lower() + solicitacao[1:]}. {providencia}"
    return Demanda(
        problema=PREFIXOS_ASSUNTO.sub("", pedido.assunto).strip(),
        descricao=descricao.strip(),
        # esclarecimento (questionamento respondido) é sempre Baixa; o resto segue a regra por tarefa
        complexidade="Baixa" if analise.tipo == "esclarecimento" else complexidade_por_regra(analise.tarefa),
        sistema=analise.sistema,
        atribuido_a=responsavel,
        data_abertura=pedido.data,
        data_conclusao=conclusao.data,
        cliente=cliente,
    )
