# Using Alembic

o Alembic prepara as migrações e atualizações de Banco de Dados, como executá-las (automática ou manualmente), como resolver os problemas de mudanças irreversíveis, testar migrações, quais problemas podem ser detectados por testes...


## Criando as definições na pasta migrations
```bash
alembic init migrations
```

nesse ponto é necessário alterar o arquivo alembic.ini para incluir o endereço completo de conexão com o banco dados:

exemplo: `sqlalchemy.url = driver://user:pass@localhost/dbname`

também é importante lembrar de atualizar o arquivo `migrations/env.py`

apontando a variável metadata de suas representações dos modelos de banco dados. Mas o que é o Metadata? MetaData é uma espécie de objeto, um container, no qual você irá adicionar suas tabelas, índices e, em geral, todas as entidades que possui. Este é um objeto que reflete, por um lado, como você deseja ver o banco de dados, com base em seu código escrito. Por outro lado, o MetaData pode ir para o banco de dados, obter um instantâneo do que realmente está lá e construir o próprio modelo de objeto.


## Criando um Script de Migração
Antes de criar um script de migração tenha certeza que o banco de dados não possui tabelas e / ou outros scripts

```bash
alembic revision --autogenerate -m "create first migrations"
```

dentro da pasta migrations/versions será criado um novo script dom o ID de revisão e a data de criação


## Aplicando as migrações

```bash
alembic upgrade head

```


## Usos especiais

#### Adicionando uma nova coluna do tipo enumerador
ALém de descrever a coluna nova na representação do modelo, também é necessário editar o script de migração

no método upgrade() do novo script de migração gerado com o `alembic revision` será necessário observar alguns pontos, nesse caso o exemplo será a inserção de uma coluna `role`na tabela `user`.

```python
from sqlalchemy.dialects import postresql
...
def update():
    user_role = postgresql.ENUM('super_user', 'admin', 'user', name="user_role")
    user_role.create(op.get_bind())
    op.add_column('users', sa.Column('role', sa.Enum('super_user', 'admin', 'user', name="user_role"), server_default='user', nullable=False))
```