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
    def __init__(self, nome, irmas=(), itens=0):
        self.Name = nome
        self.Parent = type("Raiz", (), {"Folders": list(irmas)})()
        self.Items = type("Itens", (), {"Count": itens})()


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


# ---------- diagnóstico da caixa aberta por e-mail (permissão) ----------
class FakeDestinatario:
    def __init__(self, resolvido):
        self.Resolved = resolvido

    def Resolve(self):
        pass


class FakeNSPorEmail:
    """Simula ns.CreateRecipient(...)/GetSharedDefaultFolder(...) para os cenários de diagnóstico."""
    def __init__(self, resolve=True, erro_resolve=None, erro_permissao=None, pasta_entrada=None):
        self.resolve = resolve
        self.erro_resolve = erro_resolve
        self.erro_permissao = erro_permissao
        self.pasta_entrada = pasta_entrada

    def CreateRecipient(self, email):
        if self.erro_resolve:
            raise self.erro_resolve
        return FakeDestinatario(self.resolve)

    def GetSharedDefaultFolder(self, destinatario, tipo):
        if self.erro_permissao:
            raise self.erro_permissao
        return self.pasta_entrada


def test_diagnostico_sem_email_configurado():
    _, _, passos = outlook.diagnosticar_caixa_compartilhada(FakeNSPorEmail(), "")
    assert "não foi informado" in passos[0]


def test_diagnostico_email_nao_resolvido():
    ns = FakeNSPorEmail(resolve=False)
    _, _, passos = outlook.diagnosticar_caixa_compartilhada(ns, "portal@orgao.gov.br")
    assert "não resolveu" in passos[0]


def test_diagnostico_sem_permissao():
    ns = FakeNSPorEmail(erro_permissao=Exception("acesso negado"))
    _, _, passos = outlook.diagnosticar_caixa_compartilhada(ns, "portal@orgao.gov.br")
    assert "sem permissão" in passos[-1] and "acesso negado" in passos[-1]


def test_diagnostico_sem_pasta_de_enviados():
    entrada = FakeFolder("Caixa de Entrada", irmas=[FakeFolder("Rascunhos")], itens=5)
    ns = FakeNSPorEmail(pasta_entrada=entrada)
    achada_entrada, achada_enviados, passos = outlook.diagnosticar_caixa_compartilhada(ns, "x@orgao.gov.br")
    assert achada_entrada is entrada and achada_enviados is None
    assert "Itens Enviados" in passos[-1] and "Rascunhos" in passos[-1]


def test_diagnostico_completo_com_sucesso():
    enviados = FakeFolder("Itens Enviados")
    entrada = FakeFolder("Caixa de Entrada", irmas=[enviados], itens=5)
    ns = FakeNSPorEmail(pasta_entrada=entrada)
    achada_entrada, achada_enviados, passos = outlook.diagnosticar_caixa_compartilhada(ns, "x@orgao.gov.br")
    assert achada_entrada is entrada and achada_enviados is enviados
    assert passos[-1].startswith("Itens Enviados encontrados")
