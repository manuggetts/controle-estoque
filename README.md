# Controle de Estoque

API REST em Python para controle de estoque de produtos, com quantidade total, disponível, reservada e bloqueada, preservando a consistência em todas as operações.

O uso de IA está documentado em [AI_USAGE.md](AI_USAGE.md).

---

## 1. Visão geral

Para cada produto o sistema mantém quatro números e uma regra que nunca pode ser quebrada:

```
total = disponível + reservado + bloqueado
```

| Funcionalidade | Endpoint | Sucesso | Erros possíveis |
|---|---|---|---|
| Cadastrar produto | `POST /produtos` | 201 | 409 já existe · 422 |
| Consultar produto | `GET /produtos/{id}` | 200 | 404 |
| Entrada | `POST /produtos/{id}/entrada` | 200 | 404 · 422 |
| Saída | `POST /produtos/{id}/saida` | 200 | 404 · 409 estoque insuficiente · 422 |
| Reservar | `POST /produtos/{id}/reservas` | 201 (devolve o ID) | 404 · 409 · 422 |
| Bloquear | `POST /produtos/{id}/bloqueios` | 201 (devolve o ID) | 404 · 409 · 422 |
| Consultar reserva / bloqueio | `GET /reservas/{id}` · `GET /bloqueios/{id}` | 200 | 404 |
| Liberar reserva / bloqueio | `POST /reservas/{id}/liberar` · `POST /bloqueios/{id}/liberar` | 200 | 404 · 409 já liberado |

Os erros de regra de negócio e de validação usam o mesmo formato, com um código estável:

```json
{"erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "Quantidade disponível: 7; solicitado: 11."}}
```

## 2. Arquitetura e estrutura

Quatro camadas: o **domínio** (regras de negócio) não depende de nenhuma outra; a **infra** traduz o domínio em SQL (SQLite); os **serviços** orquestram cada caso de uso em uma única transação; a **API** expõe os serviços via HTTP.

```
controle-estoque/
├── app/
│   ├── dominio/      regras de negócio puras: modelos.py, erros.py (sem banco, sem HTTP)
│   ├── infra/        schema.sql, banco.py (transação), repositorio.py (SQL)
│   ├── servicos/     estoque.py: cada caso de uso roda em uma única transação
│   ├── api/          schemas.py (entrada/saída), aplicacao.py (rotas e tradução de erros)
│   └── main.py       cria a aplicação com o banco real
├── tests/
│   ├── dominio/      regras de negócio, sem banco
│   ├── infra/        persistência, rollback e restrições do banco
│   ├── api/          contrato HTTP, códigos de erro e fluxo completo
│   └── servicos/     concorrência
├── README.md · AI_USAGE.md · requirements.txt · pytest.ini
```

## 3. Principais decisões técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| Linguagem | Python | Linguagem que uso no dia a dia e domino melhor; permitida pelo case. |
| Exposição | API REST com FastAPI | Mais próxima de um cenário real de backend; validação e documentação Swagger automáticas. |
| Persistência | SQLite com `sqlite3` e SQL escrito à mão | Simples de executar, suporta transações e deixa o SQL explícito (sem ORM para um esquema pequeno). |
| Disponível | Calculado: total − reservado − bloqueado | Uma única fonte de verdade; impede divergência entre os números. |
| Reserva e bloqueio | Registros com ID (UUID) e status ATIVO/LIBERADO | Permitem consulta e liberação por ID, preservam histórico e detectam liberação repetida. |
| Cadastro de produto | Endpoint próprio; as demais operações em produto inexistente retornam 404 | Evita criar produtos em silêncio por erro de digitação. |
| Consistência | Validar antes de alterar + transação única + restrições no banco | Operação inválida nunca deixa estado inconsistente; o banco é a segunda barreira (`CHECK (reservado + bloqueado <= total)`). |
| Concorrência | `BEGIN IMMEDIATE` com espera de até 10 s | Operações simultâneas entram em fila; a segunda lê o estoque já atualizado. |
| Validação | Em duas camadas: formato na API, regra no domínio | Se o serviço for usado sem a API, o domínio continua protegendo. |
| Erros | Exceções de domínio com código fixo, traduzidas em um único lugar para HTTP | O domínio não conhece HTTP; formato de erro único. |
| Liberação | `POST .../liberar` (não `DELETE`) | O registro não é apagado, só muda de status. |
| Eventos (EDA/Kafka) | Fora do escopo; descrito na seção 7 | Proporcional ao escopo do case. |

## 4. Premissas

- O produto deve ser **cadastrado antes** (`POST /produtos`). Entrada, saída, reserva, bloqueio e consulta em produto inexistente retornam 404.
- Quantidades são **inteiros entre 1 e 1.000.000.000 por operação** (zero, negativos, decimais, texto, booleanos e valores acima do limite são rejeitados).
- A **saída reduz o total** e só pode usar unidades disponíveis (não retira reservadas nem bloqueadas).
- Liberar uma reserva ou bloqueio devolve a quantidade ao disponível. O registro permanece consultável com status `LIBERADO`, e liberar de novo retorna 409.
- Um mesmo pedido pode ter várias reservas do mesmo produto; cada uma tem seu ID e é liberada de forma independente.
- A liberação é sempre total (não existe liberação parcial).
- A referência do pedido é obrigatória na reserva; o motivo do bloqueio é opcional.
- Os IDs de reserva e bloqueio (UUID) são gerados pelo sistema; o ID do produto é informado pelo cliente.
- Um único estoque por produto (sem múltiplos armazéns) e sem autenticação.

## 5. Limitações conhecidas

- **SQLite** permite um escritor por vez e usa um arquivo local: serve para uma instância, não para várias com muita escrita.
- Até as consultas rodam em transação com `BEGIN IMMEDIATE`, o que serializa também as leituras. É uma simplificação consciente nesta escala.
- O teste de concorrência usa threads em um único processo; vários processos dependem do bloqueio de arquivo do SQLite e não foram testados.
- Sem autenticação, paginação, listagem de produtos, edição ou remoção de produtos.
- Sem histórico de movimentações (só o saldo atual e o status de reservas e bloqueios).
- Erros inesperados (por exemplo, esgotar a espera de 10 s pelo bloqueio de escrita) e rotas inexistentes não seguem o formato de erro padrão; retornam a resposta padrão do FastAPI.

## 6. Como executar

Requisitos: Python e Git. Desenvolvido e testado com Python 3.14 no Windows (o código usa sintaxe do Python 3.10 em diante).

```bash
git clone https://github.com/manuggetts/controle-estoque.git
cd controle-estoque
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

**Rodar os testes:**

```bash
pytest -q
```

**Subir a API:**

```bash
uvicorn app.main:app --reload
```

Com a API no ar, a documentação interativa (Swagger) fica em `http://127.0.0.1:8000/docs`. O banco é criado no arquivo `estoque.db` na pasta atual; para usar outro caminho, defina a variável de ambiente `ESTOQUE_DB`.

## 7. O que eu faria diferente em produção

- **Banco cliente-servidor** (por exemplo, PostgreSQL) com bloqueio por linha (`SELECT ... FOR UPDATE`) ou controle otimista por versão, para várias instâncias da aplicação, e migrações de esquema com uma ferramenta própria.
- **Histórico de movimentações** (auditoria) de cada entrada, saída, reserva, bloqueio e liberação.
- **Expiração de reservas** não confirmadas e conversão de reserva em saída (baixa do pedido).
- **Eventos de domínio** (Kafka ou similar) a cada operação, para integração com outros sistemas. Para não perder eventos, gravá-los numa tabela na mesma transação da operação (padrão outbox) e publicá-los depois.
- **Idempotência** nas operações de escrita, com chave enviada pelo cliente, para tolerar repetição de chamadas.
- **Segurança e operação:** autenticação e autorização, logs estruturados, métricas e tracing.
- **Entrega e nuvem:** Docker, CI com testes a cada push e implantação na AWS (por exemplo, banco gerenciado e contêiner ou serverless atrás de um API Gateway).

## 8. Visão de engenharia: os 5 aspectos mais importantes

1. **Consistência dos dados.** Estoque é um número que outras áreas usam para tomar decisões. O invariante precisa valer sempre, e por isso há duas barreiras: as regras do domínio e as restrições do banco.
2. **Testes automatizados.** Protegem as regras de negócio contra regressões e documentam o comportamento esperado. O foco foi nos casos de borda e no "estado inalterado após falha", não na quantidade de testes.
3. **Concorrência e atomicidade.** Duas reservas simultâneas da última unidade não podem ambas ter sucesso. Transação única por operação e `BEGIN IMMEDIATE` resolvem isso numa instância, e o teste com threads demonstra o comportamento.
4. **Separação de camadas.** Regras de negócio isoladas de banco e de HTTP permitem trocar o SQLite por outro banco, ou a API por uma fila, sem reescrever o domínio, e tornam os testes rápidos.
5. **Capacidade de evolução e observabilidade.** Histórico de movimentações, eventos de domínio, logs e métricas permitem diagnosticar problemas e integrar novos sistemas sem mexer no núcleo.
