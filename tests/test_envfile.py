from automacao import envfile


def test_salvar_preserva_comentarios_e_atualiza_chaves(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentário\nA=1\nB=velho\n", encoding="utf-8")
    envfile.salvar(env, {"B": "novo valor com espaço", "C": "x#y"})
    texto = env.read_text(encoding="utf-8")
    assert texto.startswith("# comentário\nA=1\n")
    valores = envfile.ler(env)
    assert valores == {"A": "1", "B": "novo valor com espaço", "C": "x#y"}


def test_ler_arquivo_inexistente_devolve_vazio(tmp_path):
    assert envfile.ler(tmp_path / "nao_existe") == {}
