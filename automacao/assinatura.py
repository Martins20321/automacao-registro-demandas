"""Extração da imagem de assinatura, OCR local e identificação do responsável."""
import hashlib
import json
import re
from pathlib import Path

import pytesseract
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
from pytesseract import Output
from rapidfuzz import fuzz, process

from .config import CACHE_OCR, DOMINIO_INTERNO, PR_CONTENT_ID, SAIDA
from .util import norm

MARCAS_HISTORICO = [
    'id="divRplyFwdMsg"', "id=divRplyFwdMsg", 'name="_MailOriginal"', "name=_MailOriginal",
    'id="mail-editor-reference-message-container"', "border-top:solid #E1E1E1",
    "border-top:solid #B5C4DF",
]


# ---------- imagens do e-mail ----------
def cortar_historico(html):
    posicoes = [html.find(m) for m in MARCAS_HISTORICO if html.find(m) >= 0]
    return html[: min(posicoes)] if posicoes else html


def extrair_imagens(msg):
    """Salva em saida/ as imagens CID do topo da mensagem (sem o histórico citado)."""
    html = cortar_historico(msg.HTMLBody or "")
    soup = BeautifulSoup(html, "lxml")
    srcs = [img.get("src", "") for img in soup.find_all("img")]
    cids = [s[4:].strip("<>").lower() for s in srcs if s.lower().startswith("cid:")]
    por_cid = {}
    for anexo in msg.Attachments:
        try:
            cid = anexo.PropertyAccessor.GetProperty(PR_CONTENT_ID)
        except Exception:
            cid = None
        if cid:
            por_cid[cid.strip("<>").lower()] = anexo
    SAIDA.mkdir(exist_ok=True)
    salvas = []
    for n, cid in enumerate(cids, 1):
        anexo = por_cid.get(cid)
        if anexo is None:
            continue
        caminho = SAIDA / f"assinatura_tmp_{n}_{Path(anexo.FileName).name}"
        anexo.SaveAsFile(str(caminho))
        salvas.append(caminho)
    return salvas


# ---------- OCR ----------
def preparar(caminho):
    img = Image.open(caminho)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fundo = Image.new("RGBA", img.size, "white")
        fundo.alpha_composite(img)
        img = fundo
    img = ImageOps.autocontrast(img.convert("L"))
    if img.width < 1800:
        img = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
    return img


def ler_linhas(img):
    dados = pytesseract.image_to_data(img, lang="por", config="--psm 11", output_type=Output.DICT)
    linhas = {}
    for i, palavra in enumerate(dados["text"]):
        palavra = palavra.strip()
        if not palavra or float(dados["conf"][i]) < 0:
            continue
        chave = (dados["block_num"][i], dados["par_num"][i], dados["line_num"][i])
        linhas.setdefault(chave, []).append((palavra, dados["height"][i]))
    return [
        {"texto": " ".join(p for p, _ in ps), "altura": sum(h for _, h in ps) / len(ps)}
        for ps in linhas.values()
    ]


def escolher_nome(linhas):
    candidatas = [
        l for l in linhas
        if "@" not in l["texto"] and not re.search(r"\d", l["texto"])
        and len(re.findall(r"[A-Za-zÀ-ú]{2,}", l["texto"])) >= 2
    ]
    return max(candidatas, key=lambda l: l["altura"])["texto"] if candidatas else ""


def extrair_email(linhas):
    """Aceita o '@' lido como outro símbolo (ex.: 'Jose.msilvaômme.gov.br')."""
    texto = " ".join(l["texto"] for l in linhas)
    dominio = DOMINIO_INTERNO.lstrip("@")
    if not dominio:
        return ""
    achado = re.search(rf"([A-Za-z0-9._-]+)[^A-Za-z0-9._\s-]?\s?{re.escape(dominio)}", texto)
    return f"{achado.group(1)}@{dominio}".lower() if achado else ""


def ocr_com_cache(caminho, cache):
    """Lê nome e e-mail da imagem; reaproveita o resultado se a imagem já foi vista."""
    chave = hashlib.sha256(Path(caminho).read_bytes()).hexdigest()
    if chave in cache:
        return cache[chave]
    linhas = ler_linhas(preparar(caminho))
    resultado = {"nome": escolher_nome(linhas), "email": extrair_email(linhas)}
    cache[chave] = resultado
    return resultado


def carregar_cache():
    try:
        return json.loads(CACHE_OCR.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_cache(cache):
    SAIDA.mkdir(exist_ok=True)
    CACHE_OCR.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- decisão ----------
def casar(nome_ocr, email_ocr, roster):
    """Compara o OCR com a lista oficial. Devolve (registro, nota_nome, nota_email)."""
    if not nome_ocr:
        return None, 0, 0
    _, nota_nome, idx = process.extractOne(
        norm(nome_ocr), [norm(r["nome"]) for r in roster], scorer=fuzz.token_sort_ratio)
    registro = roster[idx]
    nota_email = 0
    if email_ocr and registro["email"]:
        nota_email = fuzz.ratio(email_ocr.lower(), registro["email"].lower())
    return registro, nota_nome, nota_email


def identificar_responsavel(msg, roster, cache):
    """Responsável pela assinatura da mensagem: {'registro','ok','nota_nome','nota_email','motivo'}."""
    imagens = extrair_imagens(msg)
    if not imagens:
        return {"registro": None, "ok": False, "nota_nome": 0, "nota_email": 0,
                "motivo": "sem imagem de assinatura por CID"}
    melhor = None
    for caminho in imagens:
        lido = ocr_com_cache(caminho, cache)
        registro, nn, ne = casar(lido["nome"], lido["email"], roster)
        pontos = nn + ne / 10
        if registro and (melhor is None or pontos > melhor[0]):
            melhor = (pontos, registro, nn, ne)
        caminho.unlink(missing_ok=True)
    if melhor is None:
        return {"registro": None, "ok": False, "nota_nome": 0, "nota_email": 0,
                "motivo": "nome não reconhecido pelo OCR"}
    _, registro, nn, ne = melhor
    ok = nn >= 90 or (nn >= 80 and ne >= 90)
    return {"registro": registro, "ok": ok, "nota_nome": nn, "nota_email": ne,
            "motivo": "" if ok else "confiança baixa no OCR"}
