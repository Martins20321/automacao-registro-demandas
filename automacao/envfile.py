"""Leitura e gravação simples do arquivo .env (usado pela tela de configurações)."""
from pathlib import Path


def ler(caminho):
    """Devolve {CHAVE: valor} das linhas CHAVE=valor (ignora comentários e linhas vazias)."""
    valores = {}
    caminho = Path(caminho)
    if not caminho.exists():
        return valores
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"')
    return valores


def _formatar(valor):
    return f'"{valor}"' if "#" in valor else valor


def salvar(caminho, novos):
    """Atualiza (ou acrescenta) as chaves em `novos`, preservando comentários e as demais linhas."""
    caminho = Path(caminho)
    linhas = caminho.read_text(encoding="utf-8-sig").splitlines() if caminho.exists() else []
    pendentes = dict(novos)
    saida = []
    for linha in linhas:
        chave = linha.split("=", 1)[0].strip() if "=" in linha and not linha.lstrip().startswith("#") else None
        if chave in pendentes:
            saida.append(f"{chave}={_formatar(pendentes.pop(chave))}")
        else:
            saida.append(linha)
    for chave, valor in pendentes.items():
        saida.append(f"{chave}={_formatar(valor)}")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(saida) + "\n", encoding="utf-8")
