# 🚀 Passo a passo — colocar a Barbearia Recortes no ar

Guia operacional. Siga na ordem. Cada fase tem um **objetivo** e uma
**verificação** — só avance quando a verificação passar.

> **Regra de ouro:** o arquivo `.streamlit/secrets.toml` tem credenciais reais e
> **nunca** vai para o git (já está no `.gitignore`). Os segredos de produção
> vivem no painel do host (Streamlit Cloud / Render), não no repositório.

---

## FASE 1 — Subir o código no GitHub (repositório PRIVADO)

**Objetivo:** ter o código versionado no GitHub, sem nenhum segredo junto.
É pré-requisito do Streamlit Cloud e do Render.

### 1.1 — Conferir que nenhum segredo vai no commit
```bash
git init
git add -A
git status
```
Na lista do `git status`, **confirme que NÃO aparece**:
- `.streamlit/secrets.toml`
- qualquer `.env`

Se aparecer algum, PARE — o `.gitignore` não pegou. (Não deve acontecer, mas
confira sempre antes do primeiro commit: segredo que entra no histórico não sai.)

### 1.2 — Primeiro commit
```bash
git commit -m "Primeira versao - app de agendamento Barbearia Recortes"
```

### 1.3 — Criar o repositório no GitHub
- Crie um repositório **novo e PRIVADO** no GitHub (deixe "Public" desmarcado).
- Não adicione README/gitignore por lá (o projeto já tem).
- Copie os comandos que o GitHub mostra para "push an existing repository", algo como:
```bash
git remote add origin https://github.com/SEU_USUARIO/NOME_DO_REPO.git
git branch -M main
git push -u origin main
```

✅ **Verificação:** o código aparece no GitHub e **não há** `secrets.toml` lá.

---

## FASE 2 — Preparar o banco do Renan (Neon dele, LIMPO)

**Objetivo:** criar as tabelas + a conta do gestor no Neon do cliente, **sem**
os dados fictícios de teste (João Silva, Corte R$40).

### 2.1 — Gerar um segredo de sessão real
```bash
python -m scripts.gerar_segredo
```
Guarde o `SESSION_SECRET` que ele imprime — você vai usar o **mesmo** no
Streamlit Cloud e depois no Render.

### 2.2 — Apontar o secrets.toml LOCAL para o Neon do Renan
Abra `.streamlit/secrets.toml` e coloque a connection string do Neon **dele**
em `database_url`. Dois ajustes na URL que o Neon te dá:
1. troque `postgresql://` por **`postgresql+psycopg2://`**
2. garanta `?sslmode=require` no final
3. use a URL com **`-pooler`** (pooled)

Exemplo:
```toml
database_url = "postgresql+psycopg2://USUARIO:SENHA@ep-xxxx-pooler.REGIAO.aws.neon.tech/neondb?sslmode=require"
session_secret = "COLE_O_SEGREDO_GERADO_NO_2.1"

[salao]
nome = "Barbearia Recortes"
timezone = "America/Sao_Paulo"

[gestor]
email = "renan@recortes.com"
senha = "UMA_SENHA_FORTE"
```

### 2.3 — Criar o schema e o gestor (banco limpo)
```bash
python -m alembic upgrade head      # cria as tabelas
python -m scripts.resetar_gestor    # cria SO o gestor (zero dado fake)
```
⚠️ **NÃO rode** `python -m src.db.seed` no banco do Renan — ele cria João Silva
e serviços de exemplo, que você não quer em produção.

✅ **Verificação:** os dois comandos rodam sem erro e o `resetar_gestor` diz
"gestor criado" (ou "senha atualizada").

---

## FASE 3 — Publicar no Streamlit Cloud (ambiente de STAGING)

**Objetivo:** deixar o app no ar para a Renan cadastrar os dados reais
(cabeleireiros, serviços, horários). Os dados vão para o Neon dele e depois
migram sozinhos para o Render, porque o banco é o mesmo.

### 3.1 — Conectar o repositório
- Entre em https://share.streamlit.io com a conta do GitHub.
- "New app" → escolha o repositório privado → branch `main` → arquivo `app.py`.

### 3.2 — Colar os secrets no painel (NÃO no repo)
Em **Manage app → Settings → Secrets**, cole o mesmo conteúdo do seu
`secrets.toml` (o bloco da Fase 2.2). Inclua `[smtp]` se quiser que os e-mails
de confirmação/lembrete funcionem já no staging:
```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "SEU_EMAIL@gmail.com"
password = "APP_PASSWORD_DE_16_DIGITOS"
remetente = "Barbearia Recortes <SEU_EMAIL@gmail.com>"
```

### 3.3 — Publicar
O Streamlit Cloud instala o `requirements.txt` e sobe o app.

✅ **Verificação (importante):**
- Login com `renan@recortes.com` + a senha da Fase 2.2 → entra como gestor.
- **O horário no app bate com o relógio de Brasília** (confirma que o hook de
  timezone funcionou no host UTC do Streamlit Cloud).
- Não aparece nenhum "João Silva" nem "Corte R$40" (banco limpo).

---

## FASE 4 — Renan cadastra os dados reais

Peça para ela (ou faça junto no primeiro acesso), como **gestor**:
- **Cabeleireiros** — nome de cada profissional + criar o LOGIN de cada um
  (sem login, o profissional não recebe agenda/cancelamento por e-mail).
- **Serviços** — nome, preço e duração de cada um.
- **Horários de trabalho** de cada cabeleireiro.
- Descontos por profissional/serviço, se houver.

⚠️ **Não divulgue a URL `*.streamlit.app` para os clientes finais dela ainda.**
Esse é o ambiente de preparação. A URL pública de verdade será a do Render
(com domínio próprio). Se os clientes agendarem pela URL do staging, os links
quebram na virada.

---

## FASE 5 — (Depois) Produção no Render pago

Quando os dados estiverem cadastrados e você fechar cartão/conta com ela:
1. Deploy no Render usando o `Dockerfile` (já pronto).
2. As **mesmas env vars** no painel do Render: `DATABASE_URL` (o mesmo Neon do
   Renan), `SESSION_SECRET` (o mesmo da Fase 2.1), `SALAO_NOME`, `GESTOR_SENHA`,
   e o bloco `SMTP_*`. O `TZ=America/Sao_Paulo` já está fixado no Dockerfile.
3. Healthcheck do Render apontando para `/_stcore/health`.
4. Configurar o domínio próprio + HTTPS.
5. Ativar o cron de lembretes (GitHub Actions) com os mesmos secrets do repo.

Como o banco (Neon) é o mesmo do staging, **todos os dados que a Renan cadastrou
já estarão lá** — é só apontar e subir.

---

## ⚠️ Pendências conhecidas antes de considerar "pronto para o cliente final"
- [ ] **Testar o SMTP de verdade** — disparar um agendamento e confirmar que o
      e-mail chega na caixa (hoje nunca foi testado com envio real).
- [ ] **Confirmar que `renan@recortes.com` recebe e-mail** — se não receber,
      usar o Gmail pessoal dela, senão a recuperação de senha do gestor não
      funciona.
- [ ] Rodar o job de lembretes ponta a ponta (`python -m src.jobs.lembretes`,
      sem `--dry-run`, com SMTP ligado).
- [ ] Logo em vetor (opcional — o atual é fallback aceitável).
