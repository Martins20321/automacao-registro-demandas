"""Monta a conversa (recebidas + enviadas) em ordem cronológica, com texto limpo e anonimizado."""
from . import outlook
from .anonimizar import Mascara, anonimizar, html_para_texto
from .config import DOMINIO_INTERNO
from .modelos import MensagemConversa

LIMITE_MENSAGENS = 12  # primeira mensagem + as mais recentes


def montar_conversa(ns, entrada, enviados, recebidas, enviadas, roster, limite=LIMITE_MENSAGENS):
    registros = [("recebida", r) for r in recebidas] + [("enviada", r) for r in enviadas]
    registros.sort(key=lambda par: par[1]["data"])
    if len(registros) > limite:
        registros = registros[:1] + registros[-(limite - 1):]

    abertas = []
    for direcao, reg in registros:
        msg = outlook.abrir_mensagem(ns, entrada if direcao == "recebida" else enviados, reg)
        abertas.append({
            "direcao": direcao, "data": reg["data"], "texto": html_para_texto(msg.HTMLBody or ""),
            "assunto": msg.Subject or "", "nome": msg.SenderName or "",
            "interno": outlook.smtp_remetente(msg).endswith(DOMINIO_INTERNO),
        })

    nomes = [r["nome"] for r in roster] + [a["nome"] for a in abertas if a["nome"]]
    mascara = Mascara()  # um mapeamento só para a conversa inteira
    mensagens = [
        MensagemConversa(
            indice=i, direcao=a["direcao"], data=a["data"],
            texto=anonimizar(a["texto"], nomes, mascara),
            assunto=a["assunto"], remetente_nome=a["nome"], remetente_interno=a["interno"])
        for i, a in enumerate(abertas)
    ]
    return mensagens, mascara
