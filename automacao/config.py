"""Constantes e caminhos do projeto (funcionam no código-fonte e no programa empacotado).

Tudo que é específico do órgão (nomes de caixa, domínio, clientes do SharePoint) vem do arquivo .env,
para não ficar no código versionado. Veja .env.example.

No programa empacotado, os dados do operador (.env, lista de estagiários, saídas) ficam em
%APPDATA%\\RegistroDemandas; os recursos fixos (Tesseract, idioma) ficam dentro do próprio programa.
"""
import os
import shutil
import sys
from pathlib import Path

import pytesseract
from dotenv import load_dotenv

EMPACOTADO = getattr(sys, "frozen", False)


def _pastas():
    if EMPACOTADO:
        recursos = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        dados = Path(os.environ.get("APPDATA") or Path.home()) / "RegistroDemandas"
    else:
        recursos = dados = Path(__file__).resolve().parent.parent
    dados.mkdir(parents=True, exist_ok=True)
    return recursos, dados


RECURSOS, RAIZ = _pastas()      # RAIZ = pasta de dados do operador
ARQUIVO_ENV = RAIZ / ".env"
SAIDA = RAIZ / "saida"
ROSTER = RAIZ / "config" / "estagiarios.csv"
CACHE_OCR = SAIDA / "cache_ocr.json"


def _semear():
    """Primeira execução de um pacote interno: copia a configuração que acompanha o programa."""
    if not EMPACOTADO:
        return
    inicial = Path(sys.executable).resolve().parent / "configuracao-inicial"
    if not inicial.is_dir():
        return
    ROSTER.parent.mkdir(parents=True, exist_ok=True)
    for origem, destino in ((inicial / ".env", ARQUIVO_ENV), (inicial / "estagiarios.csv", ROSTER)):
        if origem.exists() and not destino.exists():
            shutil.copy2(origem, destino)


def garantir_roster():
    """Garante que existe config/estagiarios.csv (copia o exemplo se não houver)."""
    if not ROSTER.exists():
        ROSTER.parent.mkdir(parents=True, exist_ok=True)
        exemplo = RECURSOS / "config" / "estagiarios.exemplo.csv"
        if exemplo.exists():
            shutil.copy2(exemplo, ROSTER)
    return ROSTER


_semear()
load_dotenv(ARQUIVO_ENV)        # não sobrescreve variáveis já definidas no ambiente


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


# Tesseract: usa a cópia que acompanha o programa; se não houver, a instalada no Windows.
_TESSERACT_EMBUTIDO = RECURSOS / "tesseract" / "tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = (
    str(_TESSERACT_EMBUTIDO) if _TESSERACT_EMBUTIDO.exists()
    else r"C:\Program Files\Tesseract-OCR\tesseract.exe")
os.environ["TESSDATA_PREFIX"] = str(RECURSOS / "tessdata")
