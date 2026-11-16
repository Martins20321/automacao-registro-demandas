"""Modelos de dados validados (Pydantic)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MensagemConversa(BaseModel):
    """Uma mensagem da conversa, já com o texto limpo e anonimizado para a IA."""
    indice: int
    direcao: Literal["recebida", "enviada"]
    data: datetime
    texto: str                      # anonimizado: é o que vai para a IA
    assunto: str = ""               # assunto real; NUNCA vai para a IA
    remetente_nome: str = ""        # nome real; NUNCA vai para a IA
    remetente_interno: bool = False


class AnaliseIA(BaseModel):
    """Resposta estruturada da IA para uma conversa."""
    tipo: Literal["demanda", "esclarecimento", "encaminhamento", "sem_resposta_util"]
    sistema: Literal["Portal", "Consultas Públicas", "Outro"]
    tarefa: Literal["ativacao_conta_cp", "alteracao_perfil_cp", "troca_quem_e_quem", "outra"] = "outra"
    complexidade: Literal["Baixa", "Normal", "Alta"] = "Normal"  # informativo: a decisão é por regra (registro.py)
    indice_solicitacao: int = Field(description="índice da mensagem que traz a solicitação a registrar")
    indice_conclusao: int = Field(description="índice da resposta enviada que concluiu essa solicitação")
    solicitacao: str = Field(description="o que o usuário pediu, sem o sujeito e sem o verbo 'solicitou'")
    providencia: str = Field(description="o que a equipe fez ou informou, em uma frase")
    solicitante_token: str = Field(default="", description="marcador [PESSOA_n] de quem solicita, se identificado")
    confianca: Literal["alta", "media", "baixa"]
    motivo: str = Field(description="justificativa curta da classificação")
