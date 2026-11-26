"""Conexão com a internet: proxy, certificados do Windows e teste de alcance da API da IA.

Em redes de órgãos públicos é comum haver proxy, firewall ou inspeção de HTTPS. Este módulo
concentra o que é preciso para (1) conectar nesses casos e (2) explicar em português o que falhou.
"""
import ssl
import time
import urllib.request
from urllib.parse import urlsplit

import httpx

URL_TESTE = "https://api.groq.com/openai/v1/models"


class ErroConexaoIA(RuntimeError):
    """Não foi possível falar com a IA (rede, proxy, firewall ou certificado)."""


def proxies_detectados():
    """Proxies que o Python enxerga (variáveis de ambiente ou configuração do Windows), sem senhas."""
    saida = {}
    for esquema, url in urllib.request.getproxies().items():
        partes = urlsplit(url)
        host = partes.hostname or url
        porta = f":{partes.port}" if partes.port else ""
        saida[esquema] = f"{partes.scheme or 'http'}://{host}{porta}"
    return saida


def _verificacao_tls():
    """Usa os certificados do Windows (necessário com inspeção de HTTPS); cai no padrão se faltar."""
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        return True


TEMPO_CONEXAO = 30.0     # o handshake TLS com a IA chegou a levar mais de 11 s; o padrão do SDK (5 s) estoura
TEMPO_RESPOSTA = 60.0


def criar_cliente_http():
    """Cliente HTTP que respeita proxy do ambiente/Windows e confia nos certificados do Windows.

    Mantém a conexão aberta por 5 minutos (keep-alive): o handshake lento é pago só na primeira chamada.
    """
    return httpx.Client(
        verify=_verificacao_tls(),
        timeout=httpx.Timeout(TEMPO_RESPOSTA, connect=TEMPO_CONEXAO),
        limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=300.0))


def _cadeia(erro):
    """O erro e as causas encadeadas (o SDK da IA embrulha o erro real de rede)."""
    visto = []
    while erro is not None and erro not in visto:
        visto.append(erro)
        erro = erro.__cause__ or erro.__context__
    return visto


def explicar_erro(erro):
    """Traduz um erro de rede para uma frase útil ao operador."""
    cadeia = _cadeia(erro)
    texto = " ".join(str(e) for e in cadeia).lower()
    if any(isinstance(e, httpx.ProxyError) for e in cadeia) or "proxy" in texto:
        causa = "o proxy da rede recusou ou não respondeu"
    elif any(isinstance(e, httpx.TimeoutException) for e in cadeia) or "timed out" in texto or "timeout" in texto:
        # vem antes do certificado: "handshake timed out" também cita ssl, mas é demora, não certificado
        causa = (f"tempo esgotado ({TEMPO_CONEXAO:.0f} s para conectar): a conexão com api.groq.com está muito "
                 "lenta ou é bloqueada por firewall/proxy")
    elif "certificate_verify_failed" in texto or "certificate verify failed" in texto or "self-signed" in texto:
        causa = "o certificado da conexão não é confiável (a rede pode inspecionar o HTTPS)"
    elif any(isinstance(e, httpx.ConnectError) for e in cadeia) or "connect" in texto:
        causa = "não foi possível abrir a conexão (sem internet, DNS ou bloqueio da rede)"
    else:
        causa = f"falha de conexão ({type(erro).__name__}: {str(erro)[:120]})"
    proxies = proxies_detectados()
    proxy = ("proxy detectado: " + ", ".join(f"{k}={v}" for k, v in proxies.items())
             if proxies else "nenhum proxy configurado neste computador")
    return (f"Não consegui falar com a IA (Groq): {causa}. {proxy.capitalize()}. "
            "Peça ao TI para liberar o endereço api.groq.com na porta 443 e, se a rede usa proxy, "
            "informe o endereço dele em Configurações > Proxy da rede.")


def testar_conexao(chave="", cliente=None):
    """Testa o alcance da API da IA. Devolve (ok, detalhe). Qualquer resposta HTTP prova que há rede.

    Se `cliente` for informado, usa e MANTÉM aberto esse cliente: a conexão fica aquecida (o handshake
    lento já foi pago) para as chamadas seguintes da IA.
    """
    proprio = cliente is None
    cliente = cliente or criar_cliente_http()
    inicio = time.perf_counter()
    try:
        cabecalhos = {"Authorization": f"Bearer {chave}"} if chave else {}
        resposta = cliente.get(URL_TESTE, headers=cabecalhos)
    except Exception as erro:
        return False, explicar_erro(erro)
    finally:
        if proprio:
            cliente.close()
    segundos = time.perf_counter() - inicio
    proxies = proxies_detectados()
    via = ("via proxy " + ", ".join(proxies.values())) if proxies else "sem proxy"
    via += f", em {segundos:.1f} s" + (" (lenta, mas funciona)" if segundos > 5 else "")
    codigo = resposta.status_code
    if codigo == 200:
        return True, f"conectou ({via}) e a chave foi aceita"
    if codigo in (401, 403) and not chave:
        return True, f"conectou ({via}); sem chave para validar"
    if codigo == 401:
        return False, f"conectou ({via}), mas a chave do Groq foi recusada (401). Confira a chave."
    if codigo == 403:
        return False, f"conectou ({via}), mas recebeu 403: possível bloqueio da rede ao acessar a IA."
    return False, f"conectou ({via}), mas a resposta foi inesperada (HTTP {codigo})."
