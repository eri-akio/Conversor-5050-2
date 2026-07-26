# Plano do Conversor DRO 5050 Simples

## 1. Objetivo

Construir um conversor simples e profissional que:

1. leia a planilha de entrada do DRO 5050;
2. normalize e agrupe os dados por `idEvento`;
3. aplique as validações locais e as críticas oficiais executáveis;
4. gere os eventos individualizados e consolidados;
5. gere o XML do Documento 5050;
6. valide o XML no XSD 06/2025;
7. gere um relatório XLSX com o resultado e as inconsistências;
8. disponibilize uma interface desktop igual à interface simplificada atual.

O projeto será de homologação, sem consultas externas. A prioridade é manter o
código legível para um desenvolvedor iniciante, sem perder rastreabilidade e
conformidade.

## 2. Escopo regulatório

- Documento: `5050`.
- Data-base inicial de homologação: `2026-06`.
- XSD determinante: esquema válido a partir da data-base 06/2025.
- Entrada principal: abas `Base` e `Cabecalho`.
- Instruções 12/2026: fora do MVP.
- Validações externas UNICAD/Bacen/COSIF: fora do escopo.
- Comparações com a data-base anterior: fora do escopo.
- Valores monetários: sempre tratados com `Decimal`, nunca com `float`.

O programa poderá declarar:

```text
Validação local: APROVADO, REPROVADO ou FALHA TÉCNICA
Validação XSD: APROVADO, REPROVADO, NÃO EXECUTADO ou FALHA TÉCNICA
```

Não declarará aceitação garantida pelo Bacen, pois não executa consultas
externas nem validações históricas.

## 3. Precedência adotada

1. XSD 06/2025 para nomes XML, estrutura, cardinalidade, tipo, formato e domínio.
2. Críticas oficiais fornecidas para as condições dos códigos `DRO...`.
3. Instruções de Preenchimento para regras semânticas não conflitantes.
4. Regras locais do contrato da planilha, sempre identificadas como locais.
5. XML e PDF de exemplo apenas como referência.

Uma regra local nunca será apresentada como se fosse texto oficial da crítica.

## 4. Fluxo completo

```text
Selecionar planilha e pasta de saída
    ↓
Validar arquivo, abas e colunas
    ↓
Ler e normalizar Cabecalho
    ↓
Validar Cabecalho (codigoDocumento, dataBase, codigoConglomerado, cnpj,
                    tipoRemessa, opcaoPorProvisaoAcumulada — seção 7)
    ↓
Normalizar células da Base e validar linhas
    ↓
Detectar colisões de idEvento (seção 8)
    ↓
Agrupar por idEvento e validar consistência
    ↓
Calcular totais e probabilidades
    ↓
Classificar individualizados e consolidados
    ↓
Montar sistemas e contas internas
    ↓
Executar críticas de pré/pós-processamento locais por evento
    ↓
Se dataBase válida:
    Validar datas do evento contra o período da data-base (seção 17)
    Calcular eventos consolidados (seção 16)
    Executar críticas de pós-processamento dos consolidados
Senão:
    Nenhuma etapa dependente de semestre é executada
    ↓
Construir XML em memória (só quando aprovado localmente)
    ↓
Validar no XSD 06/2025
    ↓
Gerar relatório XLSX
    ↓
Salvar XML final somente quando aprovado
```

O relatório será tentado sempre, inclusive quando um erro de dados impedir a
geração do XML — inclusive quando a própria `dataBase` for inválida (nesse
caso o nome do relatório usa o sufixo técnico `SEM_DATA_BASE` em vez da
data-base, que não existe).

## 5. Interface desktop

A interface será mantida no mesmo formato da aplicação atual, usando
`Tkinter/ttk`.

```text
Título: Smart Reporting - CADOC 5050

Planilha Excel: [caminho] [Selecionar]
Pasta de saída: [caminho] [Selecionar] [Abrir pasta]

Status: Aguardando / Processando... / Concluído / Falha técnica

[Converter, validar e gerar XML/XLSX]
[Abrir XML]
[Abrir relatório XLSX]
```

Comportamento:

- somente uma conversão poderá ser executada por vez;
- o processamento será executado em uma thread de trabalho;
- a janela permanecerá responsiva usando fila de eventos e `after`;
- os botões de abrir artefatos serão habilitados somente quando o arquivo existir;
- a interface apenas chamará o serviço de conversão;
- nenhuma regra regulatória ficará dentro da camada visual;
- a interface validará inicialmente a seleção do `.xlsx` e da pasta de saída;
- o fechamento durante o processamento solicitará confirmação;
- a pasta de saída já vem preenchida com `Downloads\conversor 5050` (pasta
  do usuário) ao abrir a interface; o usuário pode trocar pela seleção.

## 6. Estrutura simples do novo projeto

```text
main.py
dro5050/
    models.py
    reader.py
    normalizers.py
    calculations.py
    rules_pre.py
    rules_post.py
    xml_writer.py
    report_writer.py
    conversion.py
    gui.py
resources/
    dro_5050_2025_06.xsd
tests/
```

Cada crítica será uma função explícita, com condições `if`, sem motor genérico
de regras, banco de dados ou configuração dinâmica de versões.

## 7. Validação do arquivo, abas e cabeçalhos

### Arquivo

- deve existir;
- deve possuir extensão `.xlsx`;
- deve abrir sem corrupção;
- deve permitir leitura.

Arquivo inexistente ou ilegível gera `FALHA TÉCNICA`.

### Abas obrigatórias

```text
Base
Cabecalho
```

- nomes são comparados sem diferença entre maiúsculas e minúsculas e ignorando
  espaços externos;
- não haverá reconhecimento aproximado;
- abas adicionais serão ignoradas;
- cabeçalhos estarão obrigatoriamente na linha 1;
- cabeçalhos duplicados são erro impeditivo (`XLSX-COL-002`);
- a `Base` deve possuir ao menos uma linha de dados; caso contrário, `XLSX-BASE-001`;
- a `Cabecalho` deve possuir exatamente uma linha de dados; nenhuma linha ou
  mais de uma linha geram `XLSX-CAB-002`.

### Colunas da aba `Cabecalho`

```text
codigoDocumento
dataBase
codigoConglomerado
cnpj
tipoRemessa
opcaoPorProvisaoAcumulada
```

#### Tratamento de formatação

O XSD 06/2025 exige formatos rígidos para alguns campos do cabeçalho
(`codigoConglomerado`: `C` maiúsculo + 7 dígitos; `cnpj`: exatamente 8
dígitos; `tipoRemessa`/`opcaoPorProvisaoAcumulada`: enumerações em
maiúsculo). Uma planilha real pode preencher esses campos com outra
formatação equivalente; o valor é normalizado, não substituído:

| Campo | Entrada de exemplo | Tratamento |
|---|---|---|
| `codigoConglomerado` | `c0099999` | Convertido para maiúsculo: `C0099999` |
| `cnpj` | `46.169.337/0001-28` (14 dígitos) ou `46169337` (8 dígitos, já a raiz) | Remove `.`, `/` e `-`; se restarem exatamente 8 ou exatamente 14 dígitos ASCII (`[0-9]`), usa os 8 primeiros (a raiz do CNPJ): `46169337` |
| `tipoRemessa` | `i` | Convertido para maiúsculo: `I` |
| `opcaoPorProvisaoAcumulada` | `n` | Convertido para maiúsculo: `N` |

Isso não é correção de valor inválido nem substituição automática
(proibidas na seção 8) — é reconhecer uma forma alternativa e equivalente
do mesmo código, exatamente como já feito para `categoriaNivel1` etc. na
seção 8. Se o CNPJ, após remover a pontuação, não tiver exatamente 8 nem
exatamente 14 dígitos ASCII (ex.: 9-13 dígitos, letras misturadas,
dígitos Unicode fora de `[0-9]`), o campo fica inválido — nenhum dígito é
inventado nem truncado silenciosamente. `codigoDocumento` não recebe esse
tratamento (já chega correto).

`dataBase` é normalizada para o formato `AAAA-MM`, mas com validação de
negócio própria (não é "já chega correto"): deve ter mês `06` ou `12`
(o Documento 5050 é semestral) e ser `>= 2020-12` (piso do XSD,
`tipoDataMesAno`, `minInclusive 2020-12`). Uma `dataBase` fora desse
domínio (ex.: `2026-07`, `2026-13`) fica inválida na normalização —
nunca é usada em cálculos de semestre com um placeholder.

#### Validação de negócio do cabeçalho (`validar_cabecalho`)

Depois da normalização, uma etapa dedicada revalida o cabeçalho inteiro
antes de qualquer processamento de eventos: `codigoDocumento == "5050"`,
`dataBase` válida (formato + mês + piso), `codigoConglomerado` casa com
`C` + 7 dígitos, `cnpj` válido, `tipoRemessa` ∈ {`I`, `S`},
`opcaoPorProvisaoAcumulada` ∈ {`S`, `N`}. Cada campo é checado em ordem
de estado (ausente → inválido → fora do domínio) antes de qualquer
verificação de formato, para nunca gerar mais de uma ocorrência para o
mesmo campo. Quando `dataBase` é inválida, o documento é reprovado
localmente e nenhuma etapa dependente de semestre (consolidação, seção
16) roda — o nome de arquivo técnico do relatório usa
`SEM_DATA_BASE` em vez de tentar formatar uma data-base inexistente.

### Colunas funcionais da aba `Base`

As 30 colunas abaixo devem existir. A presença da coluna não significa que a
célula seja sempre obrigatória.

```text
idEvento
categoriaNivel1
categoriaNivel2
tipoAvaliacao
unidadeNegocio
dataDescoberta
dataOcorrencia
naturezaContingencia
codSistemaOrigem
nomeSistema
codigoEventoOrigem
descricaoEvento
riscoAssociado
ligadoRiscoSocioAmbiental
ligadoRiscoCibernetico
negocioDescontinuado
idBacen
probabilidadePerda
valorRisco
dataContabilizacao
contaBalAnaliticoDebito
nomeContaDebito
contaBalAnaliticoCredito
nomeContaCredito
contaCosifDebito
contaCosifCredito
valorPerdaEfetiva
valorProvisao
valorRecuperacao
fonteRecuperacao
```

`Source.Name` será aceito como metadado opcional.

Será aceito somente este alias da planilha atual:

```text
ligacaoRiscoSocioambiental → ligadoRiscoSocioAmbiental
```

Se o alias e o nome canônico estiverem presentes simultaneamente, ocorrerá
erro de ambiguidade.

## 8. Ausência e normalização

| Valor original | Tratamento |
|---|---|
| célula vazia | ausência |
| somente espaços | ausência depois de remover espaços externos |
| `NA` | código válido somente onde o domínio permitir |
| `N/A` | valor inválido |
| `NULL` | valor inválido |
| `-` | valor inválido |
| `*` | valor inválido |

Não haverá correção ortográfica, remoção silenciosa de acentos, truncamento ou
substituição automática de valores inválidos.

Datas serão normalizadas para `AAAA-MM-DD`, a data-base para `AAAA-MM` e
valores monetários para ponto e duas casas no XML.

### Datas em formato brasileiro (`dataDescoberta`, `dataOcorrencia`, `dataContabilizacao`)

Além do formato ISO (`AAAA-MM-DD`) e do tipo data nativo do Excel, as três
colunas de data da `Base` também aceitam texto no formato brasileiro
`DD/MM/AAAA` (dia primeiro — nunca `MM/DD/AAAA`):

```text
"05/12/2025" → 2025-12-05  (5 de dezembro de 2025)
"5/1/2025"   → 2025-01-05  (zero à esquerda opcional)
```

Dia ou mês fora do intervalo real (ex.: `31/02/2025`) fica `INVALIDO` — a
data não é inventada nem ajustada para o dia mais próximo válido. Essa não
é uma correção de valor inválido: é reconhecer uma segunda forma válida de
escrever a mesma data, como já feito para `normalizar_codigo_rotulado` e
para os campos do Cabeçalho.

### Valores monetários

Além de número puro (ex.: `2300`), estes formatos de texto são aceitos:

```text
"1427,98"        → 1427.98  (sem separador de milhar, decimal com vírgula)
"1427.98"        → 1427.98  (sem separador de milhar, decimal com ponto)
"1.427,98"       → 1427.98  (milhar com ponto, decimal com vírgula)
"1.552.165,46"   → 1552165.46  (vários grupos de milhar)
"-1.427,98"      → -1427.98    (número negativo)
```

O separador de milhar é reconhecido tanto em grupos de exatamente 3
dígitos terminados por `,` seguida de exatamente 2 dígitos (o padrão
brasileiro completo, `"1.552.165,46"`) quanto isolado, sem parte decimal
(`"1.427"`, `"1,427"`).

**Decisão registrada (revista):** um separador único seguido de
exatamente 3 dígitos (`"1.427"`, `"1,427"`) é resolvido como separador de
milhar — `"1.427"` → `1427`, não `1427,00` interpretado como decimal de
3 casas. Isso **não é uma adivinhação entre duas leituras igualmente
válidas**: a leitura decimal teria 3 casas decimais, e nenhum valor
monetário deste sistema aceita mais de 2 (regra abaixo) — então milhar é
a única leitura que pode resultar num valor válido, o que a torna a
resolução correta, não um palpite. Essa mesma regra vale para qualquer
texto com essa forma, incluindo quando aparece como parte de um número
maior (ex.: `"1427.900"` → `1427900`, não `1427,90` — o separador único
com 3 dígitos depois é resolvido como milhar antes mesmo de qualquer
análise de casas decimais). Valores como `"R$ 1.427,98"` (com prefixo de
moeda) continuam não reconhecidos.

**Nenhum valor monetário pode ter mais de duas casas decimais reais**,
seja texto ou número nativo do Excel. Isso vale tanto para o separador
único com mais/menos de 3 dígitos (`"1427,9876"`, 4 casas → inválido)
quanto para células numéricas puras do Excel (`1200.005` → inválido) —
esse segundo caminho não passa pelo texto, então a regra de milhar
sozinha não pega esse caso. Zeros à direita não contam como casas reais
quando o valor já chega como `Decimal` numérico (`Decimal("1427.900")`
equivale a `1427.90`) — mas essa equivalência só vale para um `Decimal`
já construído fora do parser de texto; como texto de planilha,
`"1427.900"` cai na regra de milhar acima (vira `1427900`) antes de
qualquer contagem de casas decimais. Essa regra existe para impedir que
um valor sem escala válida entre no cálculo dos totais e só apareça uma
inconsistência depois, na hora de formatar o XML com exatamente duas
casas — rejeitar na normalização evita que os totais sejam calculados a
partir de um valor que seria arredondado de forma diferente mais tarde.

**Também fica `INVALIDO` um valor com mais de 16 dígitos na parte
inteira**, o limite do próprio XSD (`tipoDecimal`:
`-?\d{1,16}\.\d{2}`), e qualquer valor não finito (`NaN`/`Infinity`,
possível vindo de uma célula do Excel malformada). A checagem decompõe o
`Decimal` já construído (`as_tuple()`) e remove manualmente só os zeros
decimais não significativos — deliberadamente **não** usa
`Decimal.quantize()` (pode lançar `InvalidOperation` para valores com
mais dígitos do que a precisão do contexto decimal ativo permite) nem
`Decimal.normalize()` (arredonda silenciosamente para a precisão do
contexto ativo em vez de preservar o valor, o que a tornaria uma correção
automática disfarçada — proibida nesta seção). Nenhuma das duas operações
depende do contexto `decimal` global do processo.

### Campos com código e descrição

A planilha de homologação real usa listas de validação do Excel que gravam
"código - descrição" na célula (confirmado em
`fonte/planilha input - DRO_5050_teste_XML.xlsx`), para estes campos:

```text
categoriaNivel1     "1 - descrição"      → "1"
categoriaNivel2      "11 - descrição"     → "11"
tipoAvaliacao        "I - Individual"     → "I"
naturezaContingencia "TRA - Trabalhista"  → "TRA"
idBacen              "Z1234567 - Banco Alfa" → "Z1234567"
probabilidadePerda   "PO - Possível"      → "PO"
                     "PR - Provável"      → "PR"
                     "RE - Remoto"        → "RE"
```

O separador é sempre `" - "` (espaço, hífen, espaço). O texto antes do
separador vira o valor operativo (usado nas críticas e no XML); quando não
há separador, a célula já contém o código puro e é usada como está. O
**texto da descrição não importa** — só o que vem antes do separador é
usado, então `"NA - Nao se aplica"` e `"NA - Não Aplicável"` (variações de
acentuação/redação da mesma descrição) resolvem igualmente para `"NA"`. O
valor original completo (com a descrição) é preservado para o relatório,
nunca descartado. Essa não é uma correção de valor inválido — é o
reconhecimento de uma segunda forma válida e observada de preenchimento
do mesmo código, apoiada em `docs/matriz_campos.md` do projeto anterior
(`"I - Individual" → "I"`, `"1 - descrição" → "1"`, etc.). Nenhum outro
campo usa essa convenção nesta planilha (`riscoAssociado`,
`fonteRecuperacao` e os indicadores `S`/`N` já chegam como código puro).

### Pontuação decorativa em identificadores

Alguns identificadores podem vir com pontuação que o XSD não aceita
(`idEvento` exige só letras/dígitos; as contas exigem só dígitos). Essa
pontuação é removida antes de validar — não é correção de valor, é remover
um separador visual que não faz parte do identificador:

```text
idEvento                  "IND-0001"                       → "IND0001"  (remove "-")
contaBalAnaliticoDebito   "819.951.010.400.000.000.000.003" → "819951010400000000000003"  (remove "." e "-")
contaBalAnaliticoCredito  "8.1.9.99.00-6"                   → "819990006"  (mesma regra)
contaCosifDebito          "819.951.0104"                    → "8199510104"  (remove "." e "-")
contaCosifCredito         (mesma regra)
```

Remover o hífen de `idEvento` pode fazer dois identificadores originais
distintos colidirem no mesmo valor normalizado (ex.: `"IND-0001"` e
`"IND0001"` viram ambos `"IND0001"`). Antes do agrupamento por evento, uma
checagem dedicada compara o valor original (depois de `strip()`, para não
confundir espaços externos ou tipo Excel int/str com uma origem
diferente) de cada linha por chave normalizada; se houver mais de um
valor original distinto para a mesma chave, o documento é reprovado
localmente com `BASE-IDEVENTO-COLISAO-001`, citando as linhas e os
valores originais em conflito — os identificadores nunca são fundidos
silenciosamente num único evento.

## 9. Obrigatoriedade dos campos de nível do evento

| Coluna | Célula na Base | Obrigatoriedade XML | Regra principal |
|---|---|---|---|
| `idEvento` | sempre | obrigatória | XSD |
| `categoriaNivel1` | sempre | obrigatória | XSD |
| `categoriaNivel2` | condicional | opcional | `DRO001212` e `DRO000009` |
| `tipoAvaliacao` | sempre | obrigatória | XSD |
| `unidadeNegocio` | sempre | obrigatória | XSD |
| `dataDescoberta` | condicional | opcional | `DRO001202` |
| `dataOcorrencia` | sempre | obrigatória | XSD |
| `naturezaContingencia` | sempre | obrigatória | XSD; `DRO001233` adicional |
| `codSistemaOrigem` | sempre | obrigatória no evento | XSD |
| `nomeSistema` | sempre no contrato estrito | obrigatória no bloco de sistemas | local + XSD |
| `codigoEventoOrigem` | sempre | obrigatória | XSD |
| `descricaoEvento` | condicional | opcional | `DRO001241` |
| `riscoAssociado` | condicional | opcional | `DRO001251` |
| `ligadoRiscoSocioAmbiental` | condicional | opcional | `DRO001252` |
| `ligadoRiscoCibernetico` | condicional | opcional | `DRO001253` |
| `negocioDescontinuado` | opcional | opcional | domínio `S|N` |
| `idBacen` | sempre | obrigatória | XSD |

Condições de 2021:

```text
dataOcorrencia >= 2021-01-01
→ dataDescoberta obrigatória              DRO001202
→ categoriaNivel2 obrigatória             DRO001212
→ riscoAssociado obrigatório              DRO001251
→ ligadoRiscoSocioAmbiental obrigatório   DRO001252
→ ligadoRiscoCibernetico obrigatório      DRO001253
```

Adicionalmente:

```text
menor dataContabilizacao > 2021-01-01
+ categoriaNivel2 vazia
→ DRO000009
```

**Nota — `DRO000009` e `DRO001212` usam datas-gatilho diferentes, por
desenho oficial (auditoria confirmada contra as duas planilhas de
críticas):** `DRO001212` olha `dataOcorrencia`; `DRO000009` olha
`min(dataContabilizacao)` do evento — nunca `dataOcorrencia`. Um evento
pode ter ocorrido antes de 2021 (isentando-o de `DRO001212`) e ainda
assim ter sido contabilizado/lançado só depois de 2021, disparando
`DRO000009` mesmo assim. Isso não é uma inconsistência do conversor: são
duas críticas oficiais independentes, cada uma sobre um campo de data
diferente, e podem discordar sobre o mesmo evento.

### Domínios principais

| Campo | Domínio/formato |
|---|---|
| `idEvento` | alfanumérico, 1 a 40 caracteres |
| `categoriaNivel1` | `1` a `8` |
| `categoriaNivel2` | códigos permitidos pelo XSD |
| `tipoAvaliacao` | `I`, `M` ou `NA` |
| `unidadeNegocio` | `1` a `8` |
| `naturezaContingencia` | `TRI`, `TRA`, `CIV` ou `NA` |
| `codSistemaOrigem` | alfanumérico, 1 a 10 caracteres conforme XSD |
| `codigoEventoOrigem` | alfanumérico, 1 a 73 caracteres |
| `descricaoEvento` | até 200 caracteres |
| `riscoAssociado` | `C`, `M` ou `NA` |
| indicadores sim/não | `S` ou `N` |
| `idBacen` | `Z/z` + 7 dígitos ou `I/i` + 5 dígitos |

O `idBacen` será preservado como informado; sua existência não será validada.

```text
naturezaContingencia = NA
→ tipoAvaliacao deve ser NA

naturezaContingencia em TRI, TRA ou CIV
→ tipoAvaliacao deve ser I ou M
```

Essa validação local baseada nas instruções usará `BASE-CONT-001`.

## 10. Consistência entre linhas do evento

Devem ser iguais em todas as linhas do mesmo `idEvento`:

```text
idEvento
categoriaNivel1
categoriaNivel2
tipoAvaliacao
unidadeNegocio
dataDescoberta
dataOcorrencia
naturezaContingencia
codSistemaOrigem
nomeSistema
codigoEventoOrigem
descricaoEvento
riscoAssociado
ligadoRiscoSocioAmbiental
ligadoRiscoCibernetico
negocioDescontinuado
idBacen
```

Podem variar:

```text
probabilidadePerda
valorRisco
dataContabilizacao
contaBalAnaliticoDebito
nomeContaDebito
contaBalAnaliticoCredito
nomeContaCredito
contaCosifDebito
contaCosifCredito
valorPerdaEfetiva
valorProvisao
valorRecuperacao
fonteRecuperacao
```

O programa não escolherá arbitrariamente um valor quando houver conflito.

## 11. Probabilidades

Uma linha possui probabilidade quando `probabilidadePerda` ou `valorRisco`
estiver preenchido. Quando um existir, o outro também será obrigatório.

| Regra | Comportamento |
|---|---|
| domínio | `PR`, `PO` ou `RE` |
| quantidade | no máximo três por evento |
| repetição | cada código aparece no máximo uma vez por evento |
| `valorRisco` | `Decimal`, não negativo |
| `tipoAvaliacao=I` e data a partir de 2021 | probabilidade obrigatória, `DRO001312` |
| `tipoAvaliacao=M` | probabilidade proibida, `DRO001313` |
| `tipoAvaliacao=NA` | probabilidade proibida, regra local `BASE-PROB-002` |

Regras por probabilidade:

```text
tipoAvaliacao = I
+ probabilidadePerda = PR
+ totalProvisao = 0
→ DRO000004
```

```text
tipoAvaliacao = I
+ probabilidadePerda em PO ou RE
+ valorRisco = 0
→ DRO000005
```

```text
dataOcorrencia >= 2021-01-01
+ tipoAvaliacao = I
+ naturezaContingencia diferente de NA
+ probabilidade informada
+ soma(valorRisco) <= 0
→ DRO001314
```

## 12. Contabilizações

Uma linha é contábil quando qualquer uma das onze colunas de contabilização
estiver preenchida. Cada linha poderá gerar no máximo uma contabilização.

Quando houver contabilização, o contrato estrito exige:

```text
dataContabilizacao
valorPerdaEfetiva
valorProvisao
valorRecuperacao
```

Os três valores monetários devem ser informados numericamente, usando zero
quando não houver movimento naquela natureza. Se a contabilização foi
iniciada (qualquer uma das onze colunas preenchida) e algum desses quatro
campos estiver ausente, ocorre `BASE-CONT-OBR-001`.

**Nota — regra local mais restritiva que o XSD:** o XSD marca
`valorProvisao` e `valorRecuperacao` como `optional` em
`tipoContabilizacao` (só `dataContabilizacao` e `valorPerdaEfetiva` são
`required`). `BASE-CONT-OBR-001` exige os quatro deliberadamente, como
contrato mais estrito da planilha — não é uma reprodução do XSD nem de
uma crítica oficial, e deve ser lida como tal.

### Sinal da perda contabilizada

```text
valorPerdaEfetiva < 0
→ BASE-SINAL-CONT-001
```

Essa é uma regra local baseada nas Instruções de Preenchimento: a perda
efetiva contabilizada usa sempre sinal positivo. É avaliada por linha de
contabilização, independentemente do agrupamento por `idEvento`, e não deve
ser confundida com a convenção de sinal dos totais do evento (seção 15).

### Provisão

```text
tipoAvaliacao = NA
+ valorProvisao diferente de zero
→ DRO001301
```

Para compatibilidade com a planilha de homologação, `valorProvisao` vazio ou
igual a zero será considerado ausência de provisão em avaliação `NA`, e o
atributo será omitido do XML.

A `DRO001302` será avaliada no evento agrupado para avaliações `I` ou `M`:
reprova quando não há nenhuma contabilização registrada (proxy correto
para "nenhuma provisão informada", já que uma contabilização só existe
depois de `valorProvisao` ter sido validado como presente —
`BASE-CONT-OBR-001`), **exceto** quando o evento é exclusivamente de
risco (mesma condição de `DRO001452`, seção 12): nesse caso a ausência de
contabilizações é exigida, não um erro de provisão não informada, e as
duas críticas não podem conflitar entre si.

### Recuperação

```text
valorRecuperacao > 0
→ DRO001411
```

```text
dataOcorrencia >= 2021-01-01
+ valorRecuperacao < 0
+ fonteRecuperacao vazia ou diferente de S/O
→ DRO001421
```

```text
valorRecuperacao = 0
+ fonteRecuperacao em S/O
→ BASE-REC-FONTE-001
```

Quando a recuperação for zero, a fonte poderá estar vazia ou ser `NA`.

### Contabilização sem movimento

```text
contabilização iniciada
+ valorPerdaEfetiva = 0
+ valorProvisao = 0
+ valorRecuperacao = 0
→ BASE-CONT-SEM-MOV-001
```

Essa é uma regra local impeditiva.

### Evento exclusivamente de risco

Um evento é "exclusivamente de risco" quando a soma de `valorRisco` é
positiva E `totalPerdaEfetiva`, `totalProvisao` e `totalRecuperado` são
todos zero (nenhum movimento real). Um evento pode ter risco E movimento
real ao mesmo tempo — isso não é "exclusivamente" de risco e não aciona
nenhuma das duas críticas abaixo.

Evento exclusivamente de risco não possui contabilizações em nenhuma linha.
Se possuir informações contábeis, será gerada `DRO001452`.

Evento com perda, provisão ou recuperação (portanto não exclusivamente de
risco) deve possuir os campos contábeis aplicáveis, conforme `DRO001451`.
Duas checagens: (1) uma rede de segurança de consistência interna (totais
não-zero sem nenhuma contabilização — matematicamente inatingível a
partir de dados reais); (2) por contabilização, quando há movimento
(perda, provisão ou recuperação diferente de zero), os **dois pares de
conta precisam estar completos** — débito (`contaBalAnaliticoDebito` +
`contaCosifDebito`) e crédito (`contaBalAnaliticoCredito` +
`contaCosifCredito`). Ter só um dos dois pares não é suficiente: o XML de
exemplo oficial (`DRO - Modelo XML do Documento 5050 - Exemplo.xml`)
sempre preenche as 4 contas juntas em toda contabilização, nunca só um
lado — consistente com partida dobrada (todo lançamento tem débito e
crédito). O XSD aceita as 4 contas como opcionais (não pega isso), então
a responsabilidade é local.

## 13. Sistemas de origem e contas internas

### Sistemas

- `nomeSistema` é obrigatório no modelo estrito;
- deve ter de 1 a 70 caracteres;
- aceita somente letras ASCII, números e espaços, conforme o XSD;
- o mesmo código deve possuir sempre o mesmo nome;
- sistemas válidos serão deduplicados por código;
- conflito código/nome gera `BASE-SIS-001`;
- `DRO001321` verifica se `codSistemaOrigem` (quando informado no evento)
  existe no bloco global de sistemas (Bloco 3, deduplicado por código em
  todas as linhas da planilha) — **não** exige que `nomeSistema` esteja
  preenchido na mesma linha/evento que o referencia (isso já é coberto,
  separadamente, pela obrigatoriedade de `nomeSistema` em toda linha via
  `BASE-OBR-001`).

### Contas internas

```text
contaBalAnaliticoDebito preenchida
↔ nomeContaDebito preenchido

contaBalAnaliticoCredito preenchida
↔ nomeContaCredito preenchido
```

- conta interna: de 1 a 24 dígitos;
- nome: de 1 a 70 caracteres, somente letras ASCII, números e espaços;
- o mesmo código deve possuir sempre o mesmo nome, inclusive quando aparecer
  uma vez como débito e outra como crédito;
- contas válidas serão deduplicadas globalmente por código;
- conflito código/nome gera `BASE-CONTA-001`;
- `DRO001401`/`DRO001402` verificam se a conta interna referenciada em
  cada contabilização (`contaBalAnaliticoDebito`/`Credito`) existe no
  bloco global de contas (Bloco 4, deduplicado por código em todas as
  linhas da planilha) — **não** exigem que o nome esteja repetido na
  mesma linha que a referencia (o mesmo ajuste de `DRO001321` acima,
  mesmo motivo: a conta pode ter sido nomeada uma única vez em outra
  linha/evento e continuar válida ao ser referenciada de novo).

### Pares COSIF

```text
contaBalAnaliticoDebito preenchida
→ contaCosifDebito obrigatória            DRO001441

contaBalAnaliticoCredito preenchida
→ contaCosifCredito obrigatória           DRO001442
```

Regras inversas também têm código oficial na planilha de críticas de
pré-processamento (linhas 32-33, texto oficial: "Verifica, nos casos em
que sejam devidos lançamentos no campo contaCosifDebito/Credito, se há
preenchimento do campo contaBalAnaliticoDebito/Credito correspondente"):

```text
contaCosifDebito preenchida
→ contaBalAnaliticoDebito obrigatória     DRO001443

contaCosifCredito preenchida
→ contaBalAnaliticoCredito obrigatória    DRO001444
```

O formato COSIF será validado como 8 ou 10 dígitos. O programa não confirmará
existência ou adequação oficial da conta.

## 14. Regra da tabela plana

Cada linha gera:

```text
no máximo uma probabilidade
no máximo uma contabilização
```

Não haverá cruzamento automático nem produto cartesiano.

| Linha | Probabilidade | Contabilização |
|---:|---|---|
| 2 | PR | 1 |
| 3 | PO | 2 |
| 4 | RE | 3 |
| 5 | vazia | 4 |

Contabilizações idênticas em linhas diferentes serão preservadas, pois podem
representar lançamentos reais distintos.

## 15. Cálculos por evento

```text
totalPerdaEfetiva = soma(valorPerdaEfetiva)
totalProvisao     = soma(valorProvisao)
totalRecuperado   = soma(valorRecuperacao)
```

`valorTotalRisco` será gerado somente para contingência avaliada
individualmente **e** cujo valor calculado atinja o piso de
R$10.000.000,00 (Instruções de Preenchimento 12/2020, item "k) Valor
Total em Risco da Contingência": *"O valor mínimo para um evento ser
incluído no campo valor total em risco de contingência é
R$10.000.000,00 (dez milhões de reais). Caso contrário, ele não deve ser
informado"* — regra distinta do limiar de individualização por "risco
não coberto" da seção 16, mesmo tendo hoje o mesmo valor numérico):

```text
tipoAvaliacao = I
+ (totalProvisao + soma(valorRisco)) >= 10.000.000,00
→ valorTotalRisco = totalProvisao + soma(valorRisco)
senão
→ valorTotalRisco omitido (mesmo com tipoAvaliacao = I)
```

Para `M` e `NA`, `valorTotalRisco` também será omitido. Não será criado
`valorTotalRisco="0.00"` quando o atributo não for aplicável.

### Convenção de sinal dos totais do evento

```text
totalPerdaEfetiva < 0
OU totalProvisao < 0
OU totalRecuperado > 0
OU (valorTotalRisco informado E valorTotalRisco < 0)
→ BASE-SINAL-EVENTO-001
```

Regra local baseada nas Instruções de Preenchimento, avaliada sobre os
totais já calculados do evento agrupado. Reprova qualquer violação de sinal,
inclusive valores entre `-10,00` e `0,00` que não acionam `DRO000011`/
`DRO000012` (seção 18) — as duas críticas coexistem sem se misturar:
`BASE-SINAL-EVENTO-001` cobre qualquer sinal inválido, e `DRO000011`/
`DRO000012` continuam sendo avaliadas separadamente, como críticas oficiais
próprias, pelo limiar específico de `-10,00`.

### DRO001241

```text
valorMaterialidade = totalPerdaEfetiva + COALESCE(valorTotalRisco, 0)

dataOcorrencia >= 2021-01-01
+ valorMaterialidade >= 1.000.000,00
+ descricaoEvento vazia
→ DRO001241
```

O `COALESCE` vale somente para avaliar a crítica e não determina emissão de
zero no XML.

As instruções também relacionam a descrição a perda mais provisão e à origem
do ressarcimento. Essas obrigações semânticas não são executadas no MVP por não
possuírem condição operacional inequívoca igual à crítica fornecida.

Decisão registrada: `DRO001241` é executada diretamente com a fórmula acima,
usando somente a condição inequívoca da crítica oficial. Isso é uma escolha
deliberada deste projeto — não um conflito documental não resolvido — e
significa que a aprovação desta crítica cobre apenas a fórmula de
materialidade, não as extensões semânticas mais amplas das Instruções.

## 16. Individualização e consolidação

Um evento será individualizado quando atender a pelo menos um critério:

```text
totalPerdaEfetiva + totalProvisao >= 1.000,00
OU
valor de risco não coberto >= 10.000.000,00
```

Definição registrada: `valor de risco não coberto` é a soma dos `valorRisco`
das probabilidades do evento — a mesma parcela que a fórmula do `DRO001311`
(seção 15) soma a `totalProvisao` para compor `valorTotalRisco`. `totalProvisao`
é a parte já coberta (provisionada); a soma dos `valorRisco` é a parte ainda
não coberta.

Os demais eventos válidos serão consolidados por `categoriaNivel1`.

Campos do consolidado:

```text
categoriaNivel1Consol
numEventosTotalConsol
numEventosSemestreConsol
perdaEfetivaTotalConsol
perdaEfetivaSemestreConsol
provisaoTotalConsol
provisaoSemestreConsol
```

- quantidades contam `idEvento`, não linhas;
- valores totais somam uma vez por evento;
- valores do semestre vinculam o evento a um único semestre: o da sua
  **primeira** `dataContabilizacao` válida (não "qualquer semestre em que
  o evento tenha alguma contabilização" — um evento recorrente, com
  contabilizações em vários semestres, só conta uma vez, no semestre de
  origem). Quando a primeira contabilização cai dentro do semestre da
  `dataBase`, soma-se o total acumulado de **todas** as contabilizações do
  evento (mesmo espírito de `perdaEfetivaTotalConsol`/`provisaoTotalConsol`,
  mas vinculado a 1 semestre), não só as que caem dentro do período;
- não serão criados eventos consolidados fictícios para satisfazer o XSD.

### Datas de evento posteriores ao período da data-base

`dataOcorrencia`, `dataDescoberta` (quando informada) e toda
`dataContabilizacao` do evento não podem ser posteriores ao último dia do
semestre da `dataBase` (30/06 ou 31/12). Regra local impeditiva
(`BASE-DATA-PERIODO-001` — não há código oficial equivalente, não é
inventado um); só é avaliada quando a `dataBase` já foi validada (seção
7).

## 17. Críticas oficiais de pré-processamento

Tipo oficial de todas: `E — Erro`. Quando executadas e inconsistentes, o
tratamento local será `ERRO IMPEDITIVO`.

### Executadas localmente

| Código | Condição resumida |
|---|---|
| `DRO001001` | `codigoConglomerado` deve existir no snapshot local do UNICAD (`assets/lista_codigos_conglomerados.txt`) |
| `DRO001101` | `codigoConta` deve ser único no bloco de contas internas |
| `DRO001102` | `codigoSistema` deve ser único no bloco de sistemas |
| `DRO001103` | deve existir apenas um evento XML final por `idEvento` |
| `DRO001201` | `dataOcorrencia <= dataDescoberta` quando descoberta informada |
| `DRO001202` | descoberta obrigatória para ocorrência a partir de 2021 |
| `DRO001212` | categoria nível 2 obrigatória para ocorrência a partir de 2021 |
| `DRO001231` | individualizado deve atender ao limiar aplicável |
| `DRO001232` | `abs(totalRecuperado)` não supera perda mais provisão |
| `DRO001233` | risco informado exige natureza `TRI`, `TRA` ou `CIV` |
| `DRO001241` | descrição obrigatória pela fórmula oficial de materialidade |
| `DRO001251` | risco associado obrigatório a partir de 2021 |
| `DRO001252` | indicador socioambiental obrigatório a partir de 2021 |
| `DRO001253` | indicador cibernético obrigatório a partir de 2021 |
| `DRO001301` | avaliação `NA` não aceita provisão diferente de zero |
| `DRO001302` | avaliação `I/M` exige tratamento coerente da provisão |
| `DRO001311` | risco total igual a provisão mais soma dos riscos |
| `DRO001312` | avaliação individual a partir de 2021 exige probabilidade |
| `DRO001313` | avaliação massificada não aceita probabilidade |
| `DRO001314` | soma dos riscos deve ser positiva no contexto aplicável |
| `DRO001321` | sistema do evento deve existir no bloco de sistemas |
| `DRO001401` | conta interna de débito deve existir no bloco de contas |
| `DRO001402` | conta interna de crédito deve existir no bloco de contas |
| `DRO001411` | recuperação deve ser menor ou igual a zero |
| `DRO001421` | recuperação efetiva a partir de 2021 exige fonte `S` ou `O` |
| `DRO001431` | conta COSIF de débito deve existir no cadastro oficial COSIF (`assets/lista_COSIF_validas.txt`) |
| `DRO001432` | conta COSIF de crédito deve existir no cadastro oficial COSIF (`assets/lista_COSIF_validas.txt`) |
| `DRO001441` | conta interna de débito exige conta COSIF de débito |
| `DRO001442` | conta interna de crédito exige conta COSIF de crédito |
| `DRO001443` | conta COSIF de débito exige conta interna de débito (seção 13) |
| `DRO001444` | conta COSIF de crédito exige conta interna de crédito (seção 13) |
| `DRO001451` | evento não exclusivamente de risco exige campos contábeis |
| `DRO001452` | evento exclusivamente de risco não deve ter contabilização |

Total: 33 críticas oficiais de pré-processamento executadas localmente.

### Não executadas

| Código | Motivo |
|---|---|
| `DRO001002` | depende das bases Bacen/UNICAD |

Essa crítica não será registrada como aprovada ou reprovada. O relatório
indicará apenas que a validação externa não faz parte do escopo.

`DRO001001` deixou de fazer parte desta lista: passou a ser executada
contra um snapshot local do cadastro UNICAD (não uma consulta em tempo
real), ver seção "Executadas localmente" acima.

## 18. Críticas oficiais de pós-processamento

### Executadas localmente

| Código | Tipo oficial | Condição resumida |
|---|---|---|
| `DRO000001` | Inconsistência | média semestral consolidada maior que 1.000 |
| `DRO000002` | Inconsistência | média total consolidada maior que 1.000 |
| `DRO000003` | Inconsistência | contingência individual a partir de 2021 sem probabilidades |
| `DRO000004` | Inconsistência | `PR` com `totalProvisao = 0` |
| `DRO000005` | Inconsistência | `PO/RE` com `valorRisco = 0` |
| `DRO000009` | Inconsistência | primeira contabilização após 01/01/2021 sem categoria nível 2 |
| `DRO000010` | Inconsistência | contabilização anterior à descoberta |
| `DRO000011` | Inconsistência | `totalPerdaEfetiva < -10` |
| `DRO000012` | Inconsistência | `totalProvisao < -10` |
| `DRO000013` | Inconsistência | `totalRecuperado > 0` |
| `DRO000014` | Inconsistência | recuperação em módulo supera perda mais provisão |
| `DRO000015` | Inconsistência | totais diferem da soma das contabilizações |
| `DRO000018` | Inconsistência | perda total consolidada menor que `-10` |
| `DRO000019` | Inconsistência | provisão total consolidada menor que `-10` |
| `DRO000021` | Inconsistência | categorias nível 1 e 2 incompatíveis |
| `DRO000023` | Inconsistência | saldo acumulado de perda fica negativo |
| `DRO000024` | Esclarecimento | saldo acumulado de provisão fica negativo |
| `DRO000032` | Inconsistência | `categoriaNivel1` em `1` ou `2` (fraude interna/externa) com `totalProvisao > 0` |

- `Inconsistência` será tratada como `ERRO IMPEDITIVO`;
- `Esclarecimento` será tratado como `AVISO`;
- lançamentos na mesma data serão avaliados pelo saldo do fechamento diário,
  sem inventar uma ordem intradiária;
- `DRO000021` usa a convenção verificada diretamente no XSD 06/2025
  (`tipoCategoriaNivel2`, enumeração `11|12|21|22|31|32|33|41|42|43|44|45|
  51|61|71|81|82|83|84|85|86`): o primeiro dígito de `categoriaNivel2`
  corresponde ao `categoriaNivel1`. Incompatível quando o primeiro dígito
  de `categoriaNivel2` não é igual a `categoriaNivel1`. A validação XSD
  (seção 20) continua sendo o crivo definitivo sobre os códigos em si
  (inclusive se o valor pertence à enumeração);
- saldo acumulado (`DRO000023`/`DRO000024`) é por `idEvento`: as
  contabilizações do evento são agrupadas por `dataContabilizacao` (mesma
  data soma antes de acumular), ordenadas cronologicamente, e o saldo
  corre de `valorPerdaEfetiva` (`DRO000023`) e de `valorProvisao`
  (`DRO000024`) fechamento a fechamento.

### Não executadas

```text
DRO000016
DRO000017
DRO000022
DRO000026
DRO000027
DRO000028
DRO000029
DRO000030
```

Dependem de histórico da data-base anterior, fora do escopo desta
homologação.

Total: 18 críticas de pós-processamento locais e 8 fora do escopo desta
homologação.

`DRO000032` (categorias 1/2 = fraude interna/externa, convenção Basileia
II já usada em `DRO000021`) foi confirmada diretamente na planilha
oficial de críticas de pós-processamento (linha 27: *"categoriaNivel1 = 1
ou 2 e totalProvisao > 0"*) — não depende de nenhuma tabela externa de
códigos de fraude; essa condição já está pronta na própria planilha. A
crítica se aplica a todo evento agrupado consistente, individualizado ou
não: o par `categoriaNivel1`/`totalProvisao` de um evento é o mesmo dado
de origem em ambos os casos, e a condição oficial não recorta por bloco
de saída do XML.

## 19. Regras locais principais

| Código | Regra |
|---|---|
| `XLSX-001` | arquivo ausente, inválido ou ilegível |
| `XLSX-ABA-001` | aba obrigatória ausente |
| `XLSX-COL-001` | coluna obrigatória ausente |
| `XLSX-COL-002` | cabeçalho duplicado ou ambíguo |
| `XLSX-BASE-001` | aba `Base` sem nenhuma linha de dados |
| `XLSX-CAB-002` | aba `Cabecalho` sem nenhuma linha, ou com mais de uma linha de dados |
| `BASE-OBR-001` | célula sempre obrigatória vazia |
| `BASE-NULO-001` | marcador inválido como `N/A`, `NULL`, `-` ou `*` |
| `BASE-AGR-001` | conflito entre campos de nível do mesmo evento |
| `BASE-CONT-001` | natureza da contingência incompatível com avaliação |
| `BASE-SIS-001` | mesmo sistema associado a nomes diferentes |
| `BASE-CONTA-001` | mesma conta associada a nomes diferentes |
| `BASE-PROB-001` | probabilidade e valor de risco incompletos |
| `BASE-PROB-002` | probabilidade informada para avaliação `NA` |
| `BASE-PROB-003` | probabilidade repetida ou mais de três no evento |
| `BASE-SINAL-CONT-001` | perda contabilizada (`valorPerdaEfetiva`) informada com sinal negativo |
| `BASE-CONT-OBR-001` | contabilização iniciada sem `dataContabilizacao`, `valorPerdaEfetiva`, `valorProvisao` ou `valorRecuperacao` |
| `BASE-SINAL-EVENTO-001` | totais do evento agrupado violam a convenção de sinal |
| `BASE-COSIF-FORM-001` | COSIF não possui 8 ou 10 dígitos |
| `BASE-REC-FONTE-001` | fonte `S/O` sem recuperação efetiva |
| `BASE-CONT-SEM-MOV-001` | contabilização com os três movimentos zerados |
| `BASE-CAB-CODDOC-001` | `codigoDocumento` ausente, inválido ou diferente de `"5050"` |
| `BASE-CAB-DATABASE-001` | `dataBase` ausente ou inválida (formato, mês fora de `{06,12}`, ou anterior a `2020-12`) |
| `BASE-CAB-CONGLOMERADO-001` | `codigoConglomerado` ausente, inválido ou fora do padrão `C` + 7 dígitos |
| `BASE-CAB-CNPJ-001` | `cnpj` ausente ou inválido |
| `BASE-CAB-REMESSA-001` | `tipoRemessa` ausente, inválido ou fora de `{I,S}` |
| `BASE-CAB-PROVACUM-001` | `opcaoPorProvisaoAcumulada` ausente, inválida ou fora de `{S,N}` |
| `BASE-DATA-PERIODO-001` | `dataOcorrencia`/`dataDescoberta`/`dataContabilizacao` posterior ao período da `dataBase` |
| `BASE-IDEVENTO-COLISAO-001` | dois ou mais `idEvento` originais distintos colidem no mesmo valor normalizado |
| `CONS-CALC-001` | dados insuficientes para calcular consolidados |
| `XSD-001` | XML incompatível com o XSD 06/2025 |
| `XML-TEC-001` | falha técnica ao construir o XML em memória |
| `XSD-TEC-001` | falha técnica ao carregar ou compilar o XSD 06/2025 |
| `ARQ-TEC-001` | falha técnica ao gravar o arquivo XML final em disco |
| `TECH-001` | falha técnica inesperada |

`BASE-CONTA-PAR-001`/`002` foram renomeadas para os códigos oficiais
`DRO001443`/`DRO001444` (seção 13/17) — deixaram de ser regras locais.

`XML-TEC-001`/`XSD-TEC-001`/`ARQ-TEC-001` (seção 20/22) atribuem a falha
a `status_xsd`, não a `status_local`: a validação local dos dados já
tinha terminado com sucesso antes da tentativa de construir/validar/
gravar o XML, então `status_local` permanece `APROVADO` — só
`status_xsd` passa a aceitar um 4º valor, `FALHA TÉCNICA`, além dos já
existentes `APROVADO`/`REPROVADO`/`NÃO EXECUTADO`.

## 20. XML

Estrutura obrigatória:

```text
documento
├── eventosIndividualizados
│   └── evento (1 ou mais)
│       ├── probabilidadesPerdas (opcional)
│       │   └── probabilidadePerda (até 3)
│       └── contabilizacoes (opcional)
│           └── contabilizacao (1 ou mais)
├── eventosConsolidados
│   └── eventoConsolidado (1 a 8)
├── sistemasOrigem
│   └── sistema (1 ou mais)
└── contasSubtitulosInternos
    └── conta (1 ou mais)
```

- atributos opcionais vazios serão omitidos;
- decimais terão ponto e duas casas;
- datas terão formato ISO;
- não haverá elementos ou valores fictícios;
- o XML será construído em memória antes de ser salvo;
- o arquivo final será salvo somente quando não houver erro impeditivo e o XSD
  estiver aprovado.

## 21. Relatório XLSX

O relatório terá somente duas abas.

### Aba `Resumo`

#### Tabela Resultado

| Resultado da validação | Status possível |
|---|---|
| Validação local | `APROVADO`, `REPROVADO` ou `FALHA TÉCNICA` |
| Validação XSD | `APROVADO`, `REPROVADO`, `NÃO EXECUTADO` ou `FALHA TÉCNICA` |

`FALHA TÉCNICA` na validação XSD sinaliza um problema técnico (XSD
ausente/corrompido, falha ao construir o XML ou ao gravar o arquivo
final), não um problema nos dados — a validação local pode continuar
`APROVADO` nesse caso.

Decisão revista: o relatório usa formatação visual (título, cabeçalhos de
seção, cores de destaque por status/gravidade, tabela com faixas
zebradas, congelamento de cabeçalho), espelhando o padrão do relatório do
projeto anterior (`xlsx_reporter.py`). O texto do status continua sendo o
valor por extenso (`APROVADO`, `REPROVADO` etc.); a cor é um reforço
visual, não substitui o texto.

#### Tabela Indicadores

| Indicador | Definição |
|---|---|
| Total de inconsistências | total de linhas da aba `Inconsistencias` |
| Regras com inconsistência | quantidade de códigos distintos |
| Eventos com inconsistência | quantidade de `idEvento` distintos afetados |
| Erros impeditivos | ocorrências que bloqueiam a validação |
| Avisos | ocorrências que exigem análise sem bloquear |
| Erros XSD | ocorrências da etapa de validação XSD |

Um erro XSD também integra o total e os erros impeditivos; o indicador
específico apenas destaca sua origem.

### Aba `Inconsistencias`

Colunas:

```text
Etapa
Tipo
Linha(s) da planilha
idEvento
Campo(s)
Código da regra
Descrição da regra
Detalhe da inconsistência
```

Etapas padronizadas:

```text
Estrutura da planilha
Normalização
Agrupamento e cálculos
Pré-processamento
Pós-processamento
Validação XSD
```

Tipos:

```text
ERRO IMPEDITIVO
AVISO
FALHA TÉCNICA
```

A aba mostrará somente problemas. Regras aprovadas não gerarão linhas.

## 22. Saídas

```text
DRO_5050_AAAA-MM.xml
Relatorio_DRO_5050_AAAA-MM.xlsx
```

- o relatório será gerado sempre que tecnicamente possível;
- o XML final será gerado somente quando aprovado localmente e no XSD;
- arquivos existentes não serão sobrescritos: se `DRO_5050_AAAA-MM.xml` e/ou
  `Relatorio_DRO_5050_AAAA-MM.xlsx` já existirem na pasta de saída, a nova
  execução grava `..._1`, `..._2` etc. (o primeiro sufixo livre), mantendo
  o mesmo número para o XML e o relatório de uma mesma execução;
- quando a `dataBase` não puder ser determinada (planilha estruturalmente
  inválida) ou for inválida (seção 7), o nome técnico do relatório usa o
  sufixo `SEM_DATA_BASE` em vez de tentar formatar uma data-base
  inexistente/inválida (ex.: `Relatorio_DRO_5050_SEM_DATA_BASE.xlsx`) —
  nesse caso nenhum XML é gerado;
- o XML final é gravado de forma atômica: escrito primeiro num arquivo
  temporário (`<nome>.xml.tmp`) e só então promovido ao nome final via
  rename atômico do sistema operacional — uma falha no meio da gravação
  (disco cheio etc.) nunca deixa um arquivo parcial no nome final, e o
  temporário é removido automaticamente se a gravação falhar;
- falhas técnicas ao construir o XML, carregar/compilar o XSD ou gravar o
  arquivo final não derrubam o processo: são capturadas, sinalizadas em
  `status_xsd = FALHA TÉCNICA` com o código correspondente
  (`XML-TEC-001`/`XSD-TEC-001`/`ARQ-TEC-001`, seção 19) e o relatório
  ainda é gerado normalmente;
- os artefatos serão gravados diretamente na pasta escolhida na interface.

## 23. Testes mínimos

Cada crítica local terá, quando aplicável:

1. caso aprovado;
2. caso inconsistente;
3. caso não aplicável;
4. caso com valor ausente ou inválido.

Testes integrados mínimos:

- planilha de homologação produz XML válido no XSD;
- ausência de cada aba obrigatória;
- ausência e duplicidade de colunas;
- conflito entre linhas do mesmo evento;
- três probabilidades válidas e quarta probabilidade inválida;
- evento com probabilidades e contabilizações sem multiplicação;
- evento somente de risco sem bloco contábil;
- contabilização integralmente zerada;
- sistema ou conta repetidos com nomes conflitantes;
- erro XSD relacionado ao campo ou evento quando possível;
- relatório gerado em execução aprovada e reprovada;
- interface permanece responsiva durante a conversão.

## 24. Limites assumidos

- a matriz representa todas as regras de presença e obrigatoriedade adotadas no
  MVP, não todas as obrigações semânticas possíveis das instruções;
- não há confirmação externa de conglomerado, `idBacen` ou conta COSIF;
- não há comparação com documentos anteriores;
- não há interpretação automática do conteúdo textual de `descricaoEvento`;
- não há suporte aos campos e blocos introduzidos nas instruções 12/2026;
- o projeto não inventa dados para produzir um XML estruturalmente válido.

## 25. Roadmap

1. criar a estrutura mínima do novo projeto;
2. implementar leitura e validação estrutural das duas abas;
3. implementar normalização e modelos simples;
4. implementar agrupamento, probabilidades, contabilizações e referências;
5. implementar as 28 críticas locais de pré-processamento;
6. implementar consolidação e as 18 críticas locais de pós-processamento;
7. implementar XML e validação XSD;
8. implementar relatório de duas abas;
9. implementar a interface no formato atual;
10. executar testes unitários e homologação ponta a ponta.

O trabalho de implementação somente deve começar depois da aprovação deste
contrato funcional.
