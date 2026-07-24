# Matriz de críticas e validações — Documento 5050

**Projeto:** Conversor XLSX → XML DRO 5050  
**Arquivo:** `docs/matriz_criticas.md`  
**Etapa:** 1.3 — Matriz de críticas e validações  
**Objetivo:** catalogar as críticas oficiais de pré e pós-processamento, separar o que pode ser executado localmente e definir o contrato técnico para implementação e relatório.

---

## 1. Fontes utilizadas

1. `criticas_pre_processamento_5050(1).xlsx`;
2. `criticas_pos_processamento_5050(1).xlsx`;
3. instruções de preenchimento 12/2020;
4. instruções de preenchimento 12/2026;
5. XSD 12/2020;
6. XSD 06/2025;
7. `docs/matriz_versoes.md`;
8. `docs/matriz_campos.md`;
9. `docs/conflitos_documentais.md`.

As descrições oficiais abaixo foram preservadas. Os nomes das funções Python, o escopo técnico e a classificação de executabilidade são decisões de arquitetura do projeto, não novos requisitos regulatórios.

---

## 2. Quantidade de regras catalogadas

| Grupo | Quantidade |
|---|---:|
| Críticas oficiais de pré-processamento | 34 |
| Críticas oficiais de pós-processamento | 26 |
| Total de críticas oficiais | 60 |
| Pré-processamento local | 28 |
| Pré-processamento parcial | 4 |
| Pré-processamento externo | 2 |
| Pós-processamento local | 18 |
| Pós-processamento histórico | 8 |

---

## 3. Estados possíveis de uma regra

| Status | Significado |
|---|---|
| `APROVADA` | Regra aplicável, executada e sem ocorrência |
| `INCONSISTENTE` | Regra executada e uma ou mais ocorrências foram encontradas |
| `NÃO APLICÁVEL` | A condição de entrada da regra não ocorreu |
| `REGRA NÃO EXECUTADA` | Faltou base externa, histórico ou outro requisito |
| `FALHA TÉCNICA` | A função não conseguiu concluir por erro de processamento |

Uma regra não executada nunca deve ser registrada como aprovada.

---

## 4. Gravidade interna

A coluna `Tipo` das fontes oficiais será preservada.

Para o relatório do projeto, será usada inicialmente esta tradução:

| Origem/tipo oficial | Gravidade interna inicial | Bloqueia aptidão local |
|---|---|---|
| Pré-processamento `E` | `ERRO IMPEDITIVO` | Sim, quando executável localmente e inconsistente |
| Pós `Inconsistência` | `ERRO` | Sim, quando executável localmente |
| Pós `Esclarecimento` | `AVISO` | Não automaticamente |
| Dependência indisponível | `REGRA NÃO EXECUTADA` | Não equivale a aprovação |
| Falha XSD | `ERRO IMPEDITIVO` | Sim |

Essa tradução é política de controle do projeto e deverá permanecer configurável.

---

## 5. Classes de executabilidade

| Classe | Definição |
|---|---|
| `LOCAL` | Pode ser executada apenas com as abas do contrato de entrada, o XML gerado e os arquivos oficiais fornecidos |
| `PARCIAL` | Parte da regra é local, mas a conclusão exige cadastro ou interpretação externa |
| `EXTERNA` | Exige UNICAD, base Bacen ou outra base não fornecida |
| `HISTORICA` | Exige a data-base imediatamente anterior ou histórico equivalente |

---

# 6. Críticas oficiais de pré-processamento

**Vigência informada no arquivo:** `jun/21` para todas as regras.  
**Tipo oficial:** `E`.

| criticaID | Tipo | Descrição oficial | Campos principais | Escopo | Classe | Dependência | Resultado sem dependência | Função Python proposta | Vigência |
|---|---|---|---|---|---|---|---|---|---|
| `DRO001001` | `E` | Verifica se o código do conglomerado prudencial existe no Unicad. | `codigoConglomerado` | `DOCUMENTO` | `EXTERNA` | UNICAD | `REGRA NÃO EXECUTADA` | `validar_codigo_conglomerado_unicad` | `jun/21` |
| `DRO001002` | `E` | Verifica se o idBacen (ou idInstal - para os casos de agências localizadas no exterior ) existe nas bases de dados do Bacen. | `idBacen; idInstal` | `EVENTO` | `EXTERNA` | UNICAD/Bacen | `REGRA NÃO EXECUTADA` | `validar_id_bacen_unicad` | `jun/21` |
| `DRO001101` | `E` | Verifica unicidade do campo codigoConta no Bloco 4 - Tabela de Subtítulos de Nível Interno. | `codigoConta` | `CONTA_INTERNA` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_unicidade_codigo_conta` | `jun/21` |
| `DRO001102` | `E` | Verifica unicidade do campo codigoSistema no Bloco 3 - Tabela de Sistemas de Origem. | `codigoSistema` | `SISTEMA_ORIGEM` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_unicidade_codigo_sistema` | `jun/21` |
| `DRO001103` | `E` | Verifica a unicidade do idEvento no documento enviado. | `idEvento` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_unicidade_id_evento` | `jun/21` |
| `DRO001201` | `E` | Verifica, quando informado, se a data de ocorrência é menor ou igual a data de descoberta. | `dataOcorrencia; dataDescoberta` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_ordem_datas_evento` | `jun/21` |
| `DRO001202` | `E` | Verifica se o campo dataDescoberta foi devidamente informado para datas de ocorrência maiores ou iguais a 1.1.2021. | `dataOcorrencia; dataDescoberta` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_obrigatoriedade_data_descoberta` | `jun/21` |
| `DRO001212` | `E` | Verifica a obrigatoriedade de preenchimento da categoriaNivel2 para eventos cuja data de ocorrência forem maiores ou iguais a 1.1.2021 . | `dataOcorrencia; categoriaNivel2` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_obrigatoriedade_categoria_nivel2` | `jun/21` |
| `DRO001231` | `E` | Verifica se o somatório dos campos totalPerdaEfetiva e totalProvisão é maior ou igual a R$ 1 mil. Valores inferiores a esse patamar devem ser informados de forma consolidada. | `totalPerdaEfetiva; totalProvisao` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_limiar_evento_individualizado` | `jun/21` |
| `DRO001232` | `E` | Verifica se o total recuperado (totalRecuperado ) é menor ou igual ao somatório, em valores absolutos, dos campos totalPerdaEfetiva e totalProvisao . | `totalRecuperado; totalPerdaEfetiva; totalProvisao` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_limite_total_recuperado` | `jun/21` |
| `DRO001233` | `E` | Verifica, quando o campo valorTotalRisco é informado, se há informação a respeito da natureza de contingência (tributária, trabalhista e/ou cívil) . | `valorTotalRisco; naturezaContingencia` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_natureza_quando_ha_risco` | `jun/21` |
| `DRO001241` | `E` | Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021 e para eventos cujo somatório do campo totalPerda Efetiva com o campo valorTotalRisco for maior ou igual a R$ 1 milhão, se o campo descricaoEvento foi devidamente preenchido . | `dataOcorrencia; totalPerdaEfetiva; valorTotalRisco; descricaoEvento` | `EVENTO` | `CONFLITO_DOCUMENTAL` | `CONF-022` | `REGRA NÃO EXECUTADA` | `registrar_conflito_descricao_evento` | `jun/21` |
| `DRO001251` | `E` | Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo riscoAssociado foi devidamente preenchido. | `dataOcorrencia; riscoAssociado` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_obrigatoriedade_risco_associado` | `jun/21` |
| `DRO001252` | `E` | Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo ligadoRiscoSocioAmbiental foi devidamente preenchido. | `dataOcorrencia; ligadoRiscoSocioAmbiental` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_obrigatoriedade_risco_socioambiental` | `jun/21` |
| `DRO001253` | `E` | Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo ligadoRIscoCibernetico foi devidamente preenchido. | `dataOcorrencia; ligadoRiscoCibernetico` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_obrigatoriedade_risco_cibernetico` | `jun/21` |
| `DRO001301` | `E` | Para tipoAvaliação igual a "NA", valores de provisão (valorProvisao) não devem ser informados. | `tipoAvaliacao; valorProvisao` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_provisao_para_tipo_na` | `jun/21` |
| `DRO001302` | `E` | Verifica, caso tipoAvaliacao seja igual a "I" ou "M", se valores para totalProvisao e/ou valorProvisao foram devidamente informados. | `tipoAvaliacao; totalProvisao; valorProvisao` | `EVENTO/CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_provisao_para_avaliacao_i_m` | `jun/21` |
| `DRO001311` | `E` | Verifica se o campo valorTotalRisco , quando informado para um dado idEvento , corresponde ao somatório do campo totalProvisao com todos os lançamento informados nos campos valorRisco . | `valorTotalRisco; totalProvisao; valorRisco` | `EVENTO/PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_composicao_valor_total_risco` | `jun/21` |
| `DRO001312` | `E` | Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021 e tipoAvaliacao igual a "I" (individual), se o campo probabilidadePerda foi devidamente preenchido. | `dataOcorrencia; tipoAvaliacao; probabilidadePerda` | `PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_probabilidade_para_avaliacao_individual` | `jun/21` |
| `DRO001313` | `E` | Verifica, quando o tipoAvaliacao for igual a "M" (massificada), a inexistência de informação no campo probabilidade de perda (probabilidadePerda ). Conforme definido, não deve ser informada probabilidade de perda para eventos com tipo de avaliação massificada. | `tipoAvaliacao; probabilidadePerda` | `PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_ausencia_probabilidade_massificada` | `jun/21` |
| `DRO001314` | `E` | Verifica se a soma dos campos valorRisco apresenta resultado maior que zero para o seguinte contexto: a) a data de ocorrência é maior ou igual a 1.1.2021; b) o tipoAvaliacao é igual a "I" (Individualizada); c) a naturezaContingencia é diferente de "NA"; e d) foi informada probabilidadePerda . | `dataOcorrencia; tipoAvaliacao; naturezaContingencia; probabilidadePerda; valorRisco` | `PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_soma_valor_risco_positiva` | `jun/21` |
| `DRO001321` | `E` | Verifica se o código preenchido para identificação do sistema origem (codigoSistemaOrigem ) está devidamente informado no Bloco 3 - Tabela de Sistemas de Origem. | `codSistemaOrigem; codigoSistema` | `EVENTO/SISTEMA_ORIGEM` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_referencia_sistema_origem` | `jun/21` |
| `DRO001401` | `E` | Verifica, nos casos em que o campo contaBalAnaliticoDebito é informado, se a referida conta está devidamente informada no campo codigoConta do Bloco 4 - Tabela de Subtítulos de Nível Interno | `contaBalAnaliticoDebito; codigoConta` | `CONTABILIZACAO/CONTA_INTERNA` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_referencia_conta_debito` | `jun/21` |
| `DRO001402` | `E` | Verifica, nos casos em que o campo contaBalAnaliticoCredito é informado, se a referida conta está devidamente informada no campo codigoConta do Bloco 4 - Tabela de Subtítulos de Nível Interno | `contaBalAnaliticoCredito; codigoConta` | `CONTABILIZACAO/CONTA_INTERNA` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_referencia_conta_credito` | `jun/21` |
| `DRO001411` | `E` | Verifica se o valorRecuperacao é menor ou igual a zero. Por convenção, valores de recuperação devem ser lançados com sinal negativo. | `valorRecuperacao` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_sinal_valor_recuperacao` | `jun/21` |
| `DRO001421` | `E` | Verifica, quando a data de ocorrência for maior ou igual a 1.1.2021, se o campo fonteRecuperacao foi devidamene informado quando há lançamento referente a valor recuperado. | `dataOcorrencia; valorRecuperacao; fonteRecuperacao` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_fonte_recuperacao` | `jun/21` |
| `DRO001431` | `E` | Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifDebito , se foi informada uma conta Cosif válida | `contaCosifDebito` | `CONTABILIZACAO` | `LOCAL` | Nenhuma (cadastro em `assets/lista_COSIF_validas.txt`) | `EXECUTADA` | `validar_conta_cosif_debito` | `jun/21` |
| `DRO001432` | `E` | Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifCredito , se foi informada uma conta Cosif válida. | `contaCosifCredito` | `CONTABILIZACAO` | `LOCAL` | Nenhuma (cadastro em `assets/lista_COSIF_validas.txt`) | `EXECUTADA` | `validar_conta_cosif_credito` | `jun/21` |
| `DRO001441` | `E` | Verifica, nos casos em que o campo contaBalAnaliticoDebito é informado, se há informação preenchida no campo contaCosifDebito correspondente . | `contaBalAnaliticoDebito; contaCosifDebito` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_par_debito_interno_cosif` | `jun/21` |
| `DRO001442` | `E` | Verifica, nos casos em que o campo contaBalAnaliticoCredito é informado, se há informação preenchida no campo contaCosifCredito correspondente . | `contaBalAnaliticoCredito; contaCosifCredito` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_par_credito_interno_cosif` | `jun/21` |
| `DRO001443` | `E` | Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifDebito , se há preenchimento do campo contaBalAnaliticoDebito correspondente. | `contaCosifDebito; contaBalAnaliticoDebito` | `CONTABILIZACAO` | `PARCIAL` | Regra de exigência COSIF | `PARCIAL` + possível `REGRA NÃO EXECUTADA` | `validar_contraparte_interna_debito` | `jun/21` |
| `DRO001444` | `E` | Verifica, nos casos em que sejam devidos lançamentos no campo contaCosifCredito , se há preenchimento do campo contaBalAnaliticoCredito correspondente. | `contaCosifCredito; contaBalAnaliticoCredito` | `CONTABILIZACAO` | `PARCIAL` | Regra de exigência COSIF | `PARCIAL` + possível `REGRA NÃO EXECUTADA` | `validar_contraparte_interna_credito` | `jun/21` |
| `DRO001451` | `E` | Verifica, para os casos que não se referem apenas a lançamentos de risco, se foram devidamente preenchidos os respectivos campos contábeis. Lançamentos que não sejam exclusivamente de risco têm que ter informações relativas às contas contábeis correspondentes. | `valorPerdaEfetiva; valorProvisao; valorRecuperacao; contas internas; contas COSIF` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_campos_contabeis_quando_nao_so_risco` | `jun/21` |
| `DRO001452` | `E` | Verifica a inexistência de informação nos campos de informações contábeis, por indevida, nos casos de um idEvento que contenha lançamentos relativos apenas a risco. Ou seja, não é devida a informação de conta contábil nos casos de um contexto de informações exclusivas a valores em risco. O bloco XML "contabilizacao" não deve ser informado. | `valorRisco; contabilizacoes; contas internas; contas COSIF` | `EVENTO/CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_ausencia_contabilizacao_quando_so_risco` | `jun/21` |

---

# 7. Críticas oficiais de pós-processamento

O arquivo de pós-processamento fornecido não apresenta coluna de vigência. Portanto, a matriz não inventa uma data inicial. A ativação por versão deverá ser confirmada na implementação.

| criticaID | Tipo oficial | Gravidade interna | Descrição oficial | Campos avaliados oficiais | Escopo | Classe | Dependência | Resultado sem dependência | Função Python proposta | Vigência |
|---|---|---|---|---|---|---|---|---|---|---|
| `DRO000001` | Inconsistência | `ERRO` | Verifica, em cada categoria do Bloco 2 - Eventos Consolidados, se a perda bruta acumulada no semestre é, em média, superior ao limite de R$ 1.000,00. | `(perdaEfetivaSemestreConsol + provisaoSemestreConsol) / numEventosSemestreConsol > 1000` | `EVENTO_CONSOLIDADO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_media_semestral_consolidada` | Não informada no arquivo |
| `DRO000002` | Inconsistência | `ERRO` | Verifica, em cada categoria do Bloco 2 - Eventos Consolidados, se a perda bruta acumulada é, em média, superior ao limite de R$ 1.000,00. | `(perdaEfetivaTotalConsol + provisaoTotalConsol) / numEventosTotalConsol > 1000` | `EVENTO_CONSOLIDADO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_media_total_consolidada` | Não informada no arquivo |
| `DRO000003` | Inconsistência | `ERRO` | Contingências passivas ocorridas após 01/01/2021, avaliadas individualmente, sem detalhamento de probabilidade de perda. | `tipoAvaliacao; probabilidadePerda; valorRisco; dataOcorrencia` | `EVENTO/PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_detalhamento_probabilidade_individual` | Não informada no arquivo |
| `DRO000004` | Inconsistência | `ERRO` | Contingências passivas, avaliadas individualmente, com atribuição de perda provável e sem atribuição de provisão. | `tipoAvaliacao = "I" e probabilidadePerda = "PR" e totalProvisao = 0` | `EVENTO/PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_provisao_para_perda_provavel` | Não informada no arquivo |
| `DRO000005` | Inconsistência | `ERRO` | Contingências passivas, avaliadas individualmente, com atribuição de perda possível ou remorta e sem atribuição do valor do risco da contingência. | `tipoAvaliacao = "I" e probabilidadePerda = "PO" ou "RE" e valorRisco = 0` | `EVENTO/PROBABILIDADE` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_valor_risco_para_po_re` | Não informada no arquivo |
| `DRO000009` | Inconsistência | `ERRO` | Eventos posteriores a 01/01/2021 sem atribuição do 2º Nível de Classificação Basileia II. | `min(dataContabilizacao) > 01/01/2021 e categoriaNivel2 = ?` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_categoria_nivel2_pos` | Não informada no arquivo |
| `DRO000010` | Inconsistência | `ERRO` | Eventos com contabilizações anteriores à data de descoberta. | `dataContabilizacao < dataDescoberta` | `EVENTO/CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_contabilizacao_apos_descoberta` | Não informada no arquivo |
| `DRO000011` | Inconsistência | `ERRO` | Eventos com valor total de perda efetiva com sinal negativo. | `totalPerdaEfetiva < -10` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_total_perda_nao_negativo` | Não informada no arquivo |
| `DRO000012` | Inconsistência | `ERRO` | Eventos com valor total de provisão com sinal negativo. | `totalProvisao < -10` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_total_provisao_nao_negativo` | Não informada no arquivo |
| `DRO000013` | Inconsistência | `ERRO` | Eventos com valor total recuperado com sinal positivo. | `totalRecuperado > 0` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_total_recuperado_nao_positivo` | Não informada no arquivo |
| `DRO000014` | Inconsistência | `ERRO` | Eventos com valor total recuperado, em módulo, superior ao valor da perda bruta. | `abs(totalRecuperado) > totalPerdaEfetiva + totalProvisao` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_recuperacao_nao_supera_perda_bruta` | Não informada no arquivo |
| `DRO000015` | Inconsistência | `ERRO` | Inconsistência entre os totais de Perda Efetiva, Provisão ou Valor Recuperado e a soma do bloco de contabilizações. | `totalPerdaEfetiva ≠ soma(valorPerdaEfetiva) ou totalProvisao ≠ soma(valorProvisao) ou totalRecuperado ≠ soma(valorRecuperado)` | `EVENTO/CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_totais_contra_contabilizacoes` | Não informada no arquivo |
| `DRO000016` | Inconsistência | `ERRO` | Existência de eventos que não estão informados na data-base e que foram informados em data-base imediatamente anterior. | `idEvento, max(dataContabilizacao), dataBase` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_eventos_ausentes_na_data_base_atual` | Não informada no arquivo |
| `DRO000017` | Inconsistência | `ERRO` | Indícios de eventos que não constam na data-base imediante anterior e que deveriam ter sido informados. | `totalPerdaEfetiva + totalProvisao; dataContabilizacao; dataDescoberta` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_eventos_omitidos_na_data_base_anterior` | Não informada no arquivo |
| `DRO000018` | Inconsistência | `ERRO` | Verifica a existência de perda efetiva negativa em cada categoria do Bloco 2 - Eventos Consolidados. | `perdaEfetivaTotalConsol < -10` | `EVENTO_CONSOLIDADO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_perda_consolidada_nao_negativa` | Não informada no arquivo |
| `DRO000019` | Inconsistência | `ERRO` | Verifica a existência de provisão negativa em cada categoria do Bloco 2 - Eventos Consolidados. | `provisaoTotalConsol < -10` | `EVENTO_CONSOLIDADO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_provisao_consolidada_nao_negativa` | Não informada no arquivo |
| `DRO000021` | Inconsistência | `ERRO` | Eventos com atribuição de 2º Nível de Classificação Basileia II incondizente com 1º Nível | `categoriaNivel1 e categoriaNivel2` | `EVENTO` | `LOCAL` | Tabela oficial de categorias | `EXECUTADA` | `validar_relacao_categoria_nivel1_nivel2` | Não informada no arquivo |
| `DRO000022` | Inconsistência | `ERRO` | Eventos que apresentam redução de Perda Efetiva com relação à data-base imediatamente anterior | `totalPerdaEfetiva; dataBase` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_reducao_total_perda_historica` | Não informada no arquivo |
| `DRO000023` | Inconsistência | `ERRO` | Verifica a existência momentânea de saldo acumulado negativo de Perda Efetiva, no bloco de contabilizações. | `valorPerda; dataContabilizacao` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_saldo_acumulado_perda` | Não informada no arquivo |
| `DRO000024` | Esclarecimento | `AVISO` | Verifica a existência momentânea de saldo acumulado negativo de Provisão, no bloco de contabilizações. | `valorProvisao; dataContabilizacao` | `CONTABILIZACAO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_saldo_acumulado_provisao` | Não informada no arquivo |
| `DRO000026` | Esclarecimento | `AVISO` | Verifica alterações indevidas no bloco de contabilizações, em comparação à data-base imediatamente anterior. | `valorPerda; valorProvisao; valorRecuperado; dataContabilizacao; dataBase` | `CONTABILIZACAO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_alteracao_historico_contabilizacoes` | Não informada no arquivo |
| `DRO000027` | Esclarecimento | `AVISO` | Eventos com alteração da natureza da contingência, em compração à data-base imediatamente anterior. | `naturezaContingencia em dataBase atual ≠ naturezaContingencia em dataBase anterior` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_alteracao_natureza_historica` | Não informada no arquivo |
| `DRO000028` | Esclarecimento | `AVISO` | Eventos com alteração na avaliação de risco associado, em compração à data-base imediatamente anterior. | `riscoAssociado em dataBase atual ≠ riscoAssociado em dataBase anterior` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_alteracao_risco_associado_historico` | Não informada no arquivo |
| `DRO000029` | Esclarecimento | `AVISO` | Eventos com alteração na avaliação de associação ao risco cibernético, em compração à data-base imediatamente anterior. | `ligadoRiscoCibernetico em dataBase atual ≠ ligadoRiscoCibernetico em dataBase anterior` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_alteracao_risco_cibernetico_historico` | Não informada no arquivo |
| `DRO000030` | Esclarecimento | `AVISO` | Eventos com alteração na avaliação de associação ao risco socioambiental, em compração à data-base imediatamente anterior. | `ligadoRiscoSocioAmbiental em dataBase atual ≠ ligadoRiscoSocioAmbiental em dataBase anterior` | `EVENTO/HISTORICO` | `HISTORICA` | Data-base anterior | `REGRA NÃO EXECUTADA` | `validar_alteracao_risco_socioambiental_historico` | Não informada no arquivo |
| `DRO000032` | Inconsistência | `ERRO` | Eventos de fraude (categorias 1 e 2 do 1º Nível de Classificação Basileia II) com provisão. | `categoriaNivel1 = 1 ou 2 e totalProvisao > 0` | `EVENTO` | `LOCAL` | Nenhuma | `EXECUTADA` | `validar_provisao_em_evento_fraude` | Não informada no arquivo |

---

# 8. Regras internas necessárias antes das críticas oficiais

As críticas oficiais não substituem validações técnicas de leitura, normalização, agrupamento e XSD.

| Código interno | Fase | Descrição | Gravidade | Escopo |
|---|---|---|---|---|
| `XLSX-EST-001` | Leitura | `Base` ou `Cabecalho` não existe, ou somente uma das abas auxiliares foi fornecida | FALHA TÉCNICA | Arquivo |
| `XLSX-EST-002` | Leitura | Coluna obrigatória da versão não existe | ERRO IMPEDITIVO | Aba |
| `XLSX-EST-003` | Leitura | A aba `Cabecalho` possui mais de uma linha de dados | ERRO IMPEDITIVO | Cabeçalho |
| `XLSX-EST-004` | Leitura | Cabeçalhos duplicados na mesma aba | ERRO IMPEDITIVO | Aba |
| `NORM-NULO-001` | Normalização | Valor representa ausência e o campo é obrigatório | ERRO IMPEDITIVO | Célula |
| `NORM-DATA-001` | Normalização | Data inválida ou impossível | ERRO IMPEDITIVO | Célula |
| `NORM-DEC-001` | Normalização | Valor monetário inválido ou ambíguo | ERRO IMPEDITIVO | Célula |
| `NORM-DOM-001` | Normalização | Código fora do domínio da versão | ERRO IMPEDITIVO | Célula/evento |
| `NORM-ID-001` | Normalização | Identificador não pode ser convertido sem perda de informação | ERRO IMPEDITIVO | Célula |
| `MAP-EVT-001` | Agrupamento | Linhas do mesmo `idEvento` têm valores conflitantes | ERRO IMPEDITIVO | Evento |
| `MAP-PROB-001` | Agrupamento | Mesma probabilidade repetida com valores de risco conflitantes | ERRO IMPEDITIVO | Evento |
| `MAP-SIS-001` | Referência | Sistema usado na `Base` não possui referência única e válida | ERRO IMPEDITIVO | Evento |
| `MAP-CONTA-001` | Referência | Conta usada na `Base` não possui referência única e válida | ERRO IMPEDITIVO | Contabilização |
| `CONS-CALC-001` | Consolidação interna | Valores, datas ou categorias não resolvidos | ERRO IMPEDITIVO | Evento/documento |
| `VER-DATA-001` | Versionamento | `dataBase` anterior a `2020-12` | ERRO IMPEDITIVO | Documento |
| `VER-DATA-002` | Versionamento | Mês diferente de `06` ou `12` | ERRO IMPEDITIVO | Documento |
| `VER-DATA-003` | Versionamento | Formato de `dataBase` inválido | ERRO IMPEDITIVO | Documento |
| `VER-001` | Versionamento | Instrução 12/2026 incompatível com o XSD 06/2025 fornecido | ERRO IMPEDITIVO | Documento |
| `XSD-001` | XSD | XML não é válido no XSD selecionado | ERRO IMPEDITIVO | XML |
| `TECH-001` | Execução | Erro inesperado de leitura, escrita ou processamento | FALHA TÉCNICA | Execução |

---

# 9. Contrato técnico de uma regra

Cada regra será representada por um objeto semelhante a:

```python
@dataclass(frozen=True)
class RegraValidacao:
    critica_id: str
    descricao: str
    origem: str
    tipo_oficial: str
    gravidade: str
    vigencia_inicial: str | None
    vigencia_final: str | None
    escopo: str
    classe_execucao: str
    dependencia: str | None
    bloqueia_apto: bool
    executor: Callable[..., "ResultadoRegra"]
```

Resultado:

```python
@dataclass
class ResultadoRegra:
    critica_id: str
    descricao: str
    origem: str
    gravidade: str
    status: str
    ids_eventos: list[str]
    ocorrencias: list["OcorrenciaValidacao"]
    motivo_nao_execucao: str | None = None
```

Ocorrência detalhada:

```python
@dataclass
class OcorrenciaValidacao:
    aba: str | None
    linha: int | None
    id_evento: str | None
    coluna: str | None
    valor_original: object | None
    valor_normalizado: object | None
    mensagem: str
    sugestao: str | None
```

---

# 10. Contrato do resumo solicitado no relatório Excel

A aba `Resumo_Criticas` terá:

| Coluna | Regra |
|---|---|
| `criticaID` | Código oficial ou interno |
| `Descrição da critica` | Descrição consolidada |
| `contador` | Quantidade de `idEvento` distintos |
| `lista de ids` | Lista ordenada e sem duplicidade |

Exemplo:

```text
criticaID: DRO001232
Descrição da critica: Total recuperado superior ao permitido
contador: 2
lista de ids: ['BZIZ513', 'C00000000']
```

Cálculo:

```python
ids_unicos = sorted(set(ids_eventos))
contador = len(ids_unicos)
```

Regras sem `idEvento`, como erro no cabeçalho:

```text
contador = 0
lista de ids = []
```

---

# 11. Ordem de execução

```text
1. Estrutura do Excel
2. Normalização
3. Seleção de versão
4. Mapeamento e agrupamento
5. Tipos, formatos e domínios
6. Obrigatoriedades
7. Consistências entre campos
8. Críticas de pré-processamento
9. Cálculos e eventos consolidados
10. Construção do XML
11. Validação XSD
12. Críticas de pós-processamento locais
13. Críticas históricas, quando houver base anterior
14. Relatórios
```

Uma regra que depende de dados inválidos de uma fase anterior deverá ser marcada como `NÃO APLICÁVEL` ou `REGRA NÃO EXECUTADA`, com motivo técnico claro, evitando resultados em cascata sem sentido.

---

# 12. Testes mínimos por regra

Cada função deverá possuir pelo menos:

1. caso aprovado;
2. caso inconsistente;
3. caso não aplicável;
4. caso com valores ausentes ou inválidos;
5. caso não executado, quando houver dependência.

Padrão de nome:

```text
tests/validators/pre_processing/test_DRO001232.py
tests/validators/post_processing/test_DRO000015.py
```

Exemplo:

```python
def test_dro001232_reprova_quando_recuperacao_supera_perda_bruta():
    ...

def test_dro001232_aprova_quando_recuperacao_esta_no_limite():
    ...

def test_dro001232_nao_aplicavel_sem_recuperacao():
    ...
```

---

# 13. Organização dos arquivos de código

```text
src/validators/
├── common/
│   ├── rule.py
│   ├── result.py
│   └── occurrence.py
├── pre_processing/
│   ├── catalog.py
│   ├── validator.py
│   └── rules/
│       ├── dro001001.py
│       ├── dro001002.py
│       └── ...
├── post_processing/
│   ├── catalog.py
│   ├── validator.py
│   └── rules/
│       ├── dro000001.py
│       ├── dro000002.py
│       └── ...
├── excel_structure_validator.py
├── normalization_validator.py
├── business_validator.py
└── xsd_validator.py
```

Uma regra por arquivo facilita teste, rastreabilidade e manutenção, mas regras muito pequenas e diretamente relacionadas poderão ser agrupadas por módulo temático sem perder o código oficial.

---

# 14. Pendências documentais

1. confirmar a vigência individual das críticas de pós-processamento;
2. obter acesso ou extrato oficial do UNICAD;
3. obter cadastro COSIF aplicável por vigência;
4. definir formato de recebimento da data-base anterior;
5. confirmar o tratamento das críticas no leiaute 12/2026;
6. revisar a tradução interna de gravidades antes da homologação;
7. não considerar críticas externas ou históricas aprovadas sem execução.

---

# 15. Estado da etapa

```text
Etapa 1.3 — Matriz de críticas e validações: CONCLUÍDA
Etapa 1.4 — Conflitos documentais: CONCLUÍDA
Próxima etapa: 2.1 — Criar a estrutura inicial de pastas e arquivos do projeto
```

## 15. Implementação da etapa 5.5

O agrupamento por `idEvento` passou a executar localmente:

```text
DRO001103
DRO001311
DRO001312
DRO001314
DRO001452
MAP-EVT-001
MAP-PROB-001
```

Linhas repetidas com o mesmo identificador não criam eventos duplicados. Elas
formam um único evento, desde que seus atributos não sejam conflitantes.

## Implementação da etapa 5.6

As seguintes críticas de pós-processamento passaram a ser executadas localmente
após o agrupamento por `idEvento`:

```text
DRO000011
DRO000012
DRO000013
DRO000014
DRO000015
DRO000023
DRO000024
```

`DRO000024` mantém gravidade `AVISO`, conforme sua classificação como
esclarecimento. Para `DRO000023` e `DRO000024`, contabilizações na mesma data
podem resultar em `REGRA NÃO EXECUTADA` quando a ausência de sequência
intradiária impedir uma conclusão segura, conforme `CONF-023`.


## Implementação da etapa 5.7

As tabelas auxiliares passaram a executar localmente:

```text
DRO001101 — unicidade de codigoConta
DRO001102 — unicidade de codigoSistema
DRO001321 — sistema utilizado existe na tabela
DRO001401 — conta de débito existe na tabela
DRO001402 — conta de crédito existe na tabela
```

Também foram criadas validações estruturais e de formato baseadas nos XSDs,
além de informações diagnósticas sobre códigos válidos não utilizados.

As divergências de tamanho, caracteres e chaves `xs:key` estão registradas em
`CONF-025`, `CONF-026` e `CONF-027`.

## Implementação da etapa 5.11

As 34 críticas oficiais de pré-processamento foram reunidas no catálogo:

```text
src/validators/pre_processing/catalog.py
```

O integrador reutiliza os resultados das validações por linha, agrupamento,
evento e tabelas de referência.

Permanecem como `REGRA NÃO EXECUTADA` na planilha de testes:

```text
DRO001001 — UNICAD
DRO001002 — UNICAD/Bacen
DRO001241 — conflito CONF-022
```

`DRO001431`/`DRO001432` deixaram de depender de fonte externa: passam a
ser executadas localmente contra `assets/lista_COSIF_validas.txt`.

Nenhuma dessas regras é registrada como aprovada.

## Implementação da etapa 5.12

As 26 críticas oficiais de pós-processamento foram reunidas em:

```text
src/validators/post_processing/catalog.py
```

Execução local:

```text
DRO000003
DRO000004
DRO000005
DRO000009
DRO000010
DRO000011
DRO000012
DRO000013
DRO000014
DRO000015
DRO000021
DRO000023
DRO000024
DRO000032
```

Dependentes de eventos consolidados:

```text
DRO000001
DRO000002
DRO000018
DRO000019
```

Dependentes da data-base imediatamente anterior:

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

Sem as dependências correspondentes, essas regras são registradas como
`REGRA NÃO EXECUTADA`.
