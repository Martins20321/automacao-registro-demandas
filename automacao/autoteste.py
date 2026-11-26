"""Verificação da instalação: Tesseract, OCR, configuração, lista de estagiários, chave e Outlook."""
import os

from . import config, ia, outlook, rede
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
    ok_rede, detalhe_rede = rede.testar_conexao(os.getenv("GROQ_API_KEY", "").strip())
    registrar("Conexão com a IA (Groq)", ok_rede, detalhe_rede)

    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            lojas = outlook.nomes_das_caixas(ns)
            achada = outlook.localizar_loja(ns, config.LOJA) is not None if config.LOJA else None
            registrar("Outlook clássico acessível", True,
                      f"{len(lojas)} conta(s)/caixa(s) no perfil: {', '.join(lojas) if lojas else '(nenhuma)'}")
            if config.LOJA:
                if achada:
                    registrar(f"Caixa '{config.LOJA}' no perfil do Outlook", True)
                else:
                    partes = ["copie em Configurações exatamente um destes nomes: "
                             + (", ".join(lojas) if lojas else "(nenhuma caixa visível)")]
                    _, _, passos = outlook.diagnosticar_caixa_compartilhada(ns, config.CAIXA_EMAIL)
                    ok_email = bool(passos) and passos[-1].startswith("Itens Enviados encontrados")
                    partes.append("tentativa pelo e-mail da caixa: " + " | ".join(passos))
                    registrar(f"Caixa '{config.LOJA}' no perfil do Outlook", ok_email, " — ".join(partes))
                try:
                    entrada, enviados = outlook.abrir_pastas(ns)
                    registrar("Pastas da caixa abertas", True,
                              f"Caixa de Entrada com {entrada.Items.Count} item(ns), "
                              f"Itens Enviados com {enviados.Items.Count} item(ns)")
                except Exception as erro:
                    registrar("Pastas da caixa abertas", False, str(erro)[:300])
        finally:
            pythoncom.CoUninitialize()
    except Exception as erro:
        registrar("Outlook clássico acessível", False, "abra o Outlook clássico (" + str(erro)[:80] + ")")

    return "\n".join(linhas), tudo_ok
