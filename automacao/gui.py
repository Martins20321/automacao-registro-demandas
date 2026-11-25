"""Interface gráfica (Tkinter) do Registro de Demandas.

Telas: início (dados do operador) -> progresso -> prévia/edição -> resultado.
O trabalho pesado roda em outra thread para a janela não travar.
"""
import json
import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
import tkinter as tk
from datetime import datetime
from tkcalendar import DateEntry
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import config, destino, envfile, fluxo, ia, previa, progresso
from . import roster as lista
from .previa import fmt
from .util import ler_data

COMPLEXIDADES = ("Baixa", "Normal", "Alta", "Crítico")
ARQUIVO_ULTIMO = config.RAIZ / "ultimo_operador.json"

BG, FG, MUTED, ACCENT, ACCENT_FG = "#f5f6f4", "#1b2420", "#5d6a63", "#1c6b4f", "#ffffff"
WARN_BG, ERR_FG = "#fbf0dc", "#a12a2a"
FONTE = ("Segoe UI", 10)


def _dpi():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Registro de Demandas")
        self.geometry("1150x740")
        self.minsize(1000, 660)
        self.configure(bg=BG)
        self.fila = queue.Queue()
        self.itens, self.resultado, self.selecionado = [], None, None
        self._estilos()
        self._barra_topo()
        self.corpo = ttk.Frame(self)
        self.corpo.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.telas = {"inicio": self._montar_inicio(), "progresso": self._montar_progresso(),
                      "previa": self._montar_previa()}
        self.mostrar("inicio")
        self.after(150, self._poll)
        self.after(400, self._verificar_configuracao)

    # ---------- estrutura ----------
    def _estilos(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=FONTE)
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Muted.TLabel", foreground=MUTED)
        s.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"))
        s.configure("Sub.TLabel", font=("Segoe UI", 11, "bold"))
        s.configure("Aviso.TLabel", foreground=ERR_FG)
        s.configure("TButton", padding=(12, 7))
        s.configure("Accent.TButton", background=ACCENT, foreground=ACCENT_FG, padding=(18, 9),
                    font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[("active", "#165a41"), ("disabled", "#9bb7aa")])
        s.configure("Treeview", rowheight=26, fieldbackground="#ffffff")
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        s.configure("TNotebook", background=BG)
        s.configure("TCheckbutton", background=BG)

    def _barra_topo(self):
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=20, pady=(14, 8))
        ttk.Label(barra, text="Registro de Demandas", style="Titulo.TLabel").pack(side="left")
        ttk.Button(barra, text="Configurações", command=self.abrir_configuracoes).pack(side="right")
        ttk.Button(barra, text="Pasta dos arquivos", command=self.abrir_pasta_saida).pack(side="right", padx=8)
        if config.EMPACOTADO:
            ttk.Button(barra, text="Criar atalho na área de trabalho",
                      command=self.criar_atalho).pack(side="right", padx=8)

    def mostrar(self, nome):
        for tela in self.telas.values():
            tela.pack_forget()
        self.telas[nome].pack(fill="both", expand=True)

    # ---------- tela inicial ----------
    def _montar_inicio(self):
        tela = ttk.Frame(self.corpo)
        ultimo = self._ler_ultimo()
        self.var_email = tk.StringVar(value=ultimo.get("email", ""))
        self.var_nome = tk.StringVar(value=ultimo.get("nome", ""))
        self.var_desde = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.var_csv = tk.StringVar()
        self.var_todas = tk.BooleanVar(value=True)

        ttk.Label(tela, text="Busque as suas demandas concluídas e gere o registro para o SharePoint.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        form = ttk.Frame(tela)
        form.pack(anchor="w")
        linhas = [("Seu e-mail institucional", self.var_email),
                  ("Seu nome completo (com ou sem acento)", self.var_nome)]
        for i, (rotulo, var) in enumerate(linhas):
            ttk.Label(form, text=rotulo).grid(row=i, column=0, sticky="w", pady=6, padx=(0, 16))
            ttk.Entry(form, textvariable=var, width=46).grid(row=i, column=1, sticky="w", pady=6)
        ttk.Label(form, text="Buscar demandas concluídas desde").grid(
            row=2, column=0, sticky="w", pady=6, padx=(0, 16))
        DateEntry(form, textvariable=self.var_desde, date_pattern="dd/mm/yyyy", locale="pt_BR",
                  width=14, firstweekday="sunday", maxdate=datetime.now()).grid(
            row=2, column=1, sticky="w", pady=6)
        ttk.Label(form, text="CSV exportado da lista (opcional, evita duplicados)").grid(
            row=3, column=0, sticky="w", pady=6, padx=(0, 16))
        linha_csv = ttk.Frame(form)
        linha_csv.grid(row=3, column=1, sticky="w", pady=6)
        ttk.Entry(linha_csv, textvariable=self.var_csv, width=36).pack(side="left")
        ttk.Button(linha_csv, text="Procurar…", command=self._procurar_csv).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(form, variable=self.var_todas,
                        text="Verificar também conversas sem a minha categoria (mais completo, mais lento)"
                        ).grid(row=4, column=1, sticky="w", pady=(6, 0))

        ttk.Button(tela, text="Buscar minhas demandas", style="Accent.TButton",
                   command=self.iniciar_busca).pack(anchor="w", pady=(22, 18))
        dica = ttk.Frame(tela)
        dica.pack(anchor="w")
        ttk.Label(dica, text="Antes de começar", style="Sub.TLabel").pack(anchor="w")
        for texto in ("• Abra o Outlook clássico, com a caixa compartilhada visível no painel esquerdo.",
                      "• Para evitar registros duplicados, na lista do SharePoint use Exportar > Exportar para CSV "
                      "e selecione o arquivo acima.",
                      "• Se o Outlook pedir permissão de acesso, clique em permitir."):
            ttk.Label(dica, text=texto, style="Muted.TLabel").pack(anchor="w", pady=2)
        return tela

    def _procurar_csv(self):
        caminho = filedialog.askopenfilename(title="Selecione o CSV exportado da lista",
                                             filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")])
        if caminho:
            self.var_csv.set(caminho)

    def _ler_ultimo(self):
        try:
            return json.loads(ARQUIVO_ULTIMO.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _salvar_ultimo(self):
        try:
            ARQUIVO_ULTIMO.write_text(json.dumps(
                {"email": self.var_email.get().strip(), "nome": self.var_nome.get().strip()},
                ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ---------- tela de progresso ----------
    def _montar_progresso(self):
        tela = ttk.Frame(self.corpo)
        self.lbl_status = ttk.Label(tela, text="Trabalhando…", style="Sub.TLabel")
        self.lbl_status.pack(anchor="w", pady=(4, 8))
        self.barra = ttk.Progressbar(tela, mode="indeterminate")
        self.barra.pack(fill="x", pady=(0, 12))
        ttk.Label(tela, text="Isso pode levar alguns minutos. Não feche a janela do Outlook.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        quadro = ttk.Frame(tela)
        quadro.pack(fill="both", expand=True)
        self.log = tk.Text(quadro, height=18, state="disabled", bg="#ffffff", relief="solid", bd=1,
                           font=("Consolas", 10))
        rolagem = ttk.Scrollbar(quadro, command=self.log.yview)
        self.log.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        return tela

    def _log(self, texto):
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.lbl_status.configure(text=texto.strip()[:110])

    # ---------- tela de prévia ----------
    def _montar_previa(self):
        tela = ttk.Frame(self.corpo)
        self.lbl_resumo = ttk.Label(tela, text="", style="Sub.TLabel")
        self.lbl_resumo.pack(anchor="w", pady=(0, 8))
        # O rodapé é empacotado ANTES das abas para ficar sempre visível, mesmo em janelas baixas.
        rodape = ttk.Frame(tela)
        rodape.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(rodape, text="← Nova busca", command=lambda: self.mostrar("inicio")).pack(side="left")
        self.btn_confirmar = ttk.Button(rodape, text="Confirmar e copiar para o SharePoint",
                                        style="Accent.TButton", command=self.confirmar)
        self.btn_confirmar.pack(side="right")

        self.abas = ttk.Notebook(tela)
        self.abas.pack(fill="both", expand=True)

        aba1 = ttk.Frame(self.abas)
        self.abas.add(aba1, text="Para registrar")
        colunas = (("inc", "Incluir", 60), ("st", "Situação", 80), ("problema", "Problema", 330),
                   ("cliente", "Cliente", 190), ("sistema", "Sistema", 130), ("cx", "Complexidade", 125),
                   ("conc", "Conclusão", 130))
        quadro = ttk.Frame(aba1)
        quadro.pack(fill="x")
        self.arvore = ttk.Treeview(quadro, columns=[c[0] for c in colunas], show="headings", height=6,
                                   selectmode="browse")
        for chave, titulo, largura in colunas:
            self.arvore.heading(chave, text=titulo)
            self.arvore.column(chave, width=largura, anchor="w")
        self.arvore.tag_configure("revisar", background=WARN_BG)
        self.arvore.tag_configure("fora", foreground="#9aa5a0")
        rol = ttk.Scrollbar(quadro, command=self.arvore.yview)
        self.arvore.configure(yscrollcommand=rol.set)
        rol.pack(side="right", fill="y")
        self.arvore.pack(side="left", fill="x", expand=True)
        self.arvore.bind("<<TreeviewSelect>>", self._ao_selecionar)
        self._montar_detalhe(aba1)

        self.aba_ignoradas = self._montar_tabela(("tipo", "Tipo", 120), ("conc", "Conclusão", 130),
                                                 ("assunto", "Assunto", 330), ("motivo", "Motivo", 450))
        self.abas.add(self.aba_ignoradas[0], text="Ignoradas")
        self.aba_falhas = self._montar_tabela(("conc", "Conclusão", 140), ("erro", "Erro", 800))
        self.abas.add(self.aba_falhas[0], text="Falhas")

        return tela

    def _montar_tabela(self, *colunas):
        quadro = ttk.Frame(self.abas)
        arvore = ttk.Treeview(quadro, columns=[c[0] for c in colunas], show="headings")
        for chave, titulo, largura in colunas:
            arvore.heading(chave, text=titulo)
            arvore.column(chave, width=largura, anchor="w")
        rol = ttk.Scrollbar(quadro, command=arvore.yview)
        arvore.configure(yscrollcommand=rol.set)
        rol.pack(side="right", fill="y")
        arvore.pack(side="left", fill="both", expand=True)
        return quadro, arvore

    def _montar_detalhe(self, pai):
        det = ttk.Frame(pai)
        det.pack(fill="both", expand=True, pady=(10, 0))
        self.v = {k: tk.StringVar() for k in ("problema", "complexidade", "sistema", "atribuido_a",
                                                 "data_abertura", "data_conclusao", "cliente")}
        ttk.Label(det, text="Problema").grid(row=0, column=0, sticky="w")
        ttk.Entry(det, textvariable=self.v["problema"]).grid(row=0, column=1, columnspan=5, sticky="ew", pady=3)
        ttk.Label(det, text="Descrição").grid(row=1, column=0, sticky="nw")
        self.txt_desc = tk.Text(det, height=3, wrap="word", relief="solid", bd=1, font=FONTE)
        self.txt_desc.grid(row=1, column=1, columnspan=5, sticky="ew", pady=3)
        campos = [("Complexidade", "complexidade"), ("Sistema", "sistema"), ("Atribuído a", "atribuido_a"),
                  ("Data de abertura", "data_abertura"), ("Data de conclusão", "data_conclusao"),
                  ("Cliente", "cliente")]
        for i, (rotulo, chave) in enumerate(campos):
            r, c = 2 + i // 3, (i % 3) * 2
            ttk.Label(det, text=rotulo).grid(row=r, column=c, sticky="w", padx=(0, 6), pady=3)
            if chave == "complexidade":
                w = ttk.Combobox(det, textvariable=self.v[chave], values=COMPLEXIDADES, state="readonly", width=16)
            else:
                w = ttk.Entry(det, textvariable=self.v[chave], width=24)
            w.grid(row=r, column=c + 1, sticky="ew", padx=(0, 14), pady=3)
        self.lbl_avisos = ttk.Label(det, text="", style="Aviso.TLabel", wraplength=1000, justify="left")
        self.lbl_avisos.grid(row=4, column=0, columnspan=6, sticky="w", pady=(6, 0))
        botoes = ttk.Frame(det)
        botoes.grid(row=5, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(botoes, text="Aplicar alterações", command=self.aplicar_alteracoes).pack(side="left")
        self.btn_incluir = ttk.Button(botoes, text="Não incluir esta demanda", command=self.alternar_inclusao)
        self.btn_incluir.pack(side="left", padx=8)
        for col in (1, 3, 5):
            det.columnconfigure(col, weight=1)

    # ---------- ações da prévia ----------
    def _preencher_previa(self):
        r = self.resultado
        self.itens = r.registros
        for item in self.itens:
            item["incluir"] = not item["duplicada"]
        n = len(self.itens)
        extra = ""
        if r.existentes is not None:
            extra = f" | {sum(1 for i in self.itens if i['duplicada'])} já existe(m) na lista"
        else:
            extra = " | sem checagem de duplicidade (nenhum CSV informado)"
        self.lbl_resumo.configure(
            text=f"{n} demanda(s) para registrar | {len(r.ignoradas)} ignorada(s) | {len(r.falhas)} falha(s){extra}")
        self.abas.tab(0, text=f"Para registrar ({n})")
        self.abas.tab(1, text=f"Ignoradas ({len(r.ignoradas)})")
        self.abas.tab(2, text=f"Falhas ({len(r.falhas)})")
        for arv in (self.aba_ignoradas[1], self.aba_falhas[1]):
            arv.delete(*arv.get_children())
        for i in r.ignoradas:
            self.aba_ignoradas[1].insert("", "end", values=(i["tipo"], fmt(i["conclusao"]), i["assunto"], i["motivo"]))
        for f in r.falhas:
            self.aba_falhas[1].insert("", "end", values=(fmt(f["conclusao"]), f["erro"]))
        self._atualizar_arvore()
        if self.itens:
            self.arvore.selection_set("0")
        else:
            self._limpar_detalhe()
        self.btn_confirmar.configure(state="normal" if self.itens else "disabled")

    def _linha(self, item):
        d = item["demanda"]
        situacao = "JÁ EXISTE" if item["duplicada"] else ("REVISAR" if item["avisos"] else "OK")
        return ("✔" if item["incluir"] else "—", situacao, d.problema, d.cliente, d.sistema,
                d.complexidade, fmt(d.data_conclusao))

    def _tags(self, item):
        if not item["incluir"]:
            return ("fora",)
        return ("revisar",) if item["avisos"] else ()

    def _atualizar_arvore(self):
        self.arvore.delete(*self.arvore.get_children())
        for i, item in enumerate(self.itens):
            self.arvore.insert("", "end", iid=str(i), values=self._linha(item), tags=self._tags(item))

    def _atualizar_linha(self, indice):
        item = self.itens[indice]
        self.arvore.item(str(indice), values=self._linha(item), tags=self._tags(item))

    def _limpar_detalhe(self):
        for var in self.v.values():
            var.set("")
        self.txt_desc.delete("1.0", "end")
        self.lbl_avisos.configure(text="")
        self.selecionado = None

    def _ao_selecionar(self, _evento=None):
        sel = self.arvore.selection()
        if not sel:
            return
        self.selecionado = int(sel[0])
        item = self.itens[self.selecionado]
        d = item["demanda"]
        for chave in ("problema", "complexidade", "sistema", "atribuido_a", "cliente"):
            self.v[chave].set(getattr(d, chave))
        self.v["data_abertura"].set(fmt(d.data_abertura))
        self.v["data_conclusao"].set(fmt(d.data_conclusao))
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", d.descricao)
        avisos = list(item["avisos"])
        self.lbl_avisos.configure(text=("Atenção: " + " | ".join(avisos)) if avisos else "")
        self.btn_incluir.configure(text="Não incluir esta demanda" if item["incluir"] else "Incluir esta demanda")

    def aplicar_alteracoes(self):
        if self.selecionado is None:
            return
        item = self.itens[self.selecionado]
        try:
            novos = {k: self.v[k].get().strip() for k in ("problema", "sistema", "atribuido_a", "cliente")}
            novos["descricao"] = " ".join(self.txt_desc.get("1.0", "end").split())
            if "" in novos.values():
                raise ValueError("Nenhum campo pode ficar vazio.")
            novos["complexidade"] = self.v["complexidade"].get()
            if novos["complexidade"] not in COMPLEXIDADES:
                raise ValueError("Escolha a complexidade: Baixa, Normal, Alta ou Crítico.")
            for chave in ("data_abertura", "data_conclusao"):
                novos[chave] = datetime.strptime(self.v[chave].get().strip(), "%d/%m/%Y %H:%M")
        except ValueError as erro:
            texto = str(erro)
            if "does not match" in texto or "unconverted" in texto:
                texto = "Datas devem estar no formato dd/mm/aaaa hh:mm (por exemplo, 05/11/2026 09:30)."
            messagebox.showerror("Valor inválido", texto, parent=self)
            return
        item["demanda"] = item["demanda"].model_copy(update=novos)
        d = item["demanda"]
        if d.data_conclusao >= d.data_abertura:
            item["avisos"] = [a for a in item["avisos"] if "conclusão anterior" not in a]
        self._atualizar_linha(self.selecionado)
        self._ao_selecionar()
        messagebox.showinfo("Alterado", "Alterações aplicadas.", parent=self)

    def alternar_inclusao(self):
        if self.selecionado is None:
            return
        item = self.itens[self.selecionado]
        item["incluir"] = not item["incluir"]
        self._atualizar_linha(self.selecionado)
        self._ao_selecionar()

    def confirmar(self):
        escolhidos = [i for i in self.itens if i["incluir"]]
        if not escolhidos:
            messagebox.showwarning("Nada a enviar", "Nenhuma demanda está marcada para inclusão.", parent=self)
            return
        pergunta = f"Copiar {len(escolhidos)} demanda(s) para a área de transferência?"
        com_aviso = sum(1 for i in escolhidos if i["avisos"])
        if com_aviso:
            pergunta += f"\n\n{com_aviso} delas ainda têm aviso (REVISAR)."
        if not messagebox.askyesno("Confirmar", pergunta, parent=self):
            return
        self._mostrar_resultado(destino.entregar(escolhidos))

    def _mostrar_resultado(self, mensagem):
        janela = tk.Toplevel(self)
        janela.title("Pronto para colar no SharePoint")
        janela.geometry("760x470")
        janela.configure(bg=BG)
        janela.transient(self)
        ttk.Label(janela, text="Linhas copiadas", style="Titulo.TLabel").pack(anchor="w", padx=20, pady=(16, 6))
        texto = tk.Text(janela, wrap="word", relief="flat", bg=BG, font=FONTE, height=14)
        texto.insert("1.0", mensagem)
        texto.configure(state="disabled")
        texto.pack(fill="both", expand=True, padx=20)
        botoes = ttk.Frame(janela)
        botoes.pack(fill="x", padx=20, pady=14)
        if os.getenv("LISTA_URL", "").strip():
            ttk.Button(botoes, text="Abrir a lista", command=destino.abrir_lista).pack(side="left")
        ttk.Button(botoes, text="Abrir pasta dos arquivos", command=self.abrir_pasta_saida).pack(side="left", padx=8)
        ttk.Button(botoes, text="Fechar", command=janela.destroy).pack(side="right")

    # ---------- busca (thread) ----------
    def iniciar_busca(self):
        if config.configuracao_faltando():
            messagebox.showinfo("Configuração necessária",
                                "Antes de buscar, preencha as configurações do seu órgão.", parent=self)
            self.abrir_configuracoes()
            return
        try:
            desde = ler_data(self.var_desde.get())
            roster = lista.carregar()
            operador = lista.identificar_operador(self.var_nome.get(), self.var_email.get(), roster)
        except ValueError as erro:
            messagebox.showerror("Confira os dados", str(erro), parent=self)
            return
        except OSError as erro:
            messagebox.showerror("Lista de estagiários", f"Não consegui ler a lista de estagiários:\n{erro}",
                                 parent=self)
            return
        caminho_csv = self.var_csv.get().strip().strip('"')
        if caminho_csv and not Path(caminho_csv).is_file():
            messagebox.showerror("CSV da lista", "O arquivo CSV informado não foi encontrado.", parent=self)
            return
        if not ia.chave_configurada():
            chave = simpledialog.askstring(
                "Chave da IA", "Informe a chave da API do Groq (console.groq.com).\n"
                "Ela fica guardada só neste computador.", show="*", parent=self)
            if not chave or not chave.strip():
                return
            ia.salvar_chave(chave)
        try:
            provedor = ia.ProvedorGroq()
        except RuntimeError as erro:
            messagebox.showerror("IA", str(erro), parent=self)
            return
        self._salvar_ultimo()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.lbl_status.configure(text="Trabalhando…")
        self.barra.start(12)
        self.mostrar("progresso")
        progresso.definir(lambda msg: self.fila.put(("log", msg)))
        threading.Thread(target=self._trabalho, daemon=True, args=(
            operador, desde, roster, provedor, caminho_csv, not self.var_todas.get())).start()

    def _trabalho(self, operador, desde, roster, provedor, csv, so_categoria):
        try:
            resultado = fluxo.processar(operador, desde, roster, provedor, csv,
                                        verificar_todas=not so_categoria)
            self.fila.put(("ok", resultado))
        except Exception as erro:               # mostrado ao operador na thread principal
            self.fila.put(("erro", erro))

    def _poll(self):
        try:
            while True:
                tipo, valor = self.fila.get_nowait()
                if tipo == "log":
                    self._log(valor)
                elif tipo == "ok":
                    self.barra.stop()
                    self.resultado = valor
                    self._preencher_previa()
                    self.mostrar("previa")
                elif tipo == "erro":
                    self.barra.stop()
                    self.mostrar("inicio")
                    messagebox.showerror("Não foi possível concluir", self._explicar(valor), parent=self)
        except queue.Empty:
            pass
        self.after(150, self._poll)

    @staticmethod
    def _explicar(erro):
        texto = str(erro) or repr(erro)
        if "Armazenamento" in texto:
            pass  # a própria mensagem já lista as caixas encontradas e o que fazer
        elif "Dispatch" in texto or "com_error" in texto or "Outlook" in texto:
            texto += "\n\nVerifique se o Outlook CLÁSSICO está aberto (o novo Outlook não funciona)."
        return texto

    # ---------- configurações ----------
    def _verificar_configuracao(self):
        if config.configuracao_faltando():
            messagebox.showinfo("Primeiro uso", "Vamos configurar o programa com os dados do seu órgão.",
                                parent=self)
            self.abrir_configuracoes()

    def abrir_configuracoes(self):
        era_primeiro_uso = bool(config.configuracao_faltando())
        atuais = envfile.ler(config.ARQUIVO_ENV)
        janela = tk.Toplevel(self)
        janela.title("Configurações")
        janela.configure(bg=BG)
        janela.transient(self)
        janela.grab_set()
        campos = [
            ("OUTLOOK_ARMAZENAMENTO", "Nome da caixa compartilhada (como aparece no painel do Outlook)", False),
            ("OUTLOOK_EMAIL", "E-mail da caixa (só se ela NÃO aparecer como conta própria no Outlook)", False),
            ("DOMINIO_INTERNO", "Domínio dos e-mails internos (ex.: @orgao.gov.br)", False),
            ("CLIENTE_CONSULTAS_PUBLICAS", "Cliente de demandas externas de Consultas Públicas", False),
            ("CLIENTE_PORTAL_EXTERNO", "Cliente de demandas externas do portal", False),
            ("LISTA_URL", "Endereço da lista do SharePoint (opcional)", False),
            ("CATEGORIAS_IGNORADAS", "Categorias do Outlook a ignorar, separadas por vírgula (opcional)", False),
            ("GROQ_API_KEY", "Chave da API do Groq (deixe em branco para manter a atual)", True),
        ]
        vars_ = {}
        quadro = ttk.Frame(janela)
        quadro.pack(padx=20, pady=16)
        for i, (chave, rotulo, secreto) in enumerate(campos):
            ttk.Label(quadro, text=rotulo).grid(row=i, column=0, sticky="w", pady=5, padx=(0, 14))
            var = tk.StringVar(value="" if secreto else atuais.get(chave, ""))
            ttk.Entry(quadro, textvariable=var, width=52, show="*" if secreto else "").grid(
                row=i, column=1, pady=5)
            vars_[chave] = var

        def salvar():
            valores = {k: v.get().strip() for k, v in vars_.items()}
            ausentes = [k for k in config.OBRIGATORIAS if not valores.get(k)]
            if ausentes:
                messagebox.showerror("Campos obrigatórios", "Preencha: " + ", ".join(ausentes), parent=janela)
                return
            if not valores["GROQ_API_KEY"]:
                valores.pop("GROQ_API_KEY")
            if valores["DOMINIO_INTERNO"] and not valores["DOMINIO_INTERNO"].startswith("@"):
                valores["DOMINIO_INTERNO"] = "@" + valores["DOMINIO_INTERNO"]
            envfile.salvar(config.ARQUIVO_ENV, valores)
            janela.destroy()
            if era_primeiro_uso and config.EMPACOTADO and messagebox.askyesno(
                    "Atalho", "Criar um atalho do programa na Área de Trabalho?", parent=self):
                self.criar_atalho()
            self._reiniciar()

        linha2 = ttk.Frame(janela)
        linha2.pack(fill="x", padx=20, pady=(0, 6))
        ttk.Label(linha2, text=f"Lista de estagiários: {config.ROSTER}", style="Muted.TLabel").pack(anchor="w")

        botoes = ttk.Frame(janela)
        botoes.pack(fill="x", padx=20, pady=(0, 16))
        ttk.Button(botoes, text="Editar lista de estagiários",
                   command=lambda: os.startfile(config.garantir_roster())).pack(side="left")
        ttk.Button(botoes, text="Importar lista (.csv)…",
                   command=self._importar_roster).pack(side="left", padx=8)
        ttk.Button(botoes, text="Testar instalação", command=self._testar_instalacao).pack(side="left", padx=8)
        ttk.Button(botoes, text="Cancelar", command=janela.destroy).pack(side="right")
        ttk.Button(botoes, text="Salvar", style="Accent.TButton", command=salvar).pack(side="right", padx=8)

    def _importar_roster(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o CSV com a lista de estagiários (colunas: nome,email)",
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            destino = config.importar_roster(caminho)
        except Exception as erro:
            messagebox.showerror("Não foi possível importar", str(erro), parent=self)
            return
        messagebox.showinfo("Lista importada", f"Lista de estagiários atualizada:\n{destino}", parent=self)

    def _testar_instalacao(self):
        from . import autoteste
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            relatorio, tudo_ok = autoteste.executar()
        finally:
            self.config(cursor="")
        mostrar = messagebox.showinfo if tudo_ok else messagebox.showwarning
        mostrar("Teste da instalação", relatorio, parent=self)

    def _reiniciar(self):
        messagebox.showinfo("Configurações salvas", "O programa será reaberto para aplicar as configurações.",
                            parent=self)
        try:
            comando = [sys.executable] if config.EMPACOTADO else [sys.executable, *sys.argv]
            subprocess.Popen(comando)
        except Exception:
            messagebox.showinfo("Reabrir", "Feche e abra o programa novamente.", parent=self)
            return
        self.destroy()

    def abrir_pasta_saida(self):
        config.SAIDA.mkdir(parents=True, exist_ok=True)
        os.startfile(config.SAIDA)

    def criar_atalho(self):
        """Cria um atalho do programa na Área de Trabalho (facilita achar o .exe depois)."""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            # A Área de Trabalho pode estar redirecionada (ex.: OneDrive): pergunta ao Windows o caminho real.
            area_trabalho = shell.SpecialFolders("Desktop")
            destino = str(Path(area_trabalho) / "Registro de Demandas.lnk")
            atalho = shell.CreateShortcut(destino)
            atalho.TargetPath = sys.executable
            atalho.WorkingDirectory = str(Path(sys.executable).resolve().parent)
            atalho.IconLocation = sys.executable
            atalho.Description = "Registro de Demandas (Outlook → SharePoint)"
            atalho.Save()
            messagebox.showinfo("Atalho criado", "Atalho criado na Área de Trabalho.", parent=self)
        except Exception as erro:
            messagebox.showerror("Não foi possível criar o atalho", str(erro), parent=self)

    # ---------- erros inesperados ----------
    def report_callback_exception(self, tipo, valor, tb):
        detalhe = "".join(traceback.format_exception(tipo, valor, tb))
        try:
            config.SAIDA.mkdir(parents=True, exist_ok=True)
            (config.SAIDA / "erro.log").write_text(detalhe, encoding="utf-8")
        except Exception:
            pass
        messagebox.showerror("Erro inesperado", f"{valor}\n\nO detalhe foi salvo em saida\\erro.log.", parent=self)


def iniciar():
    _dpi()
    App().mainloop()
