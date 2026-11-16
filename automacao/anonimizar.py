"""Limpeza e anonimização REVERSÍVEL do texto antes de enviá-lo a qualquer serviço de IA.

Dados pessoais comuns (e-mail, telefone, CPF, links) são trocados por marcadores fixos.
Nomes de pessoas viram [PESSOA_n]; o mapeamento fica só na memória local e é usado para
recolocar os nomes reais na descrição final. Assim a IA nunca vê o nome, mas o registro o mostra.

Limite conhecido: a detecção de nomes é por regra (sequências de palavras com inicial
maiúscula, nomes de remetentes e estagiários, nome após a saudação). Um nome escrito em
minúsculas, ou um termo institucional não listado, pode passar ou ser mascarado a mais.
A conferência humana continua obrigatória.
"""
import re

from bs4 import BeautifulSoup

from .util import norm

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
TELEFONE = re.compile(r"(?<!\d)(?:\+?55[\s.-]?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}(?!\d)")
LINK = re.compile(r"https?://([^/\s]+)\S*")
SAUDACAO = re.compile(
    r"\b(Prezad[oa]s?|Ol[aá]|Caro|Cara)\s+([A-ZÀ-Ú][\wÀ-ú]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÀ-Ú][\wÀ-ú]+){0,3})")
# Duas ou mais palavras com inicial maiúscula (aceita "de/da/do/e" no meio) ou siglas longas em caixa alta
NOME_PROPRIO = re.compile(
    r"\b[A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:d[aeo]s?|e)\s+[A-ZÀ-Ú][a-zà-ú]+|\s+[A-ZÀ-Ú][a-zà-ú]+)+\b"
    r"|\b[A-ZÀ-Ú]{3,}(?:\s+[A-ZÀ-Ú]{3,})+\b")
FECHAMENTO = re.compile(
    r"^\s*(atenciosamente|respeitosamente|cordialmente|att\.?|abra[cç]os?|obrigad[oa]\.?)\W*$",
    re.IGNORECASE | re.MULTILINE)
CITACAO = re.compile(r"^\s*(De|From|Enviada em|Sent):\s.*$|^.*escreveu:\s*$",
                     re.IGNORECASE | re.MULTILINE)
MARCAS_HISTORICO_HTML = [
    'id="divRplyFwdMsg"', "id=divRplyFwdMsg", 'name="_MailOriginal"', "name=_MailOriginal",
    'id="mail-editor-reference-message-container"', "border-top:solid #E1E1E1",
    "border-top:solid #B5C4DF",
]
PALAVRAS_COMUNS = {"para", "como", "pela", "pelo", "sistema", "portal", "site"}
# Termos institucionais que ajudam a classificar e NÃO devem ser mascarados
TERMOS_VISIVEIS = {
    "consulta", "consultas", "publica", "publicas", "portal", "ministerio", "minas", "energia",
    "microsoft", "teams", "plone", "outlook", "sharepoint", "power", "secretaria", "departamento",
    "coordenacao", "diretoria", "conselho", "comite", "nacional", "gabinete", "assessoria",
    "governo", "federal", "brasil", "gov",
}
SIGLAS_VISIVEIS = {"MME", "SNTEP", "REIDI", "SEI", "PGD", "CNPE", "CNPM", "CGIT", "STI", "SREIDI", "SAPED"}


class Mascara:
    """Guarda o mapeamento [PESSOA_n] -> texto original (apenas em memória)."""

    def __init__(self):
        self.mapa = {}
        self._por_texto = {}

    def token(self, original):
        chave = norm(original)
        if chave not in self._por_texto:
            self._por_texto[chave] = f"[PESSOA_{len(self._por_texto) + 1}]"
            self.mapa[self._por_texto[chave]] = original.strip()
        return self._por_texto[chave]

    def restaurar(self, texto):
        for token, original in self.mapa.items():
            texto = texto.replace(token, original)
        return texto


def html_para_texto(html):
    """Texto do topo da mensagem: sem histórico citado, sem assinatura e sem imagens."""
    posicoes = [html.find(m) for m in MARCAS_HISTORICO_HTML if html.find(m) >= 0]
    if posicoes:
        html = html[: min(posicoes)]
    texto = BeautifulSoup(html, "lxml").get_text("\n")
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    texto = re.sub(r"\n\s*\n+", "\n\n", texto).strip()
    corte = [m.start() for m in (CITACAO.search(texto), FECHAMENTO.search(texto)) if m]
    return texto[: min(corte)].strip() if corte else texto


def _institucional(sequencia):
    palavras = re.findall(r"[A-Za-zÀ-ú]+", sequencia)
    if any(norm(p) in TERMOS_VISIVEIS for p in palavras):
        return True
    if all(p.isupper() for p in palavras):
        return all(len(p) <= 4 or p in SIGLAS_VISIVEIS for p in palavras)
    return False


def anonimizar(texto, nomes_conhecidos=(), mascara=None):
    mascara = mascara if mascara is not None else Mascara()
    texto = EMAIL.sub("[EMAIL]", texto)
    texto = CPF.sub("[CPF]", texto)
    texto = TELEFONE.sub("[TELEFONE]", texto)
    texto = LINK.sub(lambda m: f"[LINK:{m.group(1)}]", texto)
    texto = SAUDACAO.sub(lambda m: f"{m.group(1)} {mascara.token(m.group(2))}", texto)
    for nome in nomes_conhecidos:
        for parte in {nome, *nome.split()}:
            if len(parte) >= 4 and parte.lower() not in PALAVRAS_COMUNS:
                texto = re.sub(rf"\b{re.escape(parte)}\b", lambda m: mascara.token(m.group(0)),
                               texto, flags=re.IGNORECASE)
    texto = NOME_PROPRIO.sub(
        lambda m: m.group(0) if _institucional(m.group(0)) else mascara.token(m.group(0)), texto)
    return texto
