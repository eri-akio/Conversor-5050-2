# Validação de totais, contabilizações e saldos

**Projeto:** Conversor XLSX → XML DRO 5050  
**Etapa:** 5.6  
**Arquivo principal:** `src/validators/event_financial_validator.py`

## 1. Objetivo

Conferir os valores financeiros após o agrupamento por `idEvento`.

A etapa usa somente valores normalizados com `Decimal` e preserva os
lançamentos contábeis originais.

## 2. Resumo financeiro

Para cada evento é criado um `EventFinancialSummary` contendo:

```text
totais declarados
soma das contabilizações
diferenças entre total e soma
quantidade e linhas das contabilizações
saldos acumulados por data
contabilizações sem data válida
```

Nenhum total é substituído silenciosamente pelo valor calculado.

## 3. Regras implementadas

| Código | Regra | Gravidade |
|---|---|---|
| `DRO000011` | `totalPerdaEfetiva < -10` | ERRO |
| `DRO000012` | `totalProvisao < -10` | ERRO |
| `DRO000013` | `totalRecuperado > 0` | ERRO |
| `DRO000014` | `abs(totalRecuperado) > totalPerdaEfetiva + totalProvisao` | ERRO |
| `DRO000015` | Totais diferentes da soma das contabilizações | ERRO |
| `DRO000023` | Saldo acumulado negativo de perda | ERRO |
| `DRO000024` | Saldo acumulado negativo de provisão | AVISO |

Os limites de `-10` são aplicados exatamente como constam nas críticas
de pós-processamento. Não foi criada tolerância adicional.

## 4. Conferência dos totais

São calculados:

```text
soma(valorPerdaEfetiva)
soma(valorProvisao)
soma(valorRecuperacao)
```

E comparados, sem arredondamento adicional, com:

```text
totalPerdaEfetiva
totalProvisao
totalRecuperado
```

Campos monetários ausentes dentro de uma contabilização contribuem com
zero. Um total do evento ausente, inválido ou conflitante faz a regra
ficar como `REGRA NÃO EXECUTADA`.

## 5. Saldos por data

Os saldos de perda e provisão começam em zero e são acumulados pela
`dataContabilizacao`.

Para cada data são preservados:

```text
saldo de abertura
movimentos do dia
saldo de fechamento
menor saldo possível dentro do dia
linhas de origem
```

## 6. Contabilizações na mesma data

As fontes fornecidas possuem data, mas não horário ou sequência
intradiária.

Por isso, o sistema não usa arbitrariamente a ordem da linha para
aprovar ou reprovar uma crítica oficial.

Em uma mesma data:

- se o saldo de fechamento é negativo, a regra é `REPROVADA`;
- se o saldo nunca ficaria negativo, qualquer que fosse a ordem, a
  regra é `APROVADA`;
- se algumas ordens ficariam negativas e outras não, a regra é
  `REGRA NÃO EXECUTADA`.

Essa limitação está registrada como `CONF-023`.

## 7. Ausência de contabilizações

Sem contabilizações:

- `DRO000015` ainda compara os totais com somas iguais a zero;
- `DRO000023` e `DRO000024` ficam `NÃO APLICÁVEL`.

Assim, um evento exclusivamente de risco com totais contábeis zerados
pode passar na conferência de totais sem criar contabilizações
fictícias.

## 8. Resultado de aviso

`DRO000024` é classificada como esclarecimento nas críticas fornecidas.
Por isso, uma falha gera `AVISO` e não bloqueia o evento por si só.

O aviso permanece no relatório e não é tratado como aprovação.

## 9. Vigência

O arquivo de críticas de pós-processamento fornecido não informa a
vigência individual dessas regras.

Elas são executadas localmente sobre os campos comuns dos perfis
fornecidos. No perfil presumido de 12/2026, o resultado continua
diagnóstico e não remove o bloqueio documental da versão.

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
python -m pytest tests/test_event_financial_validator.py -v
```

## 12. Próxima etapa

```text
5.7 — Ler e validar as tabelas de sistemas e contas internas
```

## 13. Convencao de sinal e estornos

Movimentos negativos de perda e provisao podem representar estornos. O
projeto nao cria uma rejeicao local absoluta: aplica os limites finais de
`DRO000011`/`DRO000012` e os saldos acumulados de
`DRO000023`/`DRO000024`.

