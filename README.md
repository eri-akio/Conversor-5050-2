# Conversor DRO 5050 (versão simples)

Aplicação em Python 3.13 para ler a planilha Excel do DRO 5050, validar as
regras locais aplicáveis, gerar o XML, validar contra o XSD 06/2025 e
produzir um relatório XLSX.

> Reconstrução concluída (Fases 0–10): a arquitetura antiga em camadas foi
> removida. O código novo segue `src/`, com uma função por crítica e
> validações diretas por `if`, sem motor de regras genérico. Testado de
> ponta a ponta via `python main.py` com aprovação local e XSD.

## Fonte da verdade

O contrato funcional completo — escopo regulatório, precedência entre
fontes, fluxo, estrutura de colunas, regras de pré/pós-processamento e
formato do relatório — está em
[`docs/plano_conversor_dro_5050_simples.md`](docs/plano_conversor_dro_5050_simples.md).
Qualquer dúvida sobre uma regra deve ser resolvida por esse documento, não
pelo código.

## Estrutura

```text
main.py
src/
    models.py          modelos de dados
    reader.py          leitura e validação estrutural da planilha
    normalizers.py     normalização pura de células
    calculations.py    fórmulas e classificação puras
    builders.py        construção de eventos, mapas e consolidados
    rules_local.py     ocorrências locais BASE-*
    rules_pre.py       críticas oficiais DRO001*
    rule_pos.py        críticas oficiais DRO000*
    xsd_validator.py   carga e validação do XSD 06/2025
    xml_writer.py      construção, serialização e gravação do XML
    report_writer.py   relatório XLSX
    conversion.py      orquestração do fluxo completo
    gui.py             interface desktop Tkinter/ttk
assets/fonte/
    dro_5050_2025_06.xsd
    criticas_pre_processamento_5050.xlsx
    criticas_pos_processamento_5050.xlsx
tests/
```

## Uso

```powershell
python main.py
```

Abre a interface desktop. Em modo terminal:

```powershell
python main.py "D:\dados\DRO_5050.xlsx" --output-dir "D:\saidas"
```

## Instalação e testes

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

## Gerando o executável (Windows)

```powershell
python -m pip install pyinstaller
python -m PyInstaller SmartReporting.spec --clean --noconfirm
```

Gera `dist/SmartReporting.exe` — um único arquivo, sem console, com o
XSD já embutido (`assets/schemas/`). Não precisa de Python instalado na
máquina que for rodar o `.exe`. Para reconstruir a receita do zero (ex.:
depois de adicionar um novo módulo `hiddenimports`), o comando original
usado foi:

```powershell
python -m PyInstaller --name "SmartReporting" --onefile --windowed --add-data "assets/schemas;assets/schemas" --hidden-import "src" --clean --noconfirm main.py
```

Isso sobrescreve `SmartReporting.spec`. `build/` e `dist/` não são
versionados (`.gitignore`); o `.spec` é.

## Progresso da reconstrução

Ver o roadmap completo (10 fases) em
`docs/plano_conversor_dro_5050_simples.md`, seção 25.

- [x] Fase 0 — contrato funcional fechado (regras de sinal incluídas)
- [x] Fase 1 — estrutura mínima do projeto
- [x] Fase 2 — leitura e validação estrutural
- [x] Fase 3 — normalização e modelos
- [x] Fase 4 — agrupamento, probabilidades, contabilizações
- [x] Fase 5 — críticas de pré-processamento
- [x] Fase 6 — consolidação e críticas de pós-processamento
- [x] Fase 7 — XML e validação XSD
- [x] Fase 8 — relatório XLSX
- [x] Fase 9 — interface desktop
- [x] Fase 10 — homologação ponta a ponta

### Nota sobre a Fase 10

Validada com `fonte/planilha input - DRO_5050_teste_XML.xlsx` (planilha
real no novo formato): `python main.py "fonte/planilha input -
DRO_5050_teste_XML.xlsx" --output-dir <pasta>` produz validação local e
XSD aprovadas, XML e relatório sem nenhuma inconsistência.

Essa planilha revelou que `categoriaNivel1`, `categoriaNivel2`,
`tipoAvaliacao` e `naturezaContingencia` chegam como `"código -
descrição"` (ex.: `"I - Individual"`), não como código puro — convenção
de uma lista de validação do Excel, já documentada no projeto anterior
(`docs/matriz_campos.md`: `"I - Individual" → "I"`). O normalizador
(`src/normalizers.py::normalizar_codigo_rotulado`) extrai o código
antes do separador `" - "`; código puro continua aceito sem alteração.
Ver seção 8 do plano funcional.

`assets/DRO_5050_teste.xlsx` continua incompatível (formato legado antigo:
35 colunas, nomes de sistema/conta em abas separadas, totais informados em
vez de calculados) e não deve ser usado com este leitor.
