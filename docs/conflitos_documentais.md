# Conflitos documentais — Documento 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `docs/conflitos_documentais.md`  
**Etapa:** 1.4 — Registro de conflitos documentais  
**Objetivo:** registrar divergências, ambiguidades, erros tipográficos e incompatibilidades entre os XSDs, as instruções de preenchimento, o modelo XML, o exemplo XML e as críticas oficiais.

---

## 1. Princípio geral

O conversor não deverá resolver divergências de forma silenciosa.

Toda divergência identificada deverá possuir:

- código interno;
- fontes envolvidas;
- descrição objetiva;
- impacto;
- decisão provisória;
- status;
- condição para encerramento.

### 1.1. Ordem de precedência

Para implementação, será utilizada esta ordem:

1. **XSD**, para nomes XML, estrutura, tipos, formatos e cardinalidades;
2. **instruções de preenchimento**, para regras de negócio e obrigatoriedades condicionais;
3. **críticas de pré-processamento**;
4. **críticas de pós-processamento**;
5. **modelo PDF e XML de exemplo**, somente como referência.

Essa precedência não significa que uma exigência das instruções possa ser descartada apenas porque não aparece no XSD. Quando isso ocorrer, haverá conflito impeditivo até existir uma combinação documental compatível.

---

## 2. Classificação dos conflitos

| Classificação | Significado |
|---|---|
| `IMPEDITIVO` | Impede classificar o arquivo como `APTO PARA ENVIO` |
| `ESTRUTURAL` | Afeta nome, elemento, atributo, tipo ou cardinalidade XML |
| `REGRA_NEGOCIO` | Afeta obrigatoriedade, domínio ou cálculo |
| `TIPOGRAFICO` | Provável erro de digitação ou representação ilustrativa |
| `METADADO` | Divergência em título, versão, comentário ou data interna do arquivo |
| `DEPENDENCIA_EXTERNA` | Só pode ser resolvido com base externa ou histórico |
| `INFORMATIVO` | Não bloqueia, mas deve ser documentado para evitar interpretação incorreta |

---

# 3. Resumo dos conflitos

| Código | Classificação | Tema | Gravidade | Status |
|---|---|---|---|---|
| `CONF-001` | IMPEDITIVO / ESTRUTURAL | Instruções 12/2026 não suportadas pelo XSD 06/2025 | ERRO IMPEDITIVO | ABERTO |
| `CONF-002` | REGRA_NEGOCIO / ESTRUTURAL | Domínio de `tipoAvaliacao` | ERRO IMPEDITIVO para `IE`/`ME` | ABERTO |
| `CONF-003` | REGRA_NEGOCIO / ESTRUTURAL | Domínio de `naturezaContingencia` | ERRO IMPEDITIVO para `OUT` | ABERTO |
| `CONF-004` | ESTRUTURAL | Campo `idEventoAgregador` ausente no XSD | ERRO IMPEDITIVO | ABERTO |
| `CONF-005` | ESTRUTURAL | Novos campos do consolidado ausentes no XSD | ERRO IMPEDITIVO | ABERTO |
| `CONF-006` | ESTRUTURAL | Bloco de eventos excluídos ausente no XSD | ERRO IMPEDITIVO | ABERTO |
| `CONF-007` | REGRA_NEGOCIO | Domínio de `motivoExclusao`: `1-6` versus `1-8` | ERRO IMPEDITIVO | ABERTO |
| `CONF-008` | ESTRUTURAL / TIPOGRAFICO | Nome do campo socioambiental | ERRO IMPEDITIVO na nova versão | ABERTO |
| `CONF-009` | TIPOGRAFICO | `opcapPorProvisaoAcumulada` no leiaute 12/2026 | AVISO DOCUMENTAL | TRATAMENTO DEFINIDO |
| `CONF-010` | TIPOGRAFICO | `codEventoOrigem` versus `codigoEventoOrigem` | AVISO DOCUMENTAL | TRATAMENTO DEFINIDO |
| `CONF-011` | TIPOGRAFICO | `probabilidadesPerda` versus `probabilidadesPerdas` | AVISO DOCUMENTAL | TRATAMENTO DEFINIDO |
| `CONF-012` | TIPOGRAFICO | `contaSubtitulosInternos` versus `contasSubtitulosInternos` | AVISO DOCUMENTAL | TRATAMENTO DEFINIDO |
| `CONF-013` | TIPOGRAFICO / ESTRUTURAL | Fechamento prematuro de `eventoConsolidado` no leiaute 12/2026 | AVISO DOCUMENTAL | TRATAMENTO DEFINIDO |
| `CONF-014` | INFORMATIVO | Modelo PDF usa expressões diferentes das restrições reais do XSD | AVISO DOCUMENTAL | TRATAMENTO DEFINIDO |
| `CONF-015` | METADADO | Comentário interno do XSD 06/2025 permanece com dados de 2021 | AVISO DOCUMENTAL | ABERTO |
| `CONF-016` | REGRA_NEGOCIO | Unicidade de `idEvento` removida do XSD 06/2025 | AVISO TÉCNICO | TRATAMENTO DEFINIDO |
| `CONF-017` | DEPENDENCIA_EXTERNA | Validação UNICAD não executável localmente | `DRO001001` EXECUTADA (snapshot local); `DRO001002` REGRA NÃO EXECUTADA | PARCIALMENTE TRATADO |
| `CONF-018` | DEPENDENCIA_EXTERNA | Validação da existência/adequação COSIF | REGRA NÃO EXECUTADA ou PARCIAL | ABERTO |
| `CONF-019` | DEPENDENCIA_EXTERNA | Críticas históricas sem data-base anterior | REGRA NÃO EXECUTADA | ABERTO |
| `CONF-020` | ESTRUTURAL / DADOS | Bloco consolidado obrigatório sem aba própria | ERRO IMPEDITIVO se os dados forem insuficientes | ABERTO |
| `CONF-021` | INFORMATIVO | XML de exemplo é válido, mas representa somente o leiaute legado | INFORMAÇÃO | CONFIRMADO |
| `CONF-022` | REGRA_NEGOCIO | Limiar de obrigatoriedade de `descricaoEvento` | REGRA NÃO EXECUTADA para `DRO001241` | ABERTO |

---

# 4. Conflitos impeditivos da versão 12/2026

## `CONF-001` — Instruções 12/2026 não suportadas pelo XSD 06/2025

### Fontes envolvidas

- Instruções de preenchimento válidas a partir da data-base 12/2026;
- XSD identificado como válido a partir da data-base 06/2025.

### Descrição

As instruções 12/2026 acrescentam campos, domínios e um novo bloco que não estão declarados no XSD 06/2025 fornecido.

Entre as diferenças:

```text
tipoAvaliacao = IE ou ME
naturezaContingencia = OUT
idEventoAgregador
novos campos de eventos consolidados
eventosIndividualizadosExcluidos
dataExclusao
motivoExclusao
```

### Impacto

Existem dois resultados igualmente inadequados:

1. incluir os campos da instrução nova e falhar na validação XSD;
2. omitir os campos apenas para passar no XSD e deixar de atender à instrução nova.

### Decisão provisória

Para:

```text
dataBase >= 2026-12
```

usar o perfil:

```text
DRO_2026_12_PRESUMIDA
```

e aplicar:

```text
status_final máximo = NÃO APTO PARA ENVIO
```

O sistema poderá gerar XML diagnóstico, mas não deverá classificá-lo como apto.

### Encerramento

Somente após o fornecimento e a análise de um XSD compatível com as instruções 12/2026.

---

## `CONF-002` — Domínio de `tipoAvaliacao`

### Instruções 12/2020 e XSDs fornecidos

```text
I
M
NA
```

### Instruções 12/2026

```text
I
IE
M
ME
NA
```

### Conflito

O XSD 06/2025 aceita somente:

```text
I|M|NA
```

Logo, `IE` e `ME` falhariam na validação XSD.

### Decisão provisória

- até `2026-06`: aceitar apenas `I`, `M` e `NA`;
- a partir de `2026-12`: reconhecer `IE` e `ME` na análise da instrução, mas bloquear a geração como apta com o XSD atual;
- nunca transformar `IE` em `I` nem `ME` em `M`.

### Motivo

Essa transformação eliminaria informação regulatória e alteraria o significado do dado.

---

## `CONF-003` — Domínio de `naturezaContingencia`

### XSDs fornecidos

```text
TRI
TRA
CIV
NA
```

### Instruções 12/2026

```text
TRI
TRA
CIV
OUT
NA
```

### Conflito

O valor `OUT` é exigido pela instrução nova em determinadas situações, mas não é aceito pelo XSD 06/2025.

### Decisão provisória

- não converter `OUT` em `NA`;
- não omitir o campo para fazer o XML passar;
- registrar `CONF-003`;
- classificar o resultado como `NÃO APTO PARA ENVIO`.

---

## `CONF-004` — `idEventoAgregador` ausente no XSD

### Instruções 12/2026

O campo é opcional e permite identificar eventos com a mesma causa raiz.

### XSD 06/2025

O atributo não existe em `tipoEvento`.

### Impacto

Um evento que precise informar a agregação não consegue cumprir simultaneamente as instruções 12/2026 e o XSD 06/2025.

### Decisão provisória

- ler e preservar o valor da planilha;
- validar conflitos do grupo internamente;
- não descartá-lo;
- não produzir resultado `APTO` enquanto o XSD compatível não estiver disponível.

---

## `CONF-005` — Novos campos de eventos consolidados

### Instruções 12/2026

Acrescentam:

```text
provisaoTotalCIV
provisaoTotalTRA
provisaoTotalTRI_CONST
provisaoTotalTRI_OUTROS
provisaoTotalOUTROS
recuperacaoTotalConsol
recuperacaoSemestreConsol
```

### XSD 06/2025

O tipo `eventoConsolidado` contém somente os campos do leiaute anterior:

```text
categoriaNivel1Consol
numEventosTotalConsol
numEventosSemestreConsol
perdaEfetivaTotalConsol
perdaEfetivaSemestreConsol
provisaoTotalConsol
provisaoSemestreConsol
```

### Decisão provisória

Os novos campos poderão ser calculados internamente para relatório, mas não haverá XML 12/2026 apto até existir XSD compatível.

---

## `CONF-006` — Bloco de eventos excluídos ausente no XSD

### Instruções 12/2026

Criam o bloco:

```xml
<eventosIndividualizadosExcluidos>
    <evento
        idEvento="..."
        dataExclusao="..."
        motivoExclusao="..."/>
</eventosIndividualizadosExcluidos>
```

### XSD 06/2025

Não declara esse elemento.

### Impacto

A inclusão do bloco gera falha XSD. A omissão pode violar a instrução nova quando existirem eventos que deixaram de ser individualizados.

### Decisão provisória

Bloquear `APTO` para a versão nova quando o bloco for aplicável.

---

## `CONF-007` — Domínio de `motivoExclusao`

### Instruções 12/2026 — Anexo IV

Apresenta códigos:

```text
1
2
3
4
5
6
7
8
```

### Instruções 12/2026 — Leiaute ilustrativo

Apresenta:

```text
motivoExclusao="[1-6]{1}"
```

### Conflito

Os motivos:

```text
7 — Desagregação de eventos
8 — Outros
```

existem no Anexo IV, mas seriam rejeitados pela expressão ilustrativa `[1-6]`.

### Decisão provisória

- o domínio não será tratado como definitivamente resolvido;
- não limitar os dados internamente a `1-6`;
- preservar códigos `7` e `8` quando informados;
- não gerar bloco de exclusões com o XSD 06/2025;
- aguardar XSD compatível ou esclarecimento oficial.

### Precedência provisória

Para regra de negócio, o Anexo IV é mais detalhado que o desenho ilustrativo. Porém, isso não resolve a ausência de suporte no XSD.

---

# 5. Conflitos de nomes XML

## `CONF-008` — Campo socioambiental

### Nomes encontrados

Na planilha:

```text
ligacaoRiscoSocioambiental
```

Nos XSDs fornecidos:

```text
ligadoRiscoSocioAmbiental
```

Na descrição de campo das instruções 12/2026:

```text
ligadoRSAC
```

No leiaute ilustrativo das próprias instruções 12/2026:

```text
ligadoRiscoSocioAmbiental
```

### Conflito

A instrução nova utiliza dois nomes diferentes para o mesmo conceito.

### Decisão provisória

Para versões confirmadas pelos XSDs fornecidos:

```text
Excel: ligacaoRiscoSocioambiental
XML:   ligadoRiscoSocioAmbiental
```

Para 12/2026:

- manter o alias de entrada;
- não adotar `ligadoRSAC` no XML sem confirmação do XSD da nova versão;
- registrar o conflito.

---

## `CONF-009` — `opcapPorProvisaoAcumulada`

### Leiaute ilustrativo 12/2026

```text
opcapPorProvisaoAcumulada
```

### XSDs e instruções descritivas

```text
opcaoPorProvisaoAcumulada
```

### Avaliação

A forma `opcap` aparenta ser erro tipográfico no desenho do leiaute.

### Decisão

Usar:

```text
opcaoPorProvisaoAcumulada
```

conforme os XSDs.

### Status

```text
TRATAMENTO DEFINIDO
```

---

## `CONF-010` — `codEventoOrigem`

### Leiaute ilustrativo 12/2026

```text
codEventoOrigem
```

### XSDs e descrição detalhada

```text
codigoEventoOrigem
```

### Decisão

Usar:

```text
codigoEventoOrigem
```

### Justificativa

O nome é declarado formalmente pelos XSDs e utilizado na descrição do campo.

---

## `CONF-011` — `probabilidadesPerda`

### Leiaute ilustrativo 12/2026

```text
<probabilidadesPerda>
```

### XSDs fornecidos e modelo legado

```text
<probabilidadesPerdas>
```

### Decisão

Para os XSDs fornecidos, usar:

```text
probabilidadesPerdas
```

O nome da nova versão só poderá ser alterado se um XSD posterior declarar formalmente outra estrutura.

---

## `CONF-012` — `contaSubtitulosInternos`

### Leiaute ilustrativo 12/2026

```text
<contaSubtitulosInternos>
```

### XSDs fornecidos

```text
<contasSubtitulosInternos>
```

### Decisão

Usar:

```text
contasSubtitulosInternos
```

para os XSDs existentes.

---

## `CONF-013` — Fechamento de `eventoConsolidado` no leiaute ilustrativo

### Representação encontrada

O leiaute 12/2026 apresenta fechamento do elemento logo após:

```text
provisaoSemestreConsol="..."/>
```

e mostra depois:

```text
recuperacaoTotalConsol
recuperacaoSemestreConsol
```

fora da abertura do elemento.

### Avaliação

Essa disposição não constitui XML bem-formado para os dois atributos de recuperação e aparenta ser erro de diagramação.

### Decisão

Não utilizar o desenho como fonte executável.

A estrutura futura deverá ser confirmada pelo XSD correspondente.

---

# 6. Diferenças entre o modelo PDF e o XSD

## `CONF-014` — Expressões ilustrativas não equivalem às restrições do XSD

O modelo PDF apresenta várias expressões simplificadas ou tecnicamente diferentes das restrições formais.

### Exemplos

| Campo | Modelo PDF | XSD |
|---|---|---|
| `idEvento` | representação semelhante a `[0-9][A-Z][a-z]{40}` | qualquer sequência alfanumérica entre 1 e 40 caracteres |
| `categoriaNivel2` | representação semelhante a `[11-86]{2}` | enumeração explícita dos códigos permitidos |
| `codSistemaOrigem` | representação semelhante a `[0-9][a-z][A-Z]{10}` | alfanumérico entre 1 e 10 caracteres |
| `codigoEventoOrigem` | representação semelhante a `[0-9][a-z][A-Z]{73}` | alfanumérico entre 1 e 73 caracteres |
| conta interna | `[0-9]{24}` | entre 1 e 24 dígitos |
| quantidades consolidadas | `[0-9]{18}` | entre 1 e 18 dígitos |

### Impacto

Interpretar literalmente o PDF poderia:

- exigir tamanho exato onde o XSD aceita intervalo;
- aceitar categorias inexistentes;
- rejeitar códigos válidos;
- implementar expressões regulares incorretas.

### Decisão

O modelo PDF será usado apenas para compreender a hierarquia visual.

Tipos, formatos e padrões serão obtidos do XSD.

---

# 7. Conflitos e diferenças entre os XSDs

## `CONF-015` — Metadados internos do XSD 06/2025

### Nome externo do arquivo

```text
Esquema de validação válido a partir da data-base 062025.xsd
```

### Comentários internos

O cabeçalho interno permanece indicando:

```text
Versão 1.01
Leiautes por data-base: 12/2020 e seguintes
Atualizado em 15/06/2021
```

### Conflito

O nome externo sugere uma vigência iniciada em 06/2025, mas os metadados internos não foram atualizados.

### Decisão provisória

- usar a vigência informada pelo nome oficial fornecido ao projeto;
- não inferir mudanças além das diferenças efetivamente encontradas no conteúdo;
- registrar o hash do arquivo futuramente;
- manter o conflito aberto até existir confirmação documental adicional.

---

## `CONF-016` — Unicidade de `idEvento`

### XSD 12/2020

Contém:

```xml
<xs:key name="pkidEvento">
    <xs:selector xpath="evento"/>
    <xs:field xpath="@idEvento"/>
</xs:key>
```

### XSD 06/2025

A chave foi removida.

### Instruções e crítica de pré-processamento

Continuam exigindo que o `idEvento` seja único.

### Avaliação

A remoção da chave XSD não significa autorização para IDs repetidos.

### Decisão

Implementar validação local obrigatória:

```text
DRO001103 — unicidade do idEvento
```

O XML não será considerado apto se dois eventos distintos possuírem o mesmo identificador.

---

## 7.1. Alteração confirmada e não conflitante — COSIF

A comparação dos XSDs confirmou:

### XSD 12/2020

```text
conta COSIF = 8 dígitos
```

### XSD 06/2025

```text
conta COSIF = 8 ou 10 dígitos
```

Essa diferença será tratada pela matriz de versões e não constitui conflito entre fontes para a mesma vigência.

---

# 8. Dependências externas e históricas

## `CONF-017` — UNICAD

### Críticas relacionadas

```text
DRO001001 — código do conglomerado
DRO001002 — idBacen ou idInstal
```

### Problema

O conversor local não possui acesso garantido (em tempo real) ao UNICAD.

### Decisão — `DRO001002` (idBacen / idInstal)

Sem integração ou base de referência local disponível:

```text
status = REGRA NÃO EXECUTADA
motivo = Base UNICAD indisponível
```

O sistema poderá validar somente formato e presença.

Nunca deverá declarar que o código existe oficialmente apenas porque possui formato correto.

### Decisão — `DRO001001` (código do conglomerado)

Um snapshot local do cadastro UNICAD passou a ser distribuído junto ao
conversor (`assets/lista_codigos_conglomerados.txt`, carregado por
`src.regulatory_constants.CODIGOS_CONGLOMERADOS_VALIDOS`). Com isso:

```text
status = EXECUTADA (contra o snapshot local, nao contra o UNICAD em tempo real)
função = validar_codigo_conglomerado_unicad (src/rules_pre.py)
```

Isso não é uma consulta online ao UNICAD — é uma comparação contra uma
cópia estática, que pode ficar desatualizada se o cadastro oficial mudar
sem que o arquivo local seja atualizado. A checagem de formato/presença
(`BASE-CAB-CONGLOMERADO-001`) continua sendo aplicada antes, e um erro de
formato não gera adicionalmente `DRO001001` (evita duplicidade).

---

## `CONF-018` — COSIF

### Críticas relacionadas

Incluem validação de contas COSIF e correspondência contábil.

### Problema

O XSD valida somente o formato da conta. Ele não confirma:

- existência oficial;
- vigência;
- natureza da conta;
- adequação ao lançamento;
- correspondência com a conta interna.

### Decisão

Separar:

1. **validação local de formato**, executável;
2. **validação oficial de existência/adequação**, não executada sem base externa;
3. **relação débito/crédito**, executada somente na parte que não dependa de cadastro externo.

---

## `CONF-019` — Críticas que dependem da data-base anterior

### Exemplos

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

### Problema

As quatro abas do Excel atual não contêm o histórico da data-base anterior.

### Decisão

Sem XML, Excel ou base histórica anterior:

```text
status = REGRA NÃO EXECUTADA
motivo = Documento da data-base anterior não fornecido
```

Uma regra não executada não poderá ser registrada como aprovada.

---

# 9. Conflitos relacionados ao arquivo Excel produtivo

## `CONF-020` — Bloco consolidado obrigatório sem aba própria

### Contrato de entrada

O arquivo produtivo conterá somente:

```text
Base
Cabecalho
Sistemas_Origem
Contas_Internas
```

### XSDs fornecidos

Exigem exatamente um bloco:

```text
eventosConsolidados
```

com pelo menos um:

```text
eventoConsolidado
```

### Problema

Sem a aba `Eventos_Consolidados`, o sistema precisa calcular esse bloco pela `Base`.

Isso só é possível se a `Base` contiver todos os eventos necessários, inclusive os que ficam abaixo dos limites de individualização.

### Cenários

#### Cenário A — Base completa

Contém eventos individualizados e eventos que devem ser consolidados.

```text
Resultado: cálculo possível
```

#### Cenário B — Base somente com individualizados

Não contém os eventos abaixo dos limiares.

```text
Resultado: dados insuficientes
```

#### Cenário C — Nenhum evento consolidável

Mesmo que realmente não existam eventos consolidados, o XSD fornecido exige no mínimo um `eventoConsolidado`.

### Decisão implementada

- não criar um evento consolidado fictício com zeros;
- usar a `Base` completa como única fonte;
- classificar depois do agrupamento por `idEvento`;
- registrar `DOC-CONS-001` somente quando não houver candidatos válidos;
- registrar `CONS-CALC-001` quando dados impedirem a classificação ou o cálculo.

`MAP-CONS-001` foi aposentado: a ausência da aba auxiliar é esperada e não é
mais uma ocorrência.

---

# 10. XML de exemplo

## `CONF-021` — Escopo limitado do XML de exemplo

O arquivo:

```text
DRO - Modelo XML do Documento 5050 - Exemplo.xml
```

foi validado com sucesso contra:

```text
XSD 12/2020
XSD 06/2025
```

### Interpretação

Isso confirma que o exemplo fornecido é estruturalmente compatível com os dois XSDs atuais.

### Limitação

O exemplo possui:

```text
dataBase = 2021-12
```

e representa somente o leiaute legado. Ele não comprova a estrutura das instruções 12/2026.

### Decisão

Usá-lo para:

- teste de infraestrutura do validador;
- referência de hierarquia;
- teste de regressão do leiaute legado.

Não usá-lo para:

- preencher valores ausentes;
- inferir campos da versão 12/2026;
- substituir regras das instruções ou do XSD.

---

# 11. Regras de implementação decorrentes dos conflitos

## 11.1. O sistema nunca deverá

- mudar `IE` para `I`;
- mudar `ME` para `M`;
- mudar `OUT` para `NA`;
- omitir `idEventoAgregador` sem registrar o impacto;
- criar evento consolidado fictício;
- inventar motivo de exclusão;
- assumir existência no UNICAD;
- assumir validade oficial da conta COSIF pelo formato;
- considerar regra histórica aprovada sem histórico;
- usar expressão ilustrativa do PDF no lugar do XSD;
- corrigir silenciosamente nomes conflitantes.

## 11.2. O sistema deverá

- registrar a fonte de cada regra;
- preservar o valor original;
- registrar a decisão provisória aplicada;
- incluir o código do conflito no relatório;
- bloquear `APTO` quando o conflito afetar a conformidade;
- permitir atualização futura sem alterar regras de versões anteriores.

---

# 12. Estrutura sugerida no relatório

Os conflitos aplicáveis a uma execução deverão aparecer na aba:

```text
Conflitos_Documentais
```

Colunas:

| Coluna | Conteúdo |
|---|---|
| `conflitoID` | Código `CONF-xxx` |
| `dataBase` | Data-base da execução |
| `versao` | Perfil selecionado |
| `descricao` | Resumo do conflito |
| `impacto` | Impacto no XML ou validação |
| `decisaoAplicada` | Tratamento utilizado |
| `gravidade` | Gravidade |
| `status` | Aberto, tratamento definido ou encerrado |
| `bloqueiaApto` | `S` ou `N` |

---

# 13. Critério de encerramento

Um conflito somente poderá ser marcado como `ENCERRADO` quando houver:

1. XSD posterior compatível;
2. nova instrução oficial;
3. esclarecimento oficial;
4. base externa oficial disponibilizada;
5. decisão de arquitetura que não contrarie as fontes;
6. teste automatizado que comprove o comportamento.

A resolução deverá registrar:

```text
data da resolução
fonte utilizada
versão afetada
decisão anterior
decisão nova
testes atualizados
```

---

# 14. Pendências para continuidade

| Pendência | Etapa relacionada |
|---|---|
| Criar matriz completa das críticas | 1.3 |
| Confirmar que a `Base` conterá também eventos consolidáveis | Leitor/contrato de entrada |
| Obter XSD compatível com 12/2026 | Versionamento |
| Definir fonte oficial para UNICAD | Validações externas |
| Definir fonte/tabela COSIF aplicável | Validações externas |
| Definir forma de receber a data-base anterior | Pós-processamento |
| Definir política para totais informados versus calculados | Builder e validações |

---

# 15. Estado da etapa

```text
Etapa 1.4 — Conflitos documentais: CONCLUÍDA
Etapa 1.3 — Matriz de críticas e validações: PENDENTE
Próxima etapa lógica recomendada: 1.3
```

---

## `CONF-022` — Limiar de obrigatoriedade de `descricaoEvento`

### Fontes envolvidas

- instruções de preenchimento 12/2020 e 12/2026;
- crítica de pré-processamento `DRO001241`.

### Divergência

As instruções determinam a obrigatoriedade da descrição quando a soma de:

```text
totalPerdaEfetiva + totalProvisao
```

atinge R$ 1.000.000,00.

A crítica `DRO001241`, por outro lado, descreve o confronto usando:

```text
totalPerdaEfetiva + valorTotalRisco
```

### Decisão provisória

Pela ordem de precedência do projeto, a validação local da etapa 5.4 aplica a
regra das instruções com o código interno:

```text
BASE-OBR-DESC-001
```

A crítica oficial `DRO001241` permanece como:

```text
REGRA NÃO EXECUTADA
```

com motivo `CONF-022`, até esclarecimento oficial.

### Impacto

O sistema não combina as duas fórmulas e não aplica a alternativa mais
restritiva de forma silenciosa, pois isso poderia criar falsos erros.

### Encerramento

Após esclarecimento oficial ou publicação de documento que elimine a
divergência.

## CONF-023 — Ordem intradiária das contabilizações

As críticas `DRO000023` e `DRO000024` verificam a existência momentânea de
saldo acumulado negativo usando o valor do lançamento e a
`dataContabilizacao`.

Os arquivos fornecidos não apresentam horário, sequência intradiária ou regra
oficial para ordenar vários lançamentos na mesma data.

**Impacto:** quando o saldo de fechamento do dia é não negativo, mas alguma
ordem possível dos lançamentos deixaria o saldo negativo, a regra é registrada
como `REGRA NÃO EXECUTADA`. O sistema não utiliza arbitrariamente a ordem da
planilha para aprovar ou reprovar a crítica.

## CONF-024 — Sinal positivo versus limite de -R$ 10,00

As instruções de preenchimento determinam que perda e provisão sejam lançadas
com valor positivo. As críticas de pós-processamento `DRO000011` e
`DRO000012`, por outro lado, descrevem inconsistência somente quando o total é
inferior a `-10`.

**Precedência aplicada:** a validação baseada nas instruções continua
reprovando qualquer total negativo por meio de `BASE-SINAL-EVENTO-001`.
Separadamente, `DRO000011` e `DRO000012` mantêm exatamente o limite de `-10`
descrito nas críticas.

**Impacto:** um valor entre `-10,00` e `0,00` pode não reprovar a crítica de
pós-processamento específica, mas continua impedindo a aprovação geral pela
regra de sinal das instruções.


## CONF-025 — Comprimento de `codigoSistema`

As instruções descrevem `codigoSistema` como campo alfanumérico “de 10
caracteres”. Os XSDs, porém, definem `minLength=1` e `maxLength=10`.

**Decisão:** pela precedência documental, são aceitos de 1 a 10 caracteres,
conforme o XSD. O programa não completa códigos curtos com zeros ou outros
caracteres.

## CONF-026 — Caracteres permitidos em `nomeSistema` e `nomeConta`

Os XSDs restringem os nomes ao padrão:

```text
[0-9a-zA-Z ]+
```

As instruções apresentam exemplos com acentos, como “Sistema Jurídico” e
“Sistema de apuração de fraude interna”.

**Decisão:** os nomes são validados pelo padrão do XSD. Acentos e pontuação não
são removidos automaticamente. O valor original é preservado no diagnóstico.

## CONF-027 — Chaves de unicidade dos blocos auxiliares no XSD

Os XSDs declaram `xs:key`, mas os seletores utilizam `codigoSistema` e
`codigoConta`, enquanto os elementos filhos reais são `sistema` e `conta`.

**Impacto:** a validação XSD pode não detectar códigos duplicados nesses
blocos. A aplicação executa explicitamente `DRO001102` e `DRO001101`, conforme
as críticas de pré-processamento, sem depender apenas do mecanismo `xs:key`.

## CONF-028 — Bloco consolidado obrigatório sem fonte produtiva

Os XSDs fornecidos exigem exatamente um bloco `eventosConsolidados`, contendo
de um a oito elementos `eventoConsolidado`.

O contrato produtivo do projeto utiliza somente as abas `Base`, `Cabecalho`,
`Sistemas_Origem` e `Contas_Internas`. A aba adicional
`Eventos_Consolidados` não é fonte de entrada.

A Base é processada por serviços que selecionam eventos abaixo dos dois
limiares, calculam os totais validados e determinam os movimentos do semestre
civil encerrado na `dataBase`.

**Impacto:** quando houver candidatos, o bloco é calculado. Quando todos os
eventos forem individualizados, o XML diagnóstico permanece com o bloco vazio,
registra `DOC-CONS-001` e não inventa categoria ou valores.
