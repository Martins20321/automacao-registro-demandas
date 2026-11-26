"""Testes da conexão com a IA: proxy, explicação de erros, teste de alcance e falha rápida."""
import types

import groq
import httpx
import pytest

from automacao import ia, rede


def _cliente_falso(manipulador):
    return httpx.Client(transport=httpx.MockTransport(manipulador))


def test_proxies_detectados_mascara_senha(monkeypatch):
    monkeypatch.setattr(rede.urllib.request, "getproxies",
                        lambda: {"https": "http://usuario:segredo@proxy.orgao.gov.br:8080"})
    detectados = rede.proxies_detectados()
    assert detectados == {"https": "http://proxy.orgao.gov.br:8080"}
    assert "segredo" not in str(detectados)


def test_explicar_erro_de_tempo_esgotado():
    texto = rede.explicar_erro(httpx.ConnectTimeout("timed out"))
    assert "tempo esgotado" in texto and "api.groq.com" in texto


def test_explicar_erro_de_proxy_e_de_certificado():
    assert "proxy" in rede.explicar_erro(httpx.ProxyError("falhou")).lower()
    assert "certificado" in rede.explicar_erro(httpx.ConnectError("CERTIFICATE_VERIFY_FAILED"))


def test_explicar_erro_olha_a_causa_encadeada():
    try:
        try:
            raise httpx.ConnectTimeout("sem resposta")
        except httpx.ConnectTimeout as causa:
            raise RuntimeError("Request timed out.") from causa
    except RuntimeError as erro:
        assert "tempo esgotado" in rede.explicar_erro(erro)


@pytest.mark.parametrize("status,chave,ok,trecho", [
    (200, "k", True, "chave foi aceita"),
    (401, "", True, "sem chave"),
    (401, "k", False, "recusada"),
    (403, "k", False, "bloqueio"),
    (500, "k", False, "inesperada"),
])
def test_testar_conexao_por_status(monkeypatch, status, chave, ok, trecho):
    cliente = _cliente_falso(lambda requisicao: httpx.Response(status))
    resultado, detalhe = rede.testar_conexao(chave, cliente=cliente)
    assert resultado is ok and trecho in detalhe


def test_testar_conexao_sem_rede(monkeypatch):
    def manipulador(requisicao):
        raise httpx.ConnectTimeout("timed out", request=requisicao)
    resultado, detalhe = rede.testar_conexao("k", cliente=_cliente_falso(manipulador))
    assert resultado is False and "tempo esgotado" in detalhe


def test_handshake_lento_nao_e_confundido_com_certificado():
    erro = httpx.ConnectTimeout("_ssl.c:993: The handshake operation timed out")
    texto = rede.explicar_erro(erro)
    assert "tempo esgotado" in texto and "certificado" not in texto


def test_conexao_lenta_mas_funcional_e_avisada(monkeypatch):
    relogio = iter([100.0, 111.5])                       # 11,5 s de handshake
    # troca só o `time` do módulo rede (trocar time.perf_counter global quebraria httpx/pytest)
    monkeypatch.setattr(rede, "time", types.SimpleNamespace(perf_counter=lambda: next(relogio)))
    cliente = _cliente_falso(lambda requisicao: httpx.Response(200))
    ok, detalhe = rede.testar_conexao("k", cliente=cliente)
    assert ok is True and "11.5 s" in detalhe and "lenta, mas funciona" in detalhe


def test_cliente_http_tem_tempos_generosos_e_keepalive():
    cliente = rede.criar_cliente_http()
    try:
        assert cliente.timeout.connect == rede.TEMPO_CONEXAO >= 30
        assert cliente.timeout.read == rede.TEMPO_RESPOSTA
    finally:
        cliente.close()


class _Completions:
    def __init__(self, erro):
        self.chamadas = 0
        self.erro = erro

    def create(self, **kwargs):
        self.chamadas += 1
        raise self.erro


def _provedor_com(erro, monkeypatch):
    provedor = object.__new__(ia.ProvedorGroq)
    provedor.modelo = "m"
    completions = _Completions(erro)
    provedor.cliente = type("C", (), {"chat": type("Ch", (), {"completions": completions})()})()
    monkeypatch.setattr(ia.time, "sleep", lambda s: None)
    return provedor, completions


def test_completar_json_falha_rapido_com_erro_de_conexao(monkeypatch):
    erro = groq.APITimeoutError(request=httpx.Request("POST", "https://api.groq.com"))
    provedor, completions = _provedor_com(erro, monkeypatch)
    with pytest.raises(rede.ErroConexaoIA) as excecao:
        provedor.completar_json("instrucoes", "conteudo")
    assert completions.chamadas == 2                    # uma nova tentativa e desiste
    assert "Não consegui falar com a IA" in str(excecao.value)
