"""Programa com janelas (interface gráfica). Para a versão em terminal, veja buscar_demandas.py."""
import sys

if __name__ == "__main__":
    if "--autoteste" in sys.argv:      # verificação da instalação, sem abrir janela
        from automacao import autoteste, config
        relatorio, _ = autoteste.executar()
        config.SAIDA.mkdir(parents=True, exist_ok=True)
        (config.SAIDA / "autoteste.txt").write_text(relatorio, encoding="utf-8")
    else:
        from automacao.gui import iniciar
        iniciar()
