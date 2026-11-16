"""Constantes e caminhos do projeto (funcionam no código-fonte e no executável).

Tudo que é específico do órgão (nomes de caixa, domínio, clientes do SharePoint) vem do arquivo .env,
para não ficar no código versionado. Veja .env.example.
"""
import os
import sys
from pathlib import Path

import pytesseract
from dotenv import load_dotenv


def _raiz():
    """Pasta do projeto; no executável (PyInstaller), a pasta onde está o .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RAIZ = _raiz()
load_dotenv(RAIZ / ".env")          # não sobrescreve variáveis já definidas no ambiente

SAIDA = RAIZ / "saida"
ROSTER = RAIZ / "config" / "estagiarios.csv"
CACHE_OCR = SAIDA / "cache_ocr.json"


def _cfg(nome):
    return os.getenv(nome, "").strip()


# --- Específicos do órgão (definidos no .env) ---
LOJA = _cfg("OUTLOOK_ARMAZENAMENTO")                  # nome da caixa compartilhada no painel do Outlook
DOMINIO_INTERNO = _cfg("DOMINIO_INTERNO")             # ex.: @orgao.gov.br
CLIENTE_CP = _cfg("CLIENTE_CONSULTAS_PUBLICAS")       # Cliente de demandas externas de Consultas Públicas
CLIENTE_PORTAL = _cfg("CLIENTE_PORTAL_EXTERNO")       # Cliente de demandas externas do portal
OBRIGATORIAS = {
    "OUTLOOK_ARMAZENAMENTO": LOJA, "DOMINIO_INTERNO": DOMINIO_INTERNO,
    "CLIENTE_CONSULTAS_PUBLICAS": CLIENTE_CP, "CLIENTE_PORTAL_EXTERNO": CLIENTE_PORTAL,
}

# --- Constantes do Outlook (não dependem do órgão) ---
PASTA_ENTRADA, PASTA_ENVIADOS = 6, 5
CATEGORIA_FEITO = "Feito"
# Categorias do Outlook que NÃO são nomes de estagiário (extras opcionais em CATEGORIAS_IGNORADAS, separadas por vírgula)
CATEGORIAS_NAO_PESSOA = {"feito", "em atendimento", "encaminhamento"} | {
    c.strip().lower() for c in os.getenv("CATEGORIAS_IGNORADAS", "").split(",") if c.strip()}
PR_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"


def configuracao_faltando():
    """Nomes das variáveis obrigatórias do .env que estão vazias."""
    return [nome for nome, valor in OBRIGATORIAS.items() if not valor]


# Tesseract: usa a cópia que acompanha o executável; se não houver, a instalada no Windows.
_TESSERACT_EMBUTIDO = RAIZ / "tesseract" / "tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = (
    str(_TESSERACT_EMBUTIDO) if _TESSERACT_EMBUTIDO.exists()
    else r"C:\Program Files\Tesseract-OCR\tesseract.exe")
os.environ["TESSDATA_PREFIX"] = str(RAIZ / "tessdata")
