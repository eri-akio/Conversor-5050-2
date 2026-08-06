# Normalizadores reutilizáveis da aba `Base`

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.1 — Datas, valores, domínios e identificadores  
**Arquivos principais:** `src/normalizers/`

---

## 1. Objetivo

Criar funções pequenas e reutilizáveis para preparar os valores da aba
`Base`, sem ainda montar eventos ou gerar XML.

Cada normalizador retorna um `NormalizationResult` com:

```text
status
valor original
valor normalizado
representação para o XML
regra aplicada
indicação de alteração
descrição extraída
código e mensagem de erro
```

Estados possíveis:

```text
VALID
ABSENT
INVALID
```

O estado `ABSENT` não decide se o campo é obrigatório. Essa decisão
será responsabilidade do validador da versão e da situação do evento.

---

## 2. Normalização de datas

Arquivo:

```text
src/normalizers/date_normalizer.py
```

Entradas aceitas:

```text
data nativa do Excel
datetime
DD/MM/AAAA
AAAA-MM-DD
DD/MM/AAAA HH:MM:SS
AAAA-MM-DD HH:MM:SS
formato ISO com T
```

Saída para o XML:

```text
AAAA-MM-DD
```

Um número só é interpretado como serial do Excel quando o formato da
célula indica data. Isso evita transformar valores monetários ou códigos
numéricos em datas por engano.

Exemplo:

```python
resultado = normalize_date(
    celula.value,
    excel_number_format=celula.number_format,
)

print(resultado.normalized_value)  # datetime.date
print(resultado.serialized_value)  # 2026-06-30
```

Erros:

| Código | Situação |
|---|---|
| `DATA-NULO-001` | Candidato a ausência |
| `DATA-TIPO-001` | Tipo não suportado ou número sem formato de data |
| `DATA-EXCEL-001` | Serial do Excel inválido |
| `DATA-FMT-001` | Texto com data inválida |

---

## 3. Normalização monetária

Arquivo:

```text
src/normalizers/decimal_normalizer.py
```

O valor interno é sempre:

```python
Decimal
```

Nunca `float`.

Exemplos aceitos:

```text
1.427,98       → 1427.98
1427,98        → 1427.98
1427.98        → 1427.98
1.552.165,46   → 1552165.46
-1.200,00      → -1200.00
R$ 1.427,98    → 1427.98
(210,00)       → -210.00
```

A saída padrão possui duas casas:

```text
1427.98
-1200.00
```

Valores ambíguos não são adivinhados:

```text
1.222
1,222
1.222,111,11
1,22,33
```

Exemplo:

```python
resultado = normalize_decimal("1.427,98")

print(resultado.normalized_value)  # Decimal("1427.98")
print(resultado.serialized_value)  # "1427.98"
```

Erros:

| Código | Situação |
|---|---|
| `DEC-NULO-001` | Candidato a ausência |
| `DEC-TIPO-001` | Tipo não suportado |
| `DEC-FINITO-001` | NaN ou infinito |
| `DEC-FMT-001` | Formato inválido |
| `DEC-AMB-001` | Separadores ambíguos |
| `DEC-ESCALA-001` | Casas decimais excedentes |
| `DEC-TAMANHO-001` | Parte inteira excedente |
| `DEC-SINAL-001` | Valor negativo não permitido pela chamada |
| `DEC-SIMBOLO-001` | Símbolo monetário inválido |
| `DEC-PARENTESES-001` | Parênteses contábeis inválidos |
| `DEC-CIENTIFICA-001` | Notação científica textual |
| `DEC-PRECISAO-001` | Risco de perda de precisão numérica |

O normalizador não converte valor inválido para `0.00`.
Transformações de `R$` e parênteses usam códigos de regra próprios e geram
aviso auditável na normalização da Base.

---

## 4. Normalização de domínios

Arquivo:

```text
src/normalizers/domain_normalizer.py
```

A função não possui uma lista regulatória fixa. O chamador fornece os
códigos válidos conforme o campo e a versão.

Exemplo:

```python
resultado = normalize_domain(
    "8 - Falhas na execução",
    allowed_codes={"1", "2", "3", "4", "5", "6", "7", "8"},
)
```

Resultado:

```text
código: 8
descrição preservada: Falhas na execução
```

Para códigos alfabéticos:

```python
resultado = normalize_domain(
    "tra - Trabalhista",
    allowed_codes={"TRI", "TRA", "CIV", "NA"},
)
```

Saída:

```text
TRA
```

`NA` pode ser aceito quando estiver no domínio informado. `N/A` continua
sendo candidato a ausência.

Erros:

| Código | Situação |
|---|---|
| `DOM-NULO-001` | Candidato a ausência |
| `DOM-TIPO-001` | Tipo de código não suportado |
| `DOM-COD-001` | Código fora do domínio fornecido |

---

## 5. Normalização de identificadores

Arquivo:

```text
src/normalizers/identifier_normalizer.py
```

Funções especializadas:

```text
normalize_event_id
normalize_source_system_code
normalize_origin_event_code
normalize_internal_account_code
normalize_cosif_account
normalize_bacen_id
```

### `idEvento`

Por decisao local mantida pelo projeto, todos os hifens de `idEvento` sao
removidos antes do agrupamento e da validacao alfanumerica final:

```text
ORLD-1234 -> ORLD1234
IND--0001 -> IND0001
```

O valor original permanece em `CampoNormalizado.valor_original`. Colisoes
entre origens distintas sao erros impeditivos (`BASE-IDEVENTO-COLISAO-001`);
por exemplo, `IND-0001` e `IND0001` nao podem ser reunidos silenciosamente.
Depois da remocao, o valor deve ser alfanumerico e possuir de 1 a 40
caracteres.

### `idBacen`

Exemplo:

```text
Z1234567 - Banco Exemplo
```

Resultado:

```text
código: Z1234567
descrição preservada: Banco Exemplo
```

Formatos aceitos:

```text
Z + 7 dígitos
I + 5 dígitos
```

### COSIF

A função recebe os tamanhos permitidos pela versão:

```python
normalize_cosif_account(
    valor,
    allowed_lengths={8},
)
```

para o XSD 12/2020, ou:

```python
normalize_cosif_account(
    valor,
    allowed_lengths={8, 10},
)
```

para o XSD 06/2025.

Pontuação não é removida, porque não há regra confirmada que autorize
essa transformação.

### Preservação de zeros

Identificadores especializados exigem texto. Um número vindo do Excel
é rejeitado, pois não é possível saber se zeros à esquerda já foram
eliminados.

Exemplo correto:

```text
"00001234"
```

Exemplo tecnicamente inseguro:

```text
1234
```

---

## 6. Integração com o leitor

Exemplo usando uma célula da aba `Base`:

```python
base = excel_result.get_sheet("Base")
linha = base.rows[0]

data = linha.get_cell("dataOcorrencia")

data_normalizada = normalize_date(
    data.value,
    excel_number_format=data.number_format,
)
```

O normalizador recebe o valor bruto e os metadados da célula, mas não
altera a planilha.

---

## 7. Limites desta etapa

Esta etapa ainda não:

- verifica as 35 colunas da aba `Base`;
- decide obrigatoriedades condicionais;
- agrupa linhas por `idEvento`;
- calcula totais;
- classifica eventos individualizados ou consolidados;
- executa críticas;
- gera XML.

Esses normalizadores serão usados pelo futuro leitor e mapeador da
`Base`.

---

## 8. Como testar

Todos os testes:

```powershell
python -m pytest -v
```

Somente esta etapa:

```powershell
python -m pytest tests/test_date_normalizer.py tests/test_decimal_normalizer.py tests/test_domain_normalizer.py tests/test_identifier_normalizer.py -v
```

---

## 9. Estado

```text
Etapa 5.1 — Normalizadores reutilizáveis da Base: CONCLUÍDA
Próxima etapa: 5.2 — Validar a estrutura e as colunas da aba Base
```
