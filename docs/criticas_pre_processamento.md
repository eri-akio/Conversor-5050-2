# Críticas oficiais de pré-processamento

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.11  
**Fonte oficial:** `assets/regulatory/criticas_pre_processamento_5050.xlsx`

## 1. Objetivo

Integrar em um único resultado as 34 críticas oficiais de
pré-processamento.

As regras locais já executadas nas etapas anteriores não são
recalculadas. O integrador reutiliza as evidências produzidas por:

```text
validação por linha
agrupamento por idEvento
validação do evento
tabelas de referência
```

Essa abordagem evita duas implementações divergentes para a mesma
crítica.

## 2. Catálogo oficial

Cada regra contém:

```text
código
documento
tipo oficial
descrição oficial
base confrontada
data de início
escopo
classe de execução
dependência
provedor técnico
arquivo de origem
```

O catálogo possui exatamente 34 códigos, de `DRO001001` a
`DRO001452`.

## 3. Vigência

O arquivo oficial informa início em:

```text
jun/21
```

O sistema converte essa informação para:

```text
2021-06
```

Em `dataBase` anterior, cada crítica recebe:

```text
NÃO APLICÁVEL
```

A comparação é feita com `YearMonth`, não com texto.

## 4. Consolidação dos resultados

Uma crítica pode produzir diversas evidências, por exemplo uma para
cada evento ou contabilização.

O status final da regra usa esta precedência:

```text
REPROVADA
REGRA NÃO EXECUTADA
APROVADA
NÃO APLICÁVEL
```

Portanto, uma única ocorrência reprovada impede que a crítica seja
consolidada como aprovada.

## 5. Dependências externas

### `DRO001001`

Consulta ao UNICAD para confirmar o código do conglomerado:

```text
REGRA NÃO EXECUTADA
```

### `DRO001002`

Consulta ao UNICAD/Bacen para cada `idBacen`:

```text
REGRA NÃO EXECUTADA
```

O formato local do identificador não substitui a confirmação de sua
existência.

## 6. Contas COSIF

### `DRO001431` e `DRO001432`

A aplicação já verifica localmente:

```text
formato
quantidade de dígitos
preservação de zeros
presença do par contábil
```

A existência da conta no cadastro oficial COSIF agora é verificada
diretamente contra `assets/lista_COSIF_validas.txt` (um código por
linha, carregado em `src.regulatory_constants.CONTAS_COSIF_VALIDAS`),
por `validar_conta_cosif_debito`/`validar_conta_cosif_credito` em
`src/rules_pre.py`.

Quando uma conta COSIF é informada e existe no cadastro:

```text
APROVADA
```

Quando uma conta COSIF é informada e não existe no cadastro:

```text
REPROVADA
```

Quando há conta interna e falta a COSIF correspondente:

```text
REPROVADA (DRO001441/DRO001442)
```

Quando não há lançamento aplicável:

```text
NÃO APLICÁVEL
```

### `DRO001443` e `DRO001444`

A relação local entre conta COSIF e conta interna utiliza os resultados
já produzidos pela validação por linha.

## 7. Conflito documental

`DRO001241` permanece:

```text
REGRA NÃO EXECUTADA
```

por causa de `CONF-022`, que registra fórmulas diferentes entre as
instruções e a crítica oficial.

Nenhuma das fórmulas foi escolhida silenciosamente.

## 8. Aptidão

Uma crítica não executada não é considerada aprovada.

`PreProcessingValidationResult` informa:

```text
rule_count
evidence_count
status_counts
failed_rules
not_executed_rules
is_locally_valid
is_fully_verified
blocks_apt
```

É possível não haver erro local e, ainda assim, o documento permanecer
não apto porque existem dependências externas não verificadas.

## 9. Integração com o documento

O resultado é passado ao `DocumentBuilder`.

Regras de pré-processamento não executadas geram:

```text
DOC-PRE-NE-001
```

Elas não impedem a criação de XML diagnóstico, mas bloqueiam a
classificação final como `APTO`.

## 10. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 11. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_pre_processing.py -v
```

## 12. Próxima etapa

```text
5.12 — Integrar e executar as críticas de pós-processamento
```
