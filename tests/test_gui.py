"""Teste de fumaca da Fase 9: a interface desktop constroi sem erros
(src/gui.py)."""

from __future__ import annotations

import tkinter as tk

import pytest

from pathlib import Path

from src.gui import STATUS_AGUARDANDO, Aplicacao, pasta_saida_padrao


@pytest.fixture
def raiz_tk():
    try:
        raiz = tk.Tk()
    except tk.TclError as erro:
        pytest.skip(f"Tkinter sem Tcl utilizável neste ambiente: {erro}")
    yield raiz
    raiz.destroy()


def test_aplicacao_constroi_com_status_inicial_aguardando(raiz_tk) -> None:
    app = Aplicacao(raiz_tk)

    assert app.status.get() == STATUS_AGUARDANDO
    assert app.botao_converter.instate(["!disabled"])
    assert app.botao_abrir_xml.instate(["disabled"])
    assert app.botao_abrir_relatorio.instate(["disabled"])


def test_pasta_saida_padrao_e_downloads_conversor_5050() -> None:
    assert pasta_saida_padrao() == Path.home() / "Downloads" / "conversor 5050"


def test_aplicacao_ja_preenche_pasta_de_saida_padrao(raiz_tk) -> None:
    app = Aplicacao(raiz_tk)

    assert app.pasta_saida.get() == str(pasta_saida_padrao())


def test_converter_sem_planilha_selecionada_nao_inicia_thread(
    raiz_tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = Aplicacao(raiz_tk)
    chamou_erro = {}
    monkeypatch.setattr(
        "src.gui.messagebox.showerror",
        lambda titulo, msg, **_kwargs: chamou_erro.setdefault("msg", msg),
    )

    app._iniciar_conversao()

    assert "msg" in chamou_erro
    assert app._processando is False
