# Validação de obrigatoriedades e relações por linha

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.4 — Obrigatoriedades e relações entre campos  
**Arquivo principal:** `src/validators/base_row_validator.py`

## 1. Objetivo

Executar somente regras que podem ser decididas usando os campos de uma única
linha já normalizada da aba `Base`.

O resultado de cada regra registra:

```text
código
fonte
descrição
gravidade
status
linha
idEvento
tipo da linha
colunas envolvidas
valores originais
valores normalizados
mensagem
sugestão
```

Status possíveis:

```text
APROVADA
REPROVADA
NÃO APLICÁVEL
REGRA NÃO EXECUTADA
```

Uma regra não executada nunca é tratada como aprovada.

## 2. Tipos de linha

### Evento individualizado

É o tipo padrão para os perfis confirmados e para linhas sem dados de exclusão.

Campos obrigatórios locais:

```text
idEvento
categoriaNivel1
tipoAvaliacao
unidadeNegocio
dataOcorrencia
totalPerdaEfetiva
totalRecuperado
naturezaContingencia
codSistemaOrigem
codigoEventoOrigem
idBacen
```

### Evento excluído

No perfil `DRO_2026_12_PRESUMIDA`, a presença de `dataExclusao` ou
`motivoExclusao` classifica a linha como evento excluído.

Campos obrigatórios:

```text
idEvento
dataExclusao
motivoExclusao
```

O domínio definitivo de `motivoExclusao` continua não executado devido ao
conflito documental já registrado.

## 3. Regras locais executadas

### Datas e classificação

- `DRO001201`: `dataOcorrencia <= dataDescoberta`;
- `DRO001202`: `dataDescoberta` obrigatória a partir de 01/01/2021;
- `DRO001212`: `categoriaNivel2` obrigatória a partir de 01/01/2021;
- `BASE-REL-CAT-001`: compatibilidade entre nível 1 e nível 2;
- `DRO001251`, `DRO001252` e `DRO001253`: campos de risco obrigatórios a partir de 01/01/2021.

### Limiares e totais

- `DRO001231`: perda + provisão deve atingir R$ 1.000,00 para evento individualizado;
- `DRO001232`: módulo da recuperação não pode superar perda + provisão;
- `BASE-RISCO-001`: `valorTotalRisco`, quando informado, deve atingir R$ 10.000.000,00;

### Descrição do evento

As instruções usam:

```text
totalPerdaEfetiva + totalProvisao
```

A crítica `DRO001241` usa:

```text
totalPerdaEfetiva + valorTotalRisco
```

Foi registrado `CONF-022`.

A validação local executa a regra das instruções como:

```text
BASE-OBR-DESC-001
```

A crítica `DRO001241` permanece `REGRA NÃO EXECUTADA`.

### Contingências e provisões

- `BASE-REL-CONT-001`: coerência entre `tipoAvaliacao` e `naturezaContingencia`;
- `DRO001233`: natureza obrigatória quando `valorTotalRisco` for informado;
- `DRO001301`: avaliação `NA` não pode possuir provisão diferente de zero;
- `DRO001302`: contingências devem possuir informação de provisão.

### Probabilidades

- `BASE-PROB-001`: `probabilidadePerda` e `valorRisco` formam um par;
- `DRO001313`: avaliação massificada não pode possuir probabilidade.

As regras abaixo dependem do conjunto completo de linhas do evento:

```text
DRO001312
DRO001314
```

Elas são marcadas como `REGRA NÃO EXECUTADA` nesta etapa.

### Contabilizações

- `BASE-CONT-REQ-001`: registro contábil exige data e valor de perda;
- `BASE-CONT-DATA-001`: contabilização não pode ser anterior à descoberta;
- `DRO001411`: recuperação deve ser menor ou igual a zero;
- `DRO001421`: recuperação negativa exige fonte `S` ou `O`;
- `DRO001441` a `DRO001444`: pares entre conta interna e conta COSIF;
- `DRO001451`: movimentação diferente de zero exige os campos contábeis;
- `BASE-REC-EXCL-001`: no perfil 12/2026, recuperação deve ser lançamento exclusivo.

`DRO001452` depende da análise de todas as linhas do evento e permanece não
executada nesta etapa.

## 4. Regras não incluídas nesta etapa

Ainda dependem de agrupamento, abas auxiliares, histórico ou bases externas:

```text
unicidade e conflitos por idEvento
probabilidades repetidas
soma dos valores de risco
composição de valorTotalRisco
soma e saldo das contabilizações
referência a Sistemas_Origem
referência a Contas_Internas
existência UNICAD
validade cadastral COSIF
eventos consolidados
histórico entre datas-base
```

## 5. Resultado agregado

`BaseRowsValidationResult` informa:

```text
row_count
locally_valid_row_count
invalid_row_count
status_counts
failed_rules
not_executed_rules
is_locally_valid
is_fully_verified
```

`is_locally_valid` significa apenas que as regras locais executáveis não
falharam.

`is_fully_verified` somente será verdadeiro quando não houver regras pendentes.

## 6. Como executar

```powershell
python main.py "D:\Documentos\DRO_5050_planilha.xlsx"
```

## 7. Como testar

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_base_row_validator.py -v
```

## 8. Próxima etapa

```text
5.5 — Agrupar as linhas por idEvento e validar consistência do evento
```
