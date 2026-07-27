# Matriz Excel → XML — Documento 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `docs/matriz_campos.md`  
**Etapa:** 1.2 — Matriz de campos  
**Objetivo:** documentar como cada coluna das abas de entrada será lida, normalizada, validada, agrupada e convertida para o XML.

---

## 1. Escopo do arquivo de entrada

O contrato atual aceita dois formatos.

Formato principal:

```text
Base
Cabecalho
```

Formato legado compatível:

```text
Base
Cabecalho
Sistemas_Origem
Contas_Internas
```

Abas adicionais poderão existir, mas serão ignoradas.

A ausência de `Base` ou `Cabecalho`, assim como a presença de somente uma das
duas abas auxiliares, deve resultar em:

```text
FALHA TÉCNICA
```

### 1.1. Responsabilidade de cada aba

| Aba | Responsabilidade |
|---|---|
| `Cabecalho` | Atributos do elemento raiz `<documento>` |
| `Base` | Eventos, probabilidades, contabilizações, referências embutidas e cálculo dos consolidados |
| `Sistemas_Origem` | Tabela legada opcional de códigos e nomes dos sistemas |
| `Contas_Internas` | Tabela legada opcional de códigos e nomes das contas internas |

No formato de duas abas, os nomes das referências são informados em
`nomeSistemaOrigem`, `nomeContaBalAnaliticoDebito` e
`nomeContaBalAnaliticoCredito`. Pares repetidos de código e nome são
deduplicados; o mesmo código com nomes diferentes é impeditivo.

### 1.2. Fonte dos eventos consolidados

A aba `Eventos_Consolidados` não integra o contrato produtivo. O bloco XML é calculado exclusivamente a partir dos eventos completos e validados da aba `Base`, depois do agrupamento por `idEvento` e da classificação pelos limiares oficiais.

O sistema não deverá criar eventos ou valores fictícios para satisfazer o XSD.

---

## 2. Ordem de precedência

Em caso de divergência:

1. XSD, para estrutura, nomes, tipos, formatos e cardinalidades;
2. instruções de preenchimento, para regras de negócio;
3. críticas de pré-processamento;
4. críticas de pós-processamento;
5. modelo PDF e XML de exemplo, somente como referência.

Toda divergência deverá ser registrada em `docs/conflitos_documentais.md`.

---

## 3. Colunas utilizadas na matriz

| Coluna | Significado |
|---|---|
| `Aba` | Aba do Excel de origem |
| `Coluna Excel / Origem` | Nome da coluna ou indicação de cálculo |
| `Campo XML` | Atributo ou elemento de destino |
| `Bloco XML` | Local do XML |
| `Tipo` | Tipo lógico utilizado no Python |
| `Formato XSD` | Restrição estrutural do XSD |
| `Domínio / Regra` | Valores permitidos e regra principal |
| `Obrigatoriedade` | Obrigatoriedade no Excel e no XML |
| `Conversão` | Normalização necessária |
| `Cálculo / Validação` | Cálculo, confronto ou relacionamento |
| `Versão` | Vigência da regra |
| `Fonte` | Documento oficial que sustenta o mapeamento |

---

# 4. Matriz da aba `Cabecalho`

A aba deverá conter uma única linha de dados.

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Cabecalho` | `codigoDocumento` ou valor fixo | `codigoDocumento` | `documento` | `str` | padrão `5050` | Deve ser sempre `5050` | Excel: opcional; XML: obrigatório | Se vier preenchido, remover espaços e validar; se ausente, usar o valor fixo oficial | Não há cálculo | 12/2020+ | XSD 12/2020 e 06/2025; instruções |
| `Cabecalho` | `dataBase` | `dataBase` | `documento` | `YearMonth` interno | `xs:gYearMonth`, `AAAA-MM` | Mês permitido: `06` ou `12`; mínimo `2020-12` | Excel: obrigatória; XML: obrigatória | Aceitar data Excel, `MM/AAAA`, `AAAA-MM` e converter para `AAAA-MM` | Seleciona instrução, XSD, campos, domínios e críticas | 12/2020+ | XSD; instruções; `matriz_versoes.md` |
| `Cabecalho` | `codigoConglomerado` | `codigoConglomerado` | `documento` | `str` | `C` + 7 dígitos; tamanho 8 | Deve existir no UNICAD | Excel: obrigatória; XML: obrigatória | Remover espaços e converter para maiúsculas; não inventar prefixo ou dígitos | Formato local; existência externa fica `NÃO EXECUTADA` sem UNICAD | 12/2020+ | XSD; crítica `DRO001001` |
| `Cabecalho` | `cnpj` | `cnpj` | `documento` | `str` | 8 dígitos | Oito primeiros dígitos do CNPJ da instituição líder | Excel: obrigatória; XML: obrigatória | Remover `.`, `/`, `-`; aceitar raiz de 8 dígitos ou extrair os 8 primeiros de um CNPJ completo com 14 dígitos; preservar zeros à esquerda | Não validar os dígitos verificadores do CNPJ completo; o documento usa somente a raiz de 8 dígitos | 12/2020+ | XSD; instruções |
| `Cabecalho` | `tipoRemessa` | `tipoRemessa` | `documento` | `str` | enumeração | `I` ou `S` | Excel: obrigatória; XML: obrigatória | Remover espaços e converter para maiúsculas | `I`: inclusão; `S`: substituição de documento já aceito | 12/2020+ | XSD; instruções |
| `Cabecalho` | `opcaoPorProvisaoAcumulada` | `opcaoPorProvisaoAcumulada` | `documento` | `str` | `S|N` | `S` ou `N` | Excel: obrigatória; XML: obrigatória | Remover espaços e converter para maiúsculas | Confrontar com contabilizações antigas informadas de forma acumulada | 12/2020+ | XSD; instruções |

### 4.1. Regra para mais de uma linha

Se houver mais de uma linha preenchida na aba `Cabecalho`, o sistema não deverá selecionar arbitrariamente uma delas.

```text
CAB-EST-001 — A aba Cabecalho contém mais de uma linha de dados.
```

---

# 5. Matriz da aba `Base` — identificação e atributos do evento

Linhas com o mesmo `idEvento` representam partes de um único evento.

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Base` | `Source.Name` | não vai ao XML | Metadado | `str` | não aplicável | Nome do arquivo ou origem do dado | Excel: opcional; XML: não aplicável | Remover espaços externos; preservar valor original no relatório | Usado somente para rastreabilidade | Projeto | Especificação do projeto |
| `Base` | `idEvento` | `idEvento` | `eventosIndividualizados/evento` | `str` | alfanumérico, 1 a 40 caracteres | Deve ser único no documento e consistente entre datas-base | Excel: obrigatória; XML: obrigatória | Preservar texto; não remover hífen silenciosamente; hífen é inválido nos XSDs fornecidos | Validar formato localmente (`BASE-IDEVENTO-FORM-001`); agrupar linhas pelo valor normalizado; validar conflitos e duplicidade | 12/2020+ | XSD; instruções; `DRO001103` |
| `Base` | `categoriaNivel1` | `categoriaNivel1` | `evento` | `str` | `[1-8]` | Códigos de 1 a 8 | Excel: obrigatória; XML: obrigatória | `1 - descrição` → `1`, preservando a descrição no relatório | Validar formato localmente (`BASE-CATEGORIA1-FORM-001`); deve ser consistente em todas as linhas do evento | 12/2020+ | XSD; Anexo I |
| `Base` | `categoriaNivel2` | `categoriaNivel2` | `evento` | `str` | `11, 12, 21, 22, 31, 32, 33, 41, 42, 43, 44, 45, 51, 61, 71, 81-86` | Deve ser compatível com `categoriaNivel1` | Excel: condicional; XML: opcional no XSD e obrigatório por regra para eventos alcançados pela vigência | `11 - descrição` → `11` | Validar domínio localmente (`BASE-CATEGORIA2-FORM-001`); validar obrigatoriedade e combinação nível 1 × nível 2 | Eventos a partir de 01/01/2021 | XSD; instruções; `DRO001212`; pós `DRO000009` e `DRO000021` |
| `Base` | `tipoAvaliacao` | `tipoAvaliacao` | `evento` | `str` | 2020/2025: `I|M|NA` | `I`: individual; `M`: massificada; `NA`: não se aplica | Excel: obrigatória; XML: obrigatória | `I - Individual` → `I`; maiúsculas | Validar domínio localmente (`BASE-AVALIACAO-FORM-001`); controla probabilidade, risco e provisão | 12/2020 até 2026-06 | XSD 12/2020 e 06/2025 |
| `Base` | `tipoAvaliacao` | `tipoAvaliacao` | `evento` | `str` | Instrução nova: `I|IE|M|ME|NA` | `IE` e `ME` representam processos encerrados | Excel: futura/condicional; XML: conflito com XSD fornecido | Normalização de código e descrição | Não emitir `IE` ou `ME` no XML 06/2025 | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | `unidadeNegocio` | `unidadeNegocio` | `evento` | `str` | `[1-8]` | Códigos do Anexo III | Excel: obrigatória; XML: obrigatória | `1 - Varejo` → `1` | Validar formato localmente (`BASE-UNIDADE-FORM-001`); deve ser consistente por evento | 12/2020+ | XSD; Anexo III |
| `Base` | `dataDescoberta` | `dataDescoberta` | `evento` | `date` | `AAAA-MM-DD` | Não deve ser anterior à ocorrência; regra de preenchimento conforme vigência | Excel: condicional; XML: opcional no XSD | Aceitar data Excel, `DD/MM/AAAA`, `AAAA-MM-DD` e data/hora | Validar com `dataOcorrencia` e contabilizações | Eventos alcançados a partir de 01/01/2021 | XSD; instruções; `DRO001201`, `DRO001202`; pós `DRO000010` |
| `Base` | `dataOcorrencia` | `dataOcorrencia` | `evento` | `date` | `AAAA-MM-DD` | Data definida segundo política interna da instituição | Excel: obrigatória; XML: obrigatória | Normalizar para `AAAA-MM-DD` | Deve ser menor ou igual à descoberta, quando esta existir | 12/2020+ | XSD; instruções; `DRO001201` |
| `Base` | `totalPerdaEfetiva` | `totalPerdaEfetiva` | `evento` | `Decimal` | `-?\d{1,16}\.\d{2}` | Total de perda efetiva; convenção de saldo final positivo | Excel: obrigatória; XML: obrigatória | Normalizar número brasileiro/internacional; saída com duas casas | Calcular total esperado pelas contabilizações e confrontar; não corrigir silenciosamente | 12/2020+ | XSD; instruções; pós `DRO000011`, `DRO000015` |
| `Base` | `totalProvisao` | `totalProvisao` | `evento` | `Decimal` | `-?\d{1,16}\.\d{2}` | Saldo da provisão na data-base | Excel: condicional; XML: opcional no XSD | Normalizar com `Decimal`; usar zero somente quando permitido pela instrução | Calcular saldo esperado de `valorProvisao` e confrontar; considerar sinais e ordem temporal | 12/2020+ | XSD; instruções; `DRO001301`, `DRO001302`; pós `DRO000012`, `DRO000015` |
| `Base` | `totalRecuperado` | `totalRecuperado` | `evento` | `Decimal` | `-?\d{1,16}\.\d{2}` | Recuperação acumulada com sinal negativo | Excel: obrigatória; XML: obrigatória | Normalizar com duas casas; não inverter sinal automaticamente | Confrontar com soma de `valorRecuperacao`; módulo não pode superar perda bruta | 12/2020+ | XSD; instruções; `DRO001232`; pós `DRO000013`, `DRO000014`, `DRO000015` |
| `Base` | `valorTotalRisco` | `valorTotalRisco` | `evento` | `Decimal` | `-?\d{1,16}\.\d{2}` | Requerido para contingência individual conforme regra de risco | Excel: condicional; XML: opcional | Normalizar com `Decimal` | Confrontar com provisão e detalhamentos de `valorRisco`, conforme a crítica aplicável | 12/2020+ | XSD; instruções; `DRO001311` |
| `Base` | `naturezaContingencia` | `naturezaContingencia` | `evento` | `str` | 2020/2025: `TRI|TRA|CIV|NA` | Tributária, trabalhista, cível ou não aplicável | Excel: obrigatória; XML: obrigatória | `TRA - Trabalhista` → `TRA`; maiúsculas | Validar domínio localmente (`BASE-NATUREZA-FORM-001`); validar coerência com avaliação, risco e contas | 12/2020 até 2026-06 | XSD 12/2020 e 06/2025 |
| `Base` | `naturezaContingencia` | `naturezaContingencia` | `evento` | `str` | Instrução nova inclui `OUT` | Outras contingências | Excel: futura/condicional; XML: conflito com XSD 06/2025 | Código e descrição → código | Não emitir `OUT` no XML 06/2025 | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | `codSistemaOrigem` | `codSistemaOrigem` | `evento` | `str` | alfanumérico, 1 a 10 caracteres | Deve existir em `Sistemas_Origem.codigoSistema` | Excel: obrigatória; XML: obrigatória | Preservar texto e zeros; remover somente espaços externos | Validar formato localmente (`BASE-SISTEMA-FORM-001`); validar chave estrangeira e consistência por evento | 12/2020+ | XSD; instruções; `DRO001321` |
| `Base` | `codigoEventoOrigem` | `codigoEventoOrigem` | `evento` | `str` | alfanumérico, 1 a 73 caracteres | Usar `MANUAL` quando o preenchimento tiver sido manual | Excel: obrigatória; XML: obrigatória | Preservar texto; caracteres como hífen não são aceitos pelo XSD fornecido | Validar comprimento, padrão (`BASE-EVENTOORIGEM-FORM-001`) e consistência por evento | 12/2020+ | XSD; instruções |
| `Base` | `descricaoEvento` | `descricaoEvento` | `evento` | `str` | até 200 caracteres | Deve descrever causa, classificação e, quando aplicável, origem da recuperação | Excel: condicional; XML: opcional | Colapsar espaços; preservar acentos; não truncar silenciosamente | Validar tamanho localmente após colapsar espaços (`BASE-DESCRICAO-FORM-001`); pela precedência, exigir quando `dataOcorrencia >= 2021-01-01` e `totalPerdaEfetiva + totalProvisao >= 1.000.000`; manter `DRO001241` não executada por `CONF-022` | 12/2020+ | Instruções; conflito `CONF-022` |
| `Base` | `riscoAssociado` | `riscoAssociado` | `evento` | `str` | `C|M|NA` | Crédito, mercado ou não aplicável | Excel: condicional; XML: opcional | `C - Crédito` → `C`; maiúsculas | Validar domínio localmente (`BASE-RISCOASSOCIADO-FORM-001`); obrigatoriedade conforme vigência; validar consistência histórica quando houver base anterior | Eventos alcançados a partir de 01/01/2021 | XSD; `DRO001251`; pós `DRO000028` |
| `Base` | `ligacaoRiscoSocioambiental` | `ligadoRiscoSocioAmbiental` | `evento` | `str` | `S|N` | Alias da coluna Excel para o nome exigido no XSD confirmado | Excel: condicional; XML: opcional | `S - Sim` → `S`; mapear alias; maiúsculas | Validar domínio localmente (`BASE-SOCIOAMBIENTAL-FORM-001`); obrigatoriedade conforme vigência; comparação histórica quando disponível | Eventos alcançados a partir de 01/01/2021 | XSD; `DRO001252`; pós `DRO000030` |
| `Base` | `ligacaoRiscoSocioambiental` | `ligadoRSAC` | Campo descrito nas instruções novas | `str` | não confirmado em XSD | Nome alternativo usado no texto da instrução 12/2026 | Excel: mesma coluna de origem; XML: conflito | Não usar até confirmação por XSD compatível | Registrar conflito de nomenclatura | 12/2026+ | Instruções 12/2026; conflito documental |
| `Base` | `ligadoRiscoCibernetico` | `ligadoRiscoCibernetico` | `evento` | `str` | `S|N` | Sim ou não | Excel: condicional; XML: opcional | Código e descrição → código; maiúsculas | Validar domínio localmente (`BASE-CIBERNETICO-FORM-001`); obrigatoriedade conforme vigência; comparação histórica quando disponível | Eventos alcançados a partir de 01/01/2021 | XSD; `DRO001253`; pós `DRO000029` |
| `Base` | `negocioDescontinuado` | `negocioDescontinuado` | `evento` | `str` | `S|N` | Sim ou não | Excel: opcional; XML: opcional | Código e descrição → código; maiúsculas | Validar domínio localmente (`BASE-NEGOCIO-FORM-001`) quando preenchido | 12/2020+ | XSD; instruções |
| `Base` | `idBacen` | `idBacen` | `evento` | `str` | `Z` + 7 dígitos ou `I` + 5 dígitos | Deve existir nas bases do Bacen | Excel: obrigatória; XML: obrigatória | `Z1234567 - Banco Exemplo` → `Z1234567`; preservar prefixo e zeros | Validar formato localmente, aceitando prefixo minúsculo (`BASE-IDBACEN-FORM-001`); existência externa fica `NÃO EXECUTADA` sem UNICAD | 12/2020+ | XSD; instruções; `DRO001002` |
| `Base` | `idEventoAgregador` | `idEventoAgregador` | `evento` | `str` | instrução: alfanumérico até 40 | Agrupa eventos com a mesma causa raiz | Excel: futura/opcional; XML: ausente no XSD 06/2025 | Preservar código; não remover caracteres para “encaixar” | Validar grupos e limiar agregado somente quando a versão for confirmada | 12/2026+ | Instruções 12/2026; conflito `VER-001` |

---

# 6. Matriz da aba `Base` — probabilidades de perda

Um evento pode ter no máximo três registros de probabilidade, um para cada código `PR`, `PO` e `RE`.

A chave lógica será:

```text
idEvento + probabilidadePerda
```

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Base` | `probabilidadePerda` | `probabilidade` | `evento/probabilidadesPerdas/probabilidadePerda` | `str` | `PR|PO|RE` | Provável, possível ou remota | Excel: condicional; XML: obrigatório quando o registro de probabilidade existir | `PR - Provável` → `PR`; maiúsculas | Validar domínio localmente (`BASE-PROBABILIDADE-FORM-001`); não informar para avaliação massificada; validar duplicidade por evento | 12/2020+ | XSD; instruções; `DRO001312`, `DRO001313` |
| `Base` | `valorRisco` | `valorRisco` | `probabilidadePerda` | `Decimal` | `-?\d{1,16}\.\d{2}` | Valor em risco associado à probabilidade | Excel: condicional; XML: obrigatório quando `probabilidadePerda` existir | Normalizar com `Decimal` e duas casas | Confrontar com `valorTotalRisco` e provisão conforme regra aplicável | 12/2020+ | XSD; instruções; `DRO001311`, `DRO001314`; pós `DRO000003`, `DRO000005` |

### 6.1. Conflito de duplicidade

Se o mesmo evento possuir duas linhas com a mesma probabilidade e valores de risco diferentes, o sistema deverá registrar conflito e não escolher ou somar arbitrariamente.

```text
MAP-PROB-001 — Probabilidade repetida com valores conflitantes.
```

Duplicidades perfeitamente idênticas poderão ser consolidadas em um único elemento, com registro informativo no relatório.

---

# 7. Matriz da aba `Base` — contabilizações

O bloco `<contabilizacoes>` é opcional para o evento. Porém, quando existir, deve conter ao menos uma `<contabilizacao>`.

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Base` | `dataContabilizacao` | `dataContabilizacao` | `evento/contabilizacoes/contabilizacao` | `date` | `AAAA-MM-DD` | Data do lançamento | Excel: obrigatória quando houver contabilização; XML: obrigatória no elemento | Normalizar data Excel, `DD/MM/AAAA`, ISO ou data/hora | Não deve ser anterior à descoberta; ordenar lançamentos para cálculos de saldo | 12/2020+ | XSD; instruções; pós `DRO000010` |
| `Base` | `contaBalAnaliticoDebito` | `contaBalAnaliticoDebito` | `contabilizacao` | `str` | 1 a 24 dígitos | Deve existir em `Contas_Internas.codigoConta` | Excel: condicional; XML: opcional no XSD | Tratar como texto; preservar zeros; não converter para número | Validar formato localmente (`BASE-CONTABAL-FORM-001`); validar cadastro, par COSIF e exigência conforme natureza do lançamento | 12/2020+ | XSD; `DRO001401`, `DRO001441`, `DRO001443`, `DRO001451`, `DRO001452` |
| `Base` | `contaBalAnaliticoCredito` | `contaBalAnaliticoCredito` | `contabilizacao` | `str` | 1 a 24 dígitos | Deve existir em `Contas_Internas.codigoConta` | Excel: condicional; XML: opcional no XSD | Tratar como texto; preservar zeros | Validar formato localmente (`BASE-CONTABAL-FORM-001`); validar cadastro, par COSIF e exigência conforme natureza do lançamento | 12/2020+ | XSD; `DRO001402`, `DRO001442`, `DRO001444`, `DRO001451`, `DRO001452` |
| `Base` | `contaCosifDebito` | `contaCosifDebito` | `contabilizacao` | `str` | XSD 12/2020: 8 dígitos; XSD 06/2025: 8 ou 10 dígitos | Conta COSIF válida para a versão | Excel: condicional; XML: opcional no XSD | Preservar zeros; não remover pontuação sem regra confirmada; valor pontuado deve gerar análise/erro | Validar formato local; existência e adequação dependem da base COSIF | 12/2020 ou 06/2025+ | XSD; `DRO001431`, `DRO001441`, `DRO001443` |
| `Base` | `contaCosifCredito` | `contaCosifCredito` | `contabilizacao` | `str` | XSD 12/2020: 8 dígitos; XSD 06/2025: 8 ou 10 dígitos | Conta COSIF válida para a versão | Excel: condicional; XML: opcional no XSD | Preservar zeros; não remover pontuação sem regra confirmada | Validar formato local; existência e adequação dependem da base COSIF | 12/2020 ou 06/2025+ | XSD; `DRO001432`, `DRO001442`, `DRO001444` |
| `Base` | `valorPerdaEfetiva` | `valorPerdaEfetiva` | `contabilizacao` | `Decimal` | `-?\d{1,16}\.\d{2}` | Perda contabilizada; saldo acumulado não deve ficar negativo | Excel: obrigatória quando houver contabilização; XML: obrigatória no elemento | Normalizar; saída com duas casas; não substituir inválido por zero | Somar por evento e confrontar com `totalPerdaEfetiva`; verificar saldo cronológico | 12/2020+ | XSD; instruções; pós `DRO000015`, `DRO000023` |
| `Base` | `valorProvisao` | `valorProvisao` | `contabilizacao` | `Decimal` | `-?\d{1,16}\.\d{2}` | Constituições positivas e reversões negativas conforme regra | Excel: condicional; XML: opcional | Normalizar com `Decimal`; usar zero somente quando a instrução determinar | Calcular saldo cronológico e confrontar com `totalProvisao` | 12/2020+ | XSD; instruções; `DRO001301`, `DRO001302`; pós `DRO000015`, `DRO000024` |
| `Base` | `valorRecuperacao` | `valorRecuperacao` | `contabilizacao` | `Decimal` | `-?\d{1,16}\.\d{2}` | Recuperação deve ser negativa | Excel: opcional/condicional; XML: opcional | Normalizar sem inverter sinal | Lançamento de recuperação deve ser exclusivo; confrontar com `totalRecuperado` | 12/2020+ | XSD; instruções; `DRO001411`; pós `DRO000013`, `DRO000015` |
| `Base` | `fonteRecuperacao` | `fonteRecuperacao` | `contabilizacao` | `str` | `S|O|NA` | Seguro, outras formas ou não aplicável | Excel: condicional; XML: opcional | `S - Seguro` → `S`; maiúsculas | Validar domínio localmente (`BASE-FONTERECUPERACAO-FORM-001`); exigir quando houver recuperação, conforme vigência; `NA` somente quando aplicável | Eventos alcançados a partir de 01/01/2021 | XSD; instruções; `DRO001421` |

### 7.1. Identidade das contabilizações

Contabilizações idênticas não deverão ser descartadas automaticamente, pois podem representar lançamentos legítimos distintos.

Na ausência de um identificador próprio do lançamento, cada linha válida da `Base` será preservada como uma ocorrência contábil.

---

# 8. Matriz da aba `Sistemas_Origem`

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Sistemas_Origem` | `codigoSistema` | `codigoSistema` | `sistemasOrigem/sistema` | `str` | alfanumérico, 1 a 10 caracteres | Código único e consistente entre datas-base | Excel: obrigatória; XML: obrigatória | Preservar texto e zeros; remover espaços externos | Validar unicidade e existência de cada código usado na `Base` | 12/2020+ | XSD; instruções; `DRO001102`, `DRO001321` |
| `Sistemas_Origem` | `nomeSistema` | `nomeSistema` | `sistema` | `str` | alfanumérico e espaço, 1 a 70 caracteres | Nome do sistema legado | Excel: obrigatória; XML: obrigatória | Colapsar espaços; preservar o texto; não truncar silenciosamente | Validar formato/tamanho localmente após colapsar espaços (`BASE-NOMESISTEMA-FORM-001`); não permitir nome vazio; código repetido com nome diferente é conflito | 12/2020+ | XSD; instruções |

### 8.1. Sistemas não utilizados

Um sistema cadastrado mas não utilizado na `Base` poderá gerar aviso informativo, mas não erro impeditivo, salvo regra oficial posterior.

---

# 9. Matriz da aba `Contas_Internas`

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Contas_Internas` | `codigoConta` | `codigoConta` | `contasSubtitulosInternos/conta` | `str` | 1 a 24 dígitos | Código único da conta interna | Excel: obrigatória; XML: obrigatória | Tratar como texto; preservar zeros à esquerda | Validar unicidade e existência de cada conta interna usada na `Base` | 12/2020+ | XSD; instruções; `DRO001101`, `DRO001401`, `DRO001402` |
| `Contas_Internas` | `nomeConta` | `nomeConta` | `conta` | `str` | alfanumérico e espaço, 1 a 70 caracteres | Nome da conta interna | Excel: obrigatória; XML: obrigatória | Colapsar espaços; preservar texto; não truncar | Validar formato/tamanho localmente após colapsar espaços (`BASE-NOMECONTA-FORM-001`); código repetido com nome diferente é conflito | 12/2020+ | XSD; instruções |

---

# 10. Campos XML — eventos consolidados

Os sete campos são calculados exclusivamente a partir da aba `Base`. Eventos com perda bruta acumulada igual ou superior a R$ 1.000,00 ou risco não coberto igual ou superior a R$ 10.000.000,00 são individualizados; os demais candidatos válidos são agrupados por `categoriaNivel1`.

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato XSD | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Base` | categoria normalizada do grupo | `categoriaNivel1Consol` | `eventosConsolidados/eventoConsolidado` | `str` | `[1-8]` | Uma ocorrência por categoria | XML: obrigatório | Ordenar numericamente | Validar domínio e unicidade | 12/2020+ | XSD; instruções |
| `Base` | contagem de `idEvento` distintos | `numEventosTotalConsol` | `eventoConsolidado` | `int` | 1 a 18 dígitos | Quantidade total de eventos consolidados | XML: obrigatório | Inteiro sem casas | Não contar linhas ou contabilizações | 12/2020+ | XSD; instruções |
| `Base` | primeira `dataContabilizacao` | `numEventosSemestreConsol` | `eventoConsolidado` | `int` | 1 a 18 dígitos | Eventos iniciados no semestre civil | XML: obrigatório | Inteiro sem casas | Pode ser zero; não inventar datas | 12/2020+ | XSD; instruções |
| `Base` | soma de `totalPerdaEfetiva` | `perdaEfetivaTotalConsol` | `eventoConsolidado` | `Decimal` | duas casas | Perdas efetivas acumuladas | XML: obrigatório | `Decimal`, ponto e duas casas | Somar uma vez por `idEvento` | 12/2020+ | XSD; instruções |
| `Base` | `valorPerdaEfetiva` no semestre | `perdaEfetivaSemestreConsol` | `eventoConsolidado` | `Decimal` | duas casas | Movimentos de perda no semestre | XML: obrigatório | `Decimal`, ponto e duas casas | Filtrar pela data contábil | 12/2020+ | XSD; instruções |
| `Base` | soma de `totalProvisao` | `provisaoTotalConsol` | `eventoConsolidado` | `Decimal` | duas casas | Saldo provisionado na data-base | XML: obrigatório | `Decimal`, ponto e duas casas | Somar uma vez por `idEvento` | 12/2020+ | XSD; instruções |
| `Base` | `valorProvisao` no semestre | `provisaoSemestreConsol` | `eventoConsolidado` | `Decimal` | duas casas | Constituições e reversões do semestre | XML: obrigatório | `Decimal`, ponto e duas casas | Preservar o sinal dos movimentos | 12/2020+ | XSD; instruções |
| `Base` | provisões CIV | `provisaoTotalCIV` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Provisões consolidadas de natureza cível | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Somar eventos `CIV` por categoria | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | provisões TRA | `provisaoTotalTRA` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Provisões consolidadas trabalhistas | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Somar eventos `TRA` por categoria | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | provisões TRI constitucionais | `provisaoTotalTRI_CONST` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Classificação depende da conta contábil indicada na instrução | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Somar conforme natureza e conta aplicável | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | provisões TRI outros | `provisaoTotalTRI_OUTROS` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Classificação depende da conta contábil indicada na instrução | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Somar conforme natureza e conta aplicável | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | demais provisões | `provisaoTotalOUTROS` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Valores não incluídos nos quatro campos anteriores | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Calcular somente após definição inequívoca das categorias | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | recuperações acumuladas | `recuperacaoTotalConsol` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Recuperações totais dos eventos consolidados | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Somar recuperações por categoria | 12/2026+ | Instruções 12/2026; conflito `VER-001` |
| `Base` | recuperações do semestre | `recuperacaoSemestreConsol` | `eventoConsolidado` | `Decimal` | instrução: duas casas | Recuperações do último semestre | Futuro; ausente no XSD 06/2025 | Não gerar na versão confirmada atual | Somar recuperações no intervalo semestral | 12/2026+ | Instruções 12/2026; conflito `VER-001` |

### 10.1. Regra de contagem

Os campos de quantidade devem contar `idEvento` distintos, nunca linhas da planilha.

### 10.2. Eventos abaixo do limiar

A classificação deve considerar as regras oficiais de individualização, inclusive:

- perda bruta;
- provisões;
- valor de risco não coberto;
- grupo de eventos agregados, quando a versão compatível existir.

Não utilizar somente o valor de uma linha contábil.

---

# 11. Campos futuros de exclusão de eventos

As instruções 12/2026 apresentam o bloco:

```xml
<eventosIndividualizadosExcluidos>
    <evento
        idEvento="..."
        dataExclusao="..."
        motivoExclusao="..."/>
</eventosIndividualizadosExcluidos>
```

Esse bloco não existe no XSD 06/2025 fornecido.

| Aba | Coluna Excel / Origem | Campo XML | Bloco XML | Tipo | Formato | Domínio / Regra | Obrigatoriedade | Conversão | Cálculo / Validação | Versão | Fonte |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Base` | `idEvento` | `idEvento` | `eventosIndividualizadosExcluidos/evento` | `str` | alfanumérico até 40 | Deve ser o mesmo ID anteriormente individualizado | Futuro; obrigatório no evento excluído | Preservar código | Requer comparação com a data-base anterior | 12/2026+ | Instruções 12/2026 |
| `Base` | `dataExclusao` | `dataExclusao` | `evento` excluído | `date` | `AAAA-MM-DD` | Data que ensejou a não obrigatoriedade | Futuro; obrigatória no evento excluído | Normalizar data | Não pode ser inventada; validar com período e histórico | 12/2026+ | Instruções 12/2026 |
| `Base` | `motivoExclusao` | `motivoExclusao` | `evento` excluído | `str` | divergência documental | Anexo IV apresenta códigos `1` a `8`; o leiaute ilustrativo apresenta `[1-6]` | Futuro; obrigatória no evento excluído | `1 - descrição` → `1` | Não implementar domínio definitivo antes de XSD compatível ou esclarecimento oficial | 12/2026+ | Instruções 12/2026; conflito documental |

### 11.1. Conflito do domínio de `motivoExclusao`

Foi identificada uma divergência dentro das próprias instruções 12/2026:

- o Anexo IV relaciona motivos de `1` a `8`;
- o leiaute XML ilustrativo indica `[1-6]`.

Decisão:

```text
Não considerar o domínio resolvido.
Não gerar o bloco com o XSD 06/2025.
Registrar o conflito até existir XSD compatível ou esclarecimento oficial.
```

---

# 12. Cardinalidades estruturais confirmadas pelos XSDs

| Estrutura | Cardinalidade |
|---|---|
| `<documento>` | uma raiz |
| `<eventosIndividualizados>` | exatamente 1 bloco |
| `<evento>` dentro de individualizados | 1 a ilimitados |
| `<probabilidadesPerdas>` | 0 ou 1 por evento |
| `<probabilidadePerda>` | 0 a 3 |
| `<contabilizacoes>` | 0 ou 1 por evento |
| `<contabilizacao>` | 1 a ilimitadas quando o bloco existir |
| `<eventosConsolidados>` | exatamente 1 bloco |
| `<eventoConsolidado>` | 1 a 8 |
| `<sistemasOrigem>` | exatamente 1 bloco |
| `<sistema>` | 1 a ilimitados |
| `<contasSubtitulosInternos>` | exatamente 1 bloco |
| `<conta>` | 1 a ilimitadas |

O XSD 12/2020 contém uma chave de unicidade para `idEvento`. O XSD 06/2025 não contém essa chave, mas a unicidade continua sendo validada localmente pelas instruções e críticas.

---

# 13. Colunas mínimas esperadas por versão confirmada

## 13.1. Aba `Cabecalho`

```text
dataBase
codigoConglomerado
cnpj
tipoRemessa
opcaoPorProvisaoAcumulada
```

`codigoDocumento` poderá estar presente, mas o sistema também poderá usar o valor fixo `5050`.

## 13.2. Aba `Base`

Colunas de estrutura esperadas:

```text
Source.Name
idEvento
categoriaNivel1
categoriaNivel2
tipoAvaliacao
unidadeNegocio
dataDescoberta
dataOcorrencia
totalPerdaEfetiva
totalProvisao
totalRecuperado
valorTotalRisco
naturezaContingencia
codSistemaOrigem
codigoEventoOrigem
descricaoEvento
riscoAssociado
ligacaoRiscoSocioambiental
ligadoRiscoCibernetico
negocioDescontinuado
idBacen
probabilidadePerda
valorRisco
dataContabilizacao
contaBalAnaliticoDebito
contaBalAnaliticoCredito
contaCosifDebito
contaCosifCredito
valorPerdaEfetiva
valorProvisao
valorRecuperacao
fonteRecuperacao
```

Estas colunas são futuras e poderão estar ausentes nas versões confirmadas anteriores a 12/2026:

```text
idEventoAgregador
dataExclusao
motivoExclusao
```

### 13.3. Coluna ausente versus célula vazia

- **Coluna ausente:** erro estrutural quando a coluna pertence ao contrato da versão.
- **Célula vazia:** avaliada conforme a obrigatoriedade do campo e a situação do evento.
- **Coluna futura ausente:** aceita enquanto não fizer parte da versão confirmada.

## 13.4. Aba `Sistemas_Origem`

```text
codigoSistema
nomeSistema
```

## 13.5. Aba `Contas_Internas`

```text
codigoConta
nomeConta
```

---

# 14. Agrupamento e consistência por `idEvento`

Para cada conjunto de linhas do mesmo `idEvento`, estes campos devem possuir um único valor normalizado:

```text
categoriaNivel1
categoriaNivel2
tipoAvaliacao
unidadeNegocio
dataDescoberta
dataOcorrencia
totalPerdaEfetiva
totalProvisao
totalRecuperado
valorTotalRisco
naturezaContingencia
codSistemaOrigem
codigoEventoOrigem
descricaoEvento
riscoAssociado
ligacaoRiscoSocioambiental
ligadoRiscoCibernetico
negocioDescontinuado
idBacen
idEventoAgregador
```

Se houver valores diferentes, o sistema deverá gerar uma inconsistência com:

- `idEvento`;
- linhas envolvidas;
- coluna;
- valores originais;
- valores normalizados.

Ele não deverá selecionar o primeiro, o último ou o valor mais frequente.

---

# 15. Política para totais informados e calculados

A planilha fornece totais do evento, mas o sistema também deverá calcular valores esperados.

## 15.1. Valores mantidos separadamente

Exemplo interno:

```text
totalPerdaEfetiva_informado
totalPerdaEfetiva_calculado
```

O mesmo vale para:

```text
totalProvisao
totalRecuperado
valorTotalRisco
```

## 15.2. Regra de geração

Por padrão:

1. normalizar o valor informado;
2. calcular o valor esperado;
3. comparar os dois;
4. registrar inconsistência quando divergirem;
5. não substituir silenciosamente o valor informado;
6. somente aplicar correção automática se houver regra determinística, configuração explícita e registro completo da transformação.

A política definitiva de qual valor será escrito no XML em caso de divergência será definida antes da etapa do `xml_builder`.

---

# 16. Política de normalização

## 16.1. Nulos

Candidatos a ausência:

```text
vazio
None
NaN
NULL
N/A
-
*
```

`NA` não é nulo automaticamente, pois é domínio válido em vários campos.

## 16.2. Datas

Aceitar:

```text
data nativa do Excel
DD/MM/AAAA
AAAA-MM-DD
data com horário
```

Saída XML:

```text
AAAA-MM-DD
```

Cabeçalho:

```text
AAAA-MM
```

## 16.3. Valores monetários

Usar `Decimal`, nunca `float`.

Exemplos aceitos:

```text
1.427,98
1427,98
1427.98
1.552.165,46
-1200,00
```

Exemplos ambíguos ou inválidos:

```text
1.222,111,11
1,22,33
```

## 16.4. Códigos com descrição

Exemplo:

```text
8 - Falhas na execução
```

Resultado XML:

```text
8
```

A descrição deverá ser preservada no relatório de transformações.

---

# 17. Códigos internos iniciais da etapa de mapeamento

| Código | Gravidade | Descrição |
|---|---|---|
| `MAP-ABA-001` | FALHA TÉCNICA | Uma das quatro abas obrigatórias não foi encontrada |
| `MAP-COL-001` | ERRO IMPEDITIVO | Coluna obrigatória para a versão não encontrada |
| `MAP-CAB-001` | ERRO IMPEDITIVO | Mais de uma linha preenchida no cabeçalho |
| `MAP-EVT-001` | ERRO IMPEDITIVO | Valores conflitantes entre linhas do mesmo evento |
| `MAP-PROB-001` | ERRO IMPEDITIVO | Probabilidade repetida com valores de risco conflitantes |
| `MAP-SIS-001` | ERRO IMPEDITIVO | Sistema utilizado na Base não existe em Sistemas_Origem |
| `MAP-CONTA-001` | ERRO IMPEDITIVO | Conta interna utilizada na Base não existe em Contas_Internas |
| `CONS-CALC-001` | ERRO IMPEDITIVO | Valores, datas ou categorias impedem a classificação ou o cálculo consolidado |
| `MAP-VER-001` | ERRO IMPEDITIVO | Campo da instrução 12/2026 sem suporte no XSD fornecido |

---

# 18. Exemplo de transformação hierárquica

Entrada simplificada:

| idEvento | dataContabilizacao | valorPerdaEfetiva |
|---|---|---:|
| `ORLD0001` | `2025-02-01` | `1511,25` |
| `ORLD0001` | `2025-02-16` | `813,75` |

Resultado estrutural:

```xml
<evento
    idEvento="ORLD0001"
    totalPerdaEfetiva="2325.00"
    ...>
    <contabilizacoes>
        <contabilizacao
            dataContabilizacao="2025-02-01"
            valorPerdaEfetiva="1511.25"
            .../>
        <contabilizacao
            dataContabilizacao="2025-02-16"
            valorPerdaEfetiva="813.75"
            .../>
    </contabilizacoes>
</evento>
```

Duas linhas do Excel geram:

```text
1 evento
2 contabilizações
```

---

# 19. Decisões que permanecem pendentes

Antes da construção do XML, ainda deverão ser resolvidos ou formalizados:

1. política definitiva para escrever no XML totais divergentes;
2. comprovação de que a `Base` produtiva conterá eventos individualizados e consolidados;
3. tratamento de cenário sem nenhum evento consolidado, considerando a cardinalidade mínima do XSD;
4. XSD compatível com as instruções 12/2026;
5. nome definitivo do campo socioambiental na nova versão;
6. domínio definitivo de `motivoExclusao`;
7. disponibilidade de base COSIF e UNICAD;
8. disponibilidade da data-base anterior para regras históricas.

---

# 20. Estado da etapa

```text
Etapa 1.2 — Matriz Excel → XML: CONCLUÍDA
Próxima etapa: 1.3 — Matriz de críticas e validações
```

## Mapeamento final implementado na etapa 5.8

Mapeamentos cujo nome no XML difere da coluna de entrada:

| Coluna da entrada | Atributo XML | Fonte da decisão |
|---|---|---|
| `ligacaoRiscoSocioambiental` | `ligadoRiscoSocioAmbiental` | XSD |
| `probabilidadePerda` | `probabilidade` | XSD |
| `codSistemaOrigem` | `codSistemaOrigem` | XSD |
| `Contas_Internas.codigoConta` | `contasSubtitulosInternos/conta@codigoConta` | XSD |

Os campos `idEventoAgregador`, `dataExclusao` e `motivoExclusao` são
preservados para diagnóstico, mas não são mapeados para os XSDs fornecidos.
