"""Verificação da instalação: Tesseract, OCR, configuração, lista de estagiários, chave e Outlook."""
from . import config, ia
from . import roster as lista


def executar():
    """Devolve (relatório em texto, True se tudo estiver certo)."""
    linhas, tudo_ok = [], True

    def registrar(nome, ok, detalhe=""):
        nonlocal tudo_ok
        tudo_ok = tudo_ok and ok
        linhas.append(f"[{'OK' if ok else 'FALHA'}] {nome}" + (f": {detalhe}" if detalhe else ""))

    try:
        import pytesseract
        registrar("Tesseract (OCR)", True, str(pytesseract.get_tesseract_version()))
        idiomas = pytesseract.get_languages(config="")
        registrar("Idioma português do OCR", "por" in idiomas, ", ".join(idiomas))
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (520, 110), "white")
        ImageDraw.Draw(img).text((12, 24), "Maria Exemplo", fill="black", font=ImageFont.load_default(size=48))
        lido = pytesseract.image_to_string(img, lang="por").strip()
        registrar("Leitura de texto em imagem", "maria" in lido.lower(), f"leu '{lido}'")
    except Exception as erro:
        registrar("Tesseract (OCR)", False, str(erro)[:160])

    faltando = config.configuracao_faltando()
    registrar("Configurações do órgão (.env)", not faltando,
              "completas" if not faltando else "faltam: " + ", ".join(faltando))
    try:
        registrar("Lista de estagiários", True, f"{len(lista.carregar())} pessoa(s) em {config.ROSTER}")
    except Exception as erro:
        registrar("Lista de estagiários", False, str(erro)[:160])
    registrar("Chave da IA (Groq)", ia.chave_configurada(), "configurada" if ia.chave_configurada() else "não informada")

    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            lojas = [s.DisplayName for s in ns.Stores]
        finally:
            pythoncom.CoUninitialize()
        registrar("Outlook clássico acessível", True, f"{len(lojas)} conta(s)/caixa(s) no perfil")
        if config.LOJA:
            registrar(f"Caixa '{config.LOJA}' no perfil do Outlook", config.LOJA in lojas)
    except Exception as erro:
        registrar("Outlook clássico acessível", False, "abra o Outlook clássico (" + str(erro)[:80] + ")")

    return "\n".join(linhas), tudo_ok
