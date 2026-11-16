from automacao.anonimizar import anonimizar, html_para_texto


def test_remove_email_telefone_cpf_e_link():
    t = anonimizar("Escreva para joao@x.com.br, tel (61) 99876-5432, CPF 123.456.789-09, veja https://www.gov.br/mme/pt-br/a?id=1")
    assert "joao@x.com.br" not in t and "99876" not in t and "123.456" not in t
    assert "[LINK:www.gov.br]" in t and "?id=1" not in t


def test_saudacao_e_nomes_conhecidos():
    t = anonimizar("Prezado Claudir Afonso, o Fabio Skaf pediu a alteração.", ["Fabio Skaf Nacfur"])
    assert "Claudir" not in t and "Fabio" not in t and "Skaf" not in t
    assert "alteração" in t


def test_nomes_de_terceiros_sao_mascarados_e_restauraveis():
    from automacao.anonimizar import Mascara
    m = Mascara()
    t = anonimizar("Incluir Gustavo Magalhães Pinto Assis na página da Consulta Pública. Currículo de DEVID MEISTER.", (), m)
    assert "Gustavo" not in t and "MEISTER" not in t
    assert "Consulta Pública" in t          # termo institucional continua visível
    assert "Gustavo Magalhães Pinto Assis" in m.restaurar(t)


def test_html_corta_historico_e_assinatura():
    html = ("<p>Prezado X, bom dia!</p><p>Informo que a página foi atualizada.</p>"
            "<p>Respeitosamente,</p><p>Nome Estagiario</p>"
            '<div id="divRplyFwdMsg">De: alguem</div><p>texto antigo</p>')
    t = html_para_texto(html)
    assert "página foi atualizada" in t
    assert "Respeitosamente" not in t and "texto antigo" not in t
