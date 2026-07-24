"""Interface desktop Tkinter/ttk (Fase 9).

Ver docs/plano_conversor_dro_5050_simples.md secao 5. A interface so chama
o servico de conversao (src.conversion.processar); nenhuma regra
regulatoria vive nesta camada.

Layout espelhado do projeto anterior (src/gui/app.py), com uma diferenca
deliberada: o redimensionamento da janela fica desabilitado.
"""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.conversion import STATUS_FALHA_TECNICA as RESULTADO_FALHA_TECNICA
from src.conversion import processar

TITULO_JANELA = "Smart Reporting"

# Mesmo esquema de resolucao de caminho usado em src/xml_writer.py: em
# --onefile, os dados ficam em sys._MEIPASS; fora do bundle, __file__ aponta
# para a arvore de codigo-fonte original.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE_DIR = Path(__file__).resolve().parent.parent

ICONE_JANELA = _BASE_DIR / "assets" / "testeIco.ico"
TITULO_CABECALHO = "Smart Reporting - CADOC 5050"

STATUS_AGUARDANDO = "Aguardando"
STATUS_PROCESSANDO = "Processando..."
STATUS_CONCLUIDO = "Concluído"
STATUS_FALHA_TECNICA = "Falha técnica"

POLL_INTERVAL_MS = 150
PATH_ENTRY_WIDTH = 62
SELECT_BUTTON_WIDTH = 16
ACTION_BUTTON_WIDTH = 38
LARGURA_JANELA = 720
ALTURA_JANELA = 430


def pasta_saida_padrao() -> Path:
    """Pasta de saída sugerida ao abrir a interface."""

    return Path.home() / "Downloads" / "Conversor_DRO_5050"


class Aplicacao(ttk.Frame):
    def __init__(self, raiz: tk.Tk) -> None:
        super().__init__(raiz, padding=14)
        self.raiz = raiz

        self.caminho_planilha = tk.StringVar()
        self.pasta_saida = tk.StringVar(value=str(pasta_saida_padrao()))
        self.status = tk.StringVar(value=STATUS_AGUARDANDO)

        self._fila: queue.Queue = queue.Queue()
        self._processando = False
        self._caminho_xml: Path | None = None
        self._caminho_relatorio: Path | None = None

        self._configurar_janela()
        self._configurar_estilos()
        self._montar_layout()
        self._atualizar_botoes()

        self.raiz.after_idle(self._centralizar_janela)
        self.raiz.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.raiz.after(POLL_INTERVAL_MS, self._verificar_fila)

    def _configurar_janela(self) -> None:
        self.raiz.title(TITULO_JANELA)
        self.raiz.geometry(f"{LARGURA_JANELA}x{ALTURA_JANELA}")
        self.raiz.resizable(False, False)
        self.raiz.columnconfigure(0, weight=1)
        self.raiz.rowconfigure(0, weight=1)

        self.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)

    def _centralizar_janela(self) -> None:
        self.raiz.update_idletasks()
        largura_tela = self.raiz.winfo_screenwidth()
        altura_tela = self.raiz.winfo_screenheight()
        x = max((largura_tela - LARGURA_JANELA) // 2, 0)
        y = max((altura_tela - ALTURA_JANELA) // 2, 0)
        self.raiz.geometry(f"{LARGURA_JANELA}x{ALTURA_JANELA}+{x}+{y}")

    def _configurar_estilos(self) -> None:
        estilo = ttk.Style(self.raiz)
        if "vista" in estilo.theme_names():
            estilo.theme_use("vista")
        elif "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        estilo.configure("Titulo.TLabel", font=("Segoe UI", 17, "bold"))
        estilo.configure(
            "Primario.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7)
        )
        estilo.configure(
            "StatusAguardando.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#4A5568",
        )
        estilo.configure(
            "StatusProcessando.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#1D4ED8",
        )
        estilo.configure(
            "StatusConcluido.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#137333",
        )
        estilo.configure(
            "StatusFalha.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#B91C1C",
        )

    def _montar_layout(self) -> None:
        ttk.Label(self, text=TITULO_CABECALHO, style="Titulo.TLabel").grid(
            row=0, column=0, pady=(0, 18)
        )

        quadro = ttk.Frame(self, padding=12)
        quadro.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        ttk.Label(quadro, text="Planilha Excel:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.campo_planilha = ttk.Entry(
            quadro, textvariable=self.caminho_planilha, width=PATH_ENTRY_WIDTH
        )
        self.campo_planilha.grid(row=0, column=1, pady=4)
        self.botao_selecionar_planilha = ttk.Button(
            quadro,
            text="Selecionar",
            command=self._selecionar_planilha,
            width=SELECT_BUTTON_WIDTH,
        )
        self.botao_selecionar_planilha.grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(quadro, text="Pasta de saída:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.campo_pasta_saida = ttk.Entry(
            quadro, textvariable=self.pasta_saida, width=PATH_ENTRY_WIDTH
        )
        self.campo_pasta_saida.grid(row=1, column=1, pady=4)
        self.botao_selecionar_pasta = ttk.Button(
            quadro,
            text="Selecionar",
            command=self._selecionar_pasta_saida,
            width=SELECT_BUTTON_WIDTH,
        )
        self.botao_selecionar_pasta.grid(row=1, column=2, padx=(8, 0), pady=4)
        ttk.Button(
            quadro, text="Abrir pasta", command=self._abrir_pasta_saida
        ).grid(row=1, column=3, padx=(8, 0), pady=4)

        quadro_status = ttk.Frame(quadro)
        quadro_status.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(14, 8))
        quadro_status.columnconfigure(0, weight=1)
        quadro_status.columnconfigure(3, weight=1)
        ttk.Label(quadro_status, text="Status:", font=("Segoe UI", 10)).grid(
            row=0, column=1, padx=(0, 8)
        )
        self.rotulo_status = ttk.Label(
            quadro_status,
            textvariable=self.status,
            style="StatusAguardando.TLabel",
        )
        self.rotulo_status.grid(row=0, column=2)

        quadro_acoes = ttk.Frame(quadro)
        quadro_acoes.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        quadro_acoes.columnconfigure(0, weight=1)
        quadro_acoes.columnconfigure(2, weight=1)

        self.botao_converter = ttk.Button(
            quadro_acoes,
            text="Converter, validar e gerar XML/XLSX",
            command=self._iniciar_conversao,
            style="Primario.TButton",
            width=ACTION_BUTTON_WIDTH,
        )
        self.botao_converter.grid(row=0, column=1, pady=(0, 8))

        self.botao_abrir_xml = ttk.Button(
            quadro_acoes,
            text="Abrir XML",
            command=self._abrir_xml,
            width=ACTION_BUTTON_WIDTH,
        )
        self.botao_abrir_xml.grid(row=1, column=1, pady=(0, 8))

        self.botao_abrir_relatorio = ttk.Button(
            quadro_acoes,
            text="Abrir relatório XLSX",
            command=self._abrir_relatorio,
            width=ACTION_BUTTON_WIDTH,
        )
        self.botao_abrir_relatorio.grid(row=2, column=1)

    def _atualizar_botoes(self) -> None:
        self.botao_abrir_xml.state(
            ["!disabled"]
            if self._caminho_xml and self._caminho_xml.exists()
            else ["disabled"]
        )
        self.botao_abrir_relatorio.state(
            ["!disabled"]
            if self._caminho_relatorio and self._caminho_relatorio.exists()
            else ["disabled"]
        )

    def _definir_ocupado(self, ocupado: bool) -> None:
        estado = ["disabled"] if ocupado else ["!disabled"]
        for widget in (
            self.botao_selecionar_planilha,
            self.botao_selecionar_pasta,
            self.botao_converter,
            self.campo_planilha,
            self.campo_pasta_saida,
        ):
            widget.state(estado)

    def _selecionar_planilha(self) -> None:
        caminho = filedialog.askopenfilename(
            parent=self.raiz,
            title="Selecione a planilha DRO 5050",
            filetypes=(
                ("Planilhas Excel", "*.xlsx"),
                ("Todos os arquivos", "*.*"),
            ),
        )
        if caminho:
            self.caminho_planilha.set(caminho)
            self._limpar_resultado()

    def _selecionar_pasta_saida(self) -> None:
        pasta = filedialog.askdirectory(
            parent=self.raiz, title="Selecione a pasta principal de saída"
        )
        if pasta:
            self.pasta_saida.set(pasta)

    def _abrir_pasta_saida(self) -> None:
        pasta = self.pasta_saida.get().strip()
        if not pasta:
            return
        caminho = Path(pasta).expanduser().resolve()
        caminho.mkdir(parents=True, exist_ok=True)
        self._abrir_caminho(caminho)

    def _abrir_xml(self) -> None:
        if self._caminho_xml is not None:
            self._abrir_caminho(self._caminho_xml)

    def _abrir_relatorio(self) -> None:
        if self._caminho_relatorio is not None:
            self._abrir_caminho(self._caminho_relatorio)

    def _abrir_caminho(self, caminho: Path) -> None:
        import os
        import subprocess
        import sys

        try:
            if os.name == "nt":
                os.startfile(str(caminho))  # type: ignore[attr-defined]
            else:
                comando = (
                    ["open", str(caminho)]
                    if sys.platform == "darwin"
                    else ["xdg-open", str(caminho)]
                )
                subprocess.Popen(
                    comando,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as erro:
            messagebox.showerror("Abrir arquivo", str(erro), parent=self.raiz)

    def _limpar_resultado(self) -> None:
        self._caminho_xml = None
        self._caminho_relatorio = None
        self._atualizar_botoes()
        self._definir_status(STATUS_AGUARDANDO, "StatusAguardando.TLabel")

    def _definir_status(self, texto: str, estilo: str) -> None:
        self.status.set(texto)
        self.rotulo_status.configure(style=estilo)

    def _iniciar_conversao(self) -> None:
        if self._processando:
            return

        caminho_planilha = self.caminho_planilha.get().strip()
        if not caminho_planilha:
            messagebox.showerror(
                "Planilha Excel",
                "Selecione uma planilha .xlsx.",
                parent=self.raiz,
            )
            return
        if Path(caminho_planilha).suffix.lower() != ".xlsx":
            messagebox.showerror(
                "Planilha Excel",
                "O arquivo precisa possuir a extensão .xlsx.",
                parent=self.raiz,
            )
            return

        pasta_saida = self.pasta_saida.get().strip()
        if not pasta_saida:
            messagebox.showerror(
                "Pasta de saída",
                "Selecione a pasta principal de saída.",
                parent=self.raiz,
            )
            return

        self._limpar_resultado()
        self._processando = True
        self._definir_ocupado(True)
        self._definir_status(STATUS_PROCESSANDO, "StatusProcessando.TLabel")

        thread = threading.Thread(
            target=self._executar_em_thread,
            args=(Path(caminho_planilha), Path(pasta_saida)),
            daemon=True,
        )
        thread.start()

    def _executar_em_thread(self, caminho_planilha: Path, pasta_saida: Path) -> None:
        try:
            resultado = processar(caminho_planilha, pasta_saida)
        except Exception as erro:  # falha tecnica inesperada
            self._fila.put(("erro", str(erro)))
            return
        self._fila.put(("ok", resultado))

    def _verificar_fila(self) -> None:
        try:
            tipo, valor = self._fila.get_nowait()
        except queue.Empty:
            if self.raiz.winfo_exists():
                self.raiz.after(POLL_INTERVAL_MS, self._verificar_fila)
            return

        self._processando = False
        self._definir_ocupado(False)

        if tipo == "erro":
            self._definir_status(STATUS_FALHA_TECNICA, "StatusFalha.TLabel")
            messagebox.showerror("Falha técnica", valor, parent=self.raiz)
        else:
            resultado = valor
            self._caminho_xml = resultado.caminho_xml
            self._caminho_relatorio = resultado.caminho_relatorio
            self._atualizar_botoes()

            print(f"Validação local: {resultado.status_local}")
            print(f"Validação XSD: {resultado.status_xsd}")
            print(resultado.mensagem)

            if (
                resultado.status_local == RESULTADO_FALHA_TECNICA
                or resultado.status_xsd == RESULTADO_FALHA_TECNICA
            ):
                self._definir_status(STATUS_FALHA_TECNICA, "StatusFalha.TLabel")
                messagebox.showerror(
                    "Falha técnica", resultado.mensagem, parent=self.raiz
                )
            else:
                self._definir_status(STATUS_CONCLUIDO, "StatusConcluido.TLabel")

        if self.raiz.winfo_exists():
            self.raiz.after(POLL_INTERVAL_MS, self._verificar_fila)

    def _ao_fechar(self) -> None:
        if self._processando:
            if not messagebox.askyesno(
                "Operação em andamento",
                "Existe uma operação em andamento. Encerrar a aplicação mesmo assim?",
                parent=self.raiz,
            ):
                return
        self.raiz.destroy()


def run_gui() -> None:
    raiz = tk.Tk()
    try:
        raiz.iconbitmap(str(ICONE_JANELA))
    except tk.TclError:
        pass
    Aplicacao(raiz)
    raiz.mainloop()
