"""Funções pequenas e puras."""
import re
import unicodedata


def norm(texto):
    """Minúsculas, sem acento e sem espaços repetidos (para comparar nomes)."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def ler_data(texto):
    """Aceita dd/mm/aaaa ou aaaa-mm-dd."""
    from datetime import datetime
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), formato)
        except ValueError:
            pass
    raise ValueError(f"Data inválida: '{texto}'. Use dd/mm/aaaa.")


def local(dt):
    """pywin32 devolve o horário local marcado como UTC: só remove a marca."""
    return dt.replace(tzinfo=None)
