"""Análise da conversa por IA: classificação, resumo e escolha das mensagens-chave.

O provedor fica atrás de uma interface mínima (ProvedorLLM), para trocar Groq por
Azure OpenAI ou outro sem mexer no restante. A IA só recebe texto anonimizado e devolve
JSON validado por Pydantic. Ela nunca executa ações.
"""
import getpass
import os
import sys
import time
from typing import Protocol

from dotenv import load_dotenv
from pydantic import ValidationError

from . import envfile, rede
from .config import ARQUIVO_ENV
from .modelos import AnaliseIA, MensagemConversa
from .progresso import emitir
from .rede import ErroConexaoIA

INSTRUCOES = """Você analisa conversas de e-mail do suporte de TI do Ministério de Minas e Energia (MME).
A equipe cuida do portal institucional (Plone, chamado "Portal") e do sistema de Consultas Públicas.
O texto está anonimizado: [PESSOA], [EMAIL], [TELEFONE], [LINK:host]. Não tente descobrir identidades.
Mensagens "recebida" vêm do usuário; "enviada" vêm da equipe. Use SOMENTE o conteúdo da conversa.

Classifique o campo "tipo":
- "demanda": o usuário pediu uma ação e a equipe a executou (alterar página, publicar, ativar conta etc.).
- "esclarecimento": o usuário só perguntou (como faz, se pode, o que aconteceu) e a equipe respondeu ou
  orientou. ATENÇÃO: esclarecimento TAMBÉM é registrado como demanda. Nesse caso escreva "solicitacao" como
  "esclarecimento sobre ..." (o que ele quis saber) e "providencia" com a orientação dada
  (ex.: "A equipe orientou que ...").
- "encaminhamento": a equipe só repassou a outro responsável. Em Consultas Públicas a equipe FAZ: ativação
  de conta de usuário e alteração de PERFIL (por exemplo, cadastrar como GESTOR para poder contribuir ou
  cadastrar nova consulta). A equipe NÃO faz: trocar o e-mail do usuário (exige acesso ao banco de dados),
  anexar, substituir ou excluir documento anexado, e erro ao redefinir senha que não seja engano do usuário.
  Esses últimos são da empresa de software ("fábrica"), portanto "encaminhamento".
  ATENÇÃO: "encaminhamento" é quando o usuário PEDIU que a equipe EXECUTASSE algo da fábrica e a equipe só
  repassou. Se o usuário apenas PERGUNTOU como fazer algo (inclusive coisa da fábrica) e a equipe respondeu ou
  orientou, mesmo dizendo que é com a fábrica, o tipo é "esclarecimento".
- "sem_resposta_util": o usuário perguntou e a equipe não deu resposta útil (não soube responder ou não
  resolveu nada). Esse tipo NÃO é registrado.
  Perfis da Consulta Pública: ADMIN, PARTICIPANTE (padrão no cadastro), GESTOR (definido pela equipe) e
  TI_SUPORTE. Quem precisa cadastrar uma consulta ou contribuir como gestor recebe o perfil GESTOR.
  Pedido de reunião por Teams para resolver problema de login, atendido pela equipe, é "demanda".
  REUNIÃO: quando houver pedido ou agendamento de reunião, NÃO descreva só a reunião. Recupere nas mensagens
  anteriores o MOTIVO (os erros ou dificuldades que o usuário enfrentava) e escreva a solicitação com ele.
  Exemplo de solicitacao: "reunião, pois enfrentava erro ao fazer login na plataforma" e de providencia:
  "Foi agendada uma reunião pelo Teams para melhor entendimento do problema."

"sistema": "Portal" (portal institucional), "Consultas Públicas" ou "Outro" (qualquer outro sistema).
"tarefa": classifique o que a equipe EXECUTOU:
- "ativacao_conta_cp": ativação ou reativação de conta de usuário na Consulta Pública;
- "alteracao_perfil_cp": alteração de perfil (por exemplo GESTOR) na Consulta Pública;
- "troca_quem_e_quem": troca ou atualização de pessoa ou de currículo na página "Quem é Quem" do portal;
- "outra": qualquer outra tarefa (modificar página, incluir ou apagar conteúdo, criar algo etc.).
Não decida a complexidade: o programa a define pela tarefa.

A resposta de conclusão ("indice_conclusao") é SEMPRE a ÚLTIMA mensagem enviada da conversa. Em
"providencia" descreva o que a equipe fez, com base nessa última resposta (as anteriores servem só de
contexto: por exemplo, se a equipe primeiro pediu dados e depois executou, a providência é a execução).
Se a conversa tiver várias solicitações, escolha a ÚLTIMA solicitação real do usuário
("indice_solicitacao"), anterior à conclusão. Mensagens de agradecimento não são solicitações.

"solicitacao": o que foi pedido, começando direto pelo núcleo do pedido, SEM sujeito e SEM o verbo
"solicitou". Exemplo certo: "a inclusão do nome [PESSOA_2] na página da Secretaria". Exemplo errado: "o usuário
solicitou a inclusão ...". Mantenha os marcadores [PESSOA_n] exatamente como aparecem.
"providencia": o que a equipe fez ou informou, em UMA frase completa com sujeito, começando com letra
maiúscula. Exemplo: "A equipe incluiu o nome solicitado na página." Se só houve confirmação genérica,
use "A demanda foi devidamente atendida."
"motivo": explique em uma frase POR QUE escolheu esse tipo (não cite números de índice).
Os campos "indice_solicitacao" e "indice_conclusao" são SEMPRE números inteiros existentes na conversa;
se não houver resposta enviada, o tipo deve ser "encaminhamento" e use o último índice enviado ou recebido.
Não invente nada. Se não houver informação suficiente, use confianca "baixa".

"solicitante_token": se o texto do usuário se identifica pelo nome (ex.: "Meu nome é [PESSOA_3]"), o marcador
[PESSOA_n] que corresponde ao NOME DE QUEM FAZ a solicitação; caso contrário, "" (string vazia).

Responda SOMENTE com um objeto JSON com as chaves: tipo, sistema, tarefa, indice_solicitacao,
indice_conclusao, solicitacao, providencia, solicitante_token, confianca ("alta"|"media"|"baixa"), motivo."""


NAO_REGISTRADOS = ("encaminhamento", "sem_resposta_util")  # tipos que ficam de fora do registro


class ProvedorLLM(Protocol):
    def completar_json(self, instrucoes: str, conteudo: str) -> str: ...


MODELO_PADRAO = "openai/gpt-oss-120b"


def chave_configurada():
    load_dotenv(ARQUIVO_ENV)
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def salvar_chave(chave):
    """Guarda a chave no .env (só neste computador) e no ambiente do programa."""
    chave = chave.strip()
    envfile.salvar(ARQUIVO_ENV, {"GROQ_API_KEY": chave})
    os.environ["GROQ_API_KEY"] = chave


def _obter_chave():
    """Lê a chave do .env; no terminal, na primeira execução, pede ao operador."""
    if chave_configurada() or not sys.stdin or not sys.stdin.isatty():
        return os.getenv("GROQ_API_KEY", "").strip()
    print("\nPrimeira execução: informe a chave da API do Groq (console.groq.com).")
    print("Ela fica guardada só neste computador, no arquivo .env, e não aparece na tela.")
    chave = getpass.getpass("Chave do Groq: ").strip()
    if chave:
        salvar_chave(chave)
    return chave


class ProvedorGroq:
    def __init__(self):
        chave = _obter_chave()
        if not chave:
            raise RuntimeError("GROQ_API_KEY não definida. Preencha o arquivo .env (veja .env.example).")
        import httpx
        from groq import Groq
        self.chave = chave
        # Cliente que respeita proxy e certificados do Windows. O tempo de conexão é generoso porque o
        # handshake com a IA chegou a levar mais de 11 s (o padrão do SDK, 5 s, dava "Request timeout").
        self.http = rede.criar_cliente_http()
        self.cliente = Groq(api_key=chave, http_client=self.http, max_retries=1,
                            timeout=httpx.Timeout(rede.TEMPO_RESPOSTA, connect=rede.TEMPO_CONEXAO))
        self.modelo = os.getenv("GROQ_MODEL", MODELO_PADRAO)

    def verificar_conexao(self):
        """Falha logo, com mensagem clara, se a rede bloqueia a IA; também aquece a conexão."""
        ok, detalhe = rede.testar_conexao(self.chave, cliente=self.http)
        if not ok:
            raise ErroConexaoIA(detalhe)
        emitir(f"  IA: {detalhe}")

    def completar_json(self, instrucoes, conteudo):
        from groq import APIConnectionError, RateLimitError  # APITimeoutError é um APIConnectionError
        falhas_conexao = 0
        for tentativa in range(1, 6):
            try:
                resposta = self.cliente.chat.completions.create(
                    model=self.modelo, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": instrucoes},
                              {"role": "user", "content": conteudo}])
                return resposta.choices[0].message.content
            except RateLimitError:
                if tentativa >= 4:
                    raise
                espera = 15 * tentativa
                emitir(f"  (limite de requisições do Groq; aguardando {espera}s)")
                time.sleep(espera)
            except APIConnectionError as erro:
                falhas_conexao += 1
                if falhas_conexao >= 2:
                    raise ErroConexaoIA(rede.explicar_erro(erro)) from erro
                emitir("  (a IA não respondeu; tentando de novo)")
                time.sleep(2)


def formatar_conversa(mensagens: list[MensagemConversa]) -> str:
    blocos = []
    for m in mensagens:
        texto = m.texto[:1500] or "(sem texto)"
        blocos.append(f"[{m.indice}] {m.direcao} em {m.data:%d/%m/%Y %H:%M}\n{texto}")
    return "\n\n".join(blocos)


def analisar(mensagens: list[MensagemConversa], provedor: ProvedorLLM) -> AnaliseIA:
    conteudo = formatar_conversa(mensagens)
    ultimo_erro = None
    for _ in range(2):  # uma nova tentativa se o JSON vier inválido
        bruto = provedor.completar_json(INSTRUCOES, conteudo)
        try:
            analise = AnaliseIA.model_validate_json(bruto)
        except ValidationError as erro:
            ultimo_erro = erro
            continue
        if analise.tipo in NAO_REGISTRADOS:
            return analise  # não será registrada: os índices não importam
        indices = {m.indice: m for m in mensagens}
        sol, con = indices.get(analise.indice_solicitacao), indices.get(analise.indice_conclusao)
        if sol and con and sol.direcao == "recebida" and con.direcao == "enviada" and con.data >= sol.data:
            # A conclusão é sempre a última resposta enviada (a mesma usada para ler a assinatura)
            ultima = max((m for m in mensagens if m.direcao == "enviada"), key=lambda m: m.indice)
            if ultima.indice != analise.indice_conclusao and ultima.data >= sol.data:
                analise = analise.model_copy(update={"indice_conclusao": ultima.indice})
            return analise
        ultimo_erro = ValueError("índices de solicitação/conclusão inconsistentes")
    # Reserva: conversa simples (uma só resposta enviada) usa a regra fixa, marcada com confiança baixa
    recebidas = [m for m in mensagens if m.direcao == "recebida"]
    enviadas = [m for m in mensagens if m.direcao == "enviada"]
    if len(enviadas) == 1 and recebidas and recebidas[0].data <= enviadas[0].data:
        return analise.model_copy(update={"indice_solicitacao": recebidas[0].indice,
                                          "indice_conclusao": enviadas[0].indice,
                                          "confianca": "baixa"})
    raise ValueError(f"Resposta da IA inválida: {ultimo_erro}")
