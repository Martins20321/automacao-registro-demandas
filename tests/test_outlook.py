"""Testes da localização da caixa, com objetos falsos (sem precisar do Outlook instalado)."""
from automacao import outlook


class FakeStore:
    def __init__(self, nome):
        self.DisplayName = nome


class FakeNS:
    def __init__(self, nomes):
        self.Stores = [FakeStore(n) for n in nomes]


def test_localizar_loja_exato():
    ns = FakeNS(["Caixa Pessoal", "Portal CODEV"])
    assert outlook.localizar_loja(ns, "Portal CODEV").DisplayName == "Portal CODEV"


def test_localizar_loja_ignora_caixa_e_espacos():
    ns = FakeNS(["Caixa Pessoal", "  portal codev  "])
    assert outlook.localizar_loja(ns, "Portal CODEV") is not None


def test_localizar_loja_nao_encontrada():
    ns = FakeNS(["Caixa Pessoal"])
    assert outlook.localizar_loja(ns, "Portal CODEV") is None


def test_nomes_das_caixas():
    ns = FakeNS(["A", "B"])
    assert outlook.nomes_das_caixas(ns) == ["A", "B"]


class FakeFolder:
    def __init__(self, nome, irmas=()):
        self.Name = nome
        self.Parent = type("Raiz", (), {"Folders": list(irmas)})()


def test_pasta_enviados_irma_encontra_em_portugues():
    enviados = FakeFolder("Itens Enviados")
    entrada = FakeFolder("Caixa de Entrada", irmas=[FakeFolder("Caixa de Entrada"), enviados])
    assert outlook._pasta_enviados_irma(entrada) is enviados


def test_pasta_enviados_irma_encontra_em_ingles_e_ignora_caixa():
    enviados = FakeFolder("SENT ITEMS")
    entrada = FakeFolder("Inbox", irmas=[enviados])
    assert outlook._pasta_enviados_irma(entrada) is enviados


def test_pasta_enviados_irma_nao_encontrada():
    entrada = FakeFolder("Caixa de Entrada", irmas=[FakeFolder("Rascunhos")])
    assert outlook._pasta_enviados_irma(entrada) is None
