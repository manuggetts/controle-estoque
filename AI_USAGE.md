# Uso de Inteligência Artificial

**Ferramenta:** Claude (Anthropic), via chat.
**Convenção:** *Prompt (trecho)* é literal, com cortes marcados por `[...]`; *Interação (resumo)* sintetiza trocas mais longas. Só as interações de maior impacto estão registradas.

---

## Principais prompts

### P1. Planejamento prévio ao código
**Objetivo:** obter a análise do case e o plano de modelagem antes de qualquer implementação.

**Prompt (trecho):**
> Antes de escrever qualquer linha de código, nós vamos apenas PLANEJAR. Quero que você atue como meu Tech Lead / Mentor Técnico. [...] nosso objetivo é debater e estruturar tudo:
> 1. Como vamos arquitetar a solução de forma eficiente.
> 2. Como garantir que 100% dos requisitos (obrigatórios e diferenciais) sejam cumpridos.
> [...] Não gere códigos ainda. [...] analise o anexo e me diga: quais são os pontos-chave e os maiores desafios que você identificou neste case [...]

- **Técnica:** papel + restrição explícita (sem código) + objetivos numerados.
- **Validação:** pontos levantados confrontados com o enunciado do case.
- **Resultado:** invariante `total = disponível + reservado + bloqueado`; reservas e bloqueios como registros com ID; atomicidade (validar antes de alterar); ambiguidades do enunciado.
- **Decisão:** modelar a partir do invariante e documentar as premissas no README.

### P2. Integração com eventos (EDA / Kafka)
**Objetivo:** definir como tratar eventos, citados na vaga, em uma solução baseada em API sem comprometer o escopo.

**Interação (resumo):** três alternativas comparadas por custo e aderência ao escopo do case: apenas documentar; tabela de eventos com padrão outbox; Kafka real.

- **Técnica:** comparação de alternativas com critérios explícitos.
- **Validação:** confrontada com os critérios de avaliação do case (simplicidade e decisões justificadas).
- **Decisão:** priorizar o núcleo funcional completo; eventos tratados como extra e descritos na seção de produção do README.

### P3. Cadastro de produto
**Objetivo:** definir se a Entrada cria produtos inexistentes.

**Interação (resumo):** a IA recomendou que a Entrada criasse o produto automaticamente. Rejeitei: um erro de digitação no ID criaria um produto em silêncio, comprometendo a integridade do estoque.

- **Técnica:** revisão crítica de uma recomendação, com justificativa técnica.
- **Validação:** regra coberta por testes automatizados (operações em produto inexistente retornam 404; cadastro duplicado retorna 409).
- **Decisão:** cadastro prévio por endpoint próprio; as demais operações em produto inexistente retornam 404.

### P4. Estratégia de execução
**Objetivo:** organizar a implementação em etapas verificáveis.

**Interação (resumo):** definição de etapas (domínio, persistência, serviços/API, concorrência, documentação), cada uma com critério de pronto (testes passando), núcleo funcional completo primeiro e extras depois.

- **Validação:** suíte executada a cada etapa (24, 32, 63 e 64 testes passando ao fim de cada etapa).
- **Resultado:** código e testes por camada produzidos com apoio da IA.

### P5. Análise de cobertura dos testes
**Objetivo:** identificar lacunas de teste relevantes além do percentual de linhas.

**Prompt (trecho):**
> Atue como revisor de qualidade de software. Contexto: API de controle de estoque (Python, FastAPI, SQLite); regras de negócio em app/dominio, transações em app/infra. Relatório de cobertura: [relatório do pytest-cov]. Tarefa: identificar lacunas relevantes (não só percentual de linhas), priorizando regras de negócio, tratamento de erros e consistência. Restrições: no máximo 5 testes novos, sem redundância. Formato: tabela (lacuna, risco, teste sugerido).

- **Técnica:** prompt estruturado (papel, contexto, tarefa, restrições, formato de saída), elaborado com apoio da IA.
- **Validação:** relatório do `pytest-cov` (99% das linhas; apenas `app/main.py`, código de ligação, sem cobertura; 64 testes passando).
- **Resultado:** lacunas de comportamento apontadas: quantidade sem limite máximo e concorrência testada só em reservas (faltava a liberação simultânea da mesma reserva).
- **Decisão:** limite de 1.000.000.000 por operação (API e domínio) e três casos de teste novos de comportamento; `app/main.py` mantido sem teste.

### P6. Revisão crítica do código
**Objetivo:** levantar riscos de consistência, concorrência e tratamento de erros no código do repositório.

**Prompt (trecho):**
> Atue como engenheiro sênior revisando o código quanto a consistência, concorrência e tratamento de erros. Tarefa: listar riscos reais, por severidade, com o cenário de falha de cada um, indicando o que corrigir agora e o que registrar como limitação. Restrição: sem mudanças de arquitetura; o escopo é um case de 3 horas. Formato: tabela (risco, cenário, severidade, ação).

- **Técnica:** prompt estruturado com critério de priorização (severidade) e separação entre "corrigir agora" e "registrar como limitação".
- **Validação:** riscos conferidos por leitura do código-fonte do repositório.
- **Resultado:** quantidade sem limite máximo (valores acima de 64 bits não são aceitos pelo SQLite); erros inesperados e rotas inexistentes fora do formato de erro padrão; `.coverage` fora do `.gitignore`; erro de integridade qualquer tratado como "produto já existe".
- **Decisão:** limite de quantidade, `.gitignore` e README corrigidos; o ponto sobre erros inesperados e rotas inexistentes foi registrado em 'Limitações' do README.

### P7. Validação do teste de concorrência
**Objetivo:** confirmar que os testes de concorrência dependem do bloqueio de escrita antecipado e não passam por acaso.

**Interação (resumo):** teste de mutação manual: `BEGIN IMMEDIATE` substituído temporariamente por `BEGIN` em `app/infra/banco.py` (alteração não commitada) e `tests/servicos` executado 3 vezes.

- **Técnica:** teste de mutação manual (quebrar a proteção de propósito para verificar que os testes falham).
- **Validação:** nas 3 execuções, os 2 testes de concorrência falharam com `sqlite3.OperationalError: database is locked`, no `UPDATE` que sucede a leitura do produto.
- **Resultado:** a proteção vem do `BEGIN IMMEDIATE`: com `BEGIN`, a transação lê o estoque e só depois tenta escrever, e o SQLite recusa a promoção de leitura para escrita quando há outra escrita concorrente.
- **Decisão:** manter `BEGIN IMMEDIATE`; os testes de concorrência ficam como proteção contra regressão.

---

## Análise

### Onde a IA mais ajudou
- **Modelagem antes do código:** invariante e ambiguidades do enunciado levantados antes de codar.
- **Código e testes por camada:** incluindo casos de borda e a verificação de "estado inalterado após falha".
- **Revisão crítica:** cobertura e riscos analisados sobre o código real, o que levou a um limite de quantidade e a um teste de concorrência a mais.

### Sugestões modificadas ou não utilizadas
- **Entrada criando o produto automaticamente:** não adotada. Um erro de digitação no ID criaria um produto em silêncio; adotado cadastro prévio.
- **Tabela de eventos e Kafka:** não implementados (extra). O case não pede mensageria e valoriza soluções simples e justificadas; o caminho está descrito no README.

### Erros e limitações identificados
- **Afirmação exagerada:** a IA indicou que a decisão sobre eventos "altera o esquema do banco, então precisa vir antes do código". Ao ser pedido um exemplo, reconheceu o exagero: a tabela de eventos seria adicional.
- **README com afirmações sem sustentação:** o primeiro rascunho dizia que "cada camada só conhece a de baixo" (falso, pois a API importa domínio e infra) e que o projeto funcionava com Python 3.10 ou superior (nunca testado). Corrigidas após a revisão contra o case. Uma terceira, "todos os erros usam o mesmo formato", era falsa para rotas inexistentes e erros inesperados; foi corrigida após a revisão do código (P6).
- **Código gerado sem limite máximo de quantidade:** risco de erro 500 ao gravar valores muito grandes; identificado na revisão (P6) e corrigido.
- **Instruções de setup densas demais:** reformuladas em passo a passo após solicitação.
