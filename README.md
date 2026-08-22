# 💈 Salão — App de Agendamento

App modular em **Streamlit** para um salão de cabeleireiro: cadastro/login de
clientes, agendamento rápido com escolha de cabeleireiro e serviço (o calendário
mostra **apenas dias com vaga**), **descontos específicos por cabeleireiro**
amarrados ao preço do serviço, **confirmação por e-mail/WhatsApp**, **lembrete
automático 1 dia antes** e **cancelamento/reagendamento** self-service. O gestor
ainda registra **atendimentos avulsos (walk-in)** no balcão e **redefine a senha**
de clientes; o cliente também pode **redefinir a senha por código no e-mail**.
Banco de dados: **Neon (Postgres)**.

---

## Arquitetura (camadas)

```
app.py                      # entrypoint Streamlit: gate de auth + router por papel
src/
  config/settings.py        # lê env vars OU .streamlit/secrets.toml (app e jobs)
  db/                        # engine (Neon), Base, models ORM, seed
  repositorios/              # CAMADA DE DADOS — CRUD + queries (inclui relatorios)
  servicos/                  # CAMADA DE NEGÓCIO — auth, precificacao, agenda, reservas
  notificacoes/              # console (dev) / email (SMTP) / whatsapp (Meta) + dispatcher
  jobs/lembretes.py          # job CLI idempotente "1 dia antes"
  ui/
    componentes/             # styles (tema dark), guards (sessão), graficos (ECharts)
    paginas/                 # login, cadastro, agendar, meus_agendamentos, gestor_*
alembic/                     # migrations versionadas
```

**Regra-chave (desconto):** o desconto de cada cabeleireiro por serviço vive na
tabela `cabeleireiro_servico` (tipo `percentual`/`valor`). O preço final é
calculado em [`src/servicos/precificacao.py`](src/servicos/precificacao.py) sobre
o `preco_base` do serviço.

**Gráficos:** self-contained em
[`src/ui/componentes/graficos.py`](src/ui/componentes/graficos.py) (ECharts via
`streamlit-echarts`), sem dependência externa.

---

## Setup local

1. **Dependências**
   ```bash
   pip install -r requirements.txt
   ```

2. **Segredos** — copie o modelo e preencha:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Mínimo para rodar: `database_url` (Neon, com `+psycopg2` e `sslmode=require`).
   E-mail/WhatsApp são opcionais — sem eles, as notificações caem no **console**.

3. **Banco** (cria schema + dados de exemplo):
   ```bash
   python -m alembic upgrade head
   python -m src.db.seed
   ```

4. **Rodar o app**
   ```bash
   streamlit run app.py
   ```

5. **Disparar lembretes** (manual ou via agendador):
   ```bash
   python -m src.jobs.lembretes            # alvo = amanhã
   python -m src.jobs.lembretes --dry-run  # só lista
   ```

---

## Contas

- **Gestor** (admin): criado pelo seed a partir de `[gestor]` no `secrets.toml`
  (padrão `gestor@salao.com` / `admin123` — **troque**). Para mudar a senha depois,
  atualize `[gestor]` e rode:
  ```bash
  python -m src.db.seed   # idempotente: NÃO sobrescreve senha existente
  ```
  (para resetar a senha de um gestor já criado, use um script de update ou apague a
  linha do cliente gestor antes de re-seedar).
- **Cliente**: cadastro pela própria UI. Esqueceu a senha? Use **"Esqueci minha
  senha"** na tela de login (código de 6 dígitos por e-mail, válido 30 min) ou peça
  ao gestor (página **Clientes**) para redefinir.
- **Cabeleireiro**: login criado pelo gestor na página **Cabeleireiros** (seção
  "Login do cabeleireiro": e-mail + senha). A conta tem `papel='cabeleireiro'` e
  aponta para o perfil via `cliente.cabeleireiro_id`. Ao entrar, ele vê **Meu
  painel** (KPIs só dele, agenda do dia com horários marcados e **vagos**) e
  **Registrar atendimento** (agenda na própria agenda, avulso ou cliente).

### Atendimento avulso (walk-in)
Na página **Atendimento avulso**, o gestor agenda para quem aparece no balcão —
identificando por nome/telefone (sem conta) ou escolhendo um cliente cadastrado —
e vê a **agenda do dia** de cada cabeleireiro. No banco, esses agendamentos têm
`cliente_id` nulo e guardam `nome_avulso`/`telefone_avulso`.

---

## Notificações

**Quem recebe o quê** (`notificacoes/eventos.py`):

| Evento | Cliente | Profissional |
|---|---|---|
| Novo agendamento | ✅ confirmação | só se for **para hoje** (o resumo da manhã já saiu) |
| Lembrete D-1 | ✅ | — |
| **Remarcação** | ✅ de→para explícito | ✅ imediato |
| **Cancelamento** | ✅ | ✅ imediato (é o buraco na agenda dele) |
| Início do dia | — | ✅ resumo da agenda |

O e-mail do profissional vem da **conta de login** dele (o perfil `Cabeleireiro`
não tem coluna de e-mail). Sem login criado, cai no console sem quebrar.

**Por qual canal** (`notificacoes/politica.py`): o dispatcher **não** envia por
todo canal configurado — cada evento declara seus canais. É o que impede um
canal pago (SMS) de passar a custar em todo evento quando for plugado.

| Canal | Quando ativa | Config |
|---|---|---|
| Console (dev) | sempre (log/rastreio) | — |
| E-mail | se `[smtp]` preenchido + destinatário com e-mail | Gmail app password |
| WhatsApp | se `[whatsapp]` preenchido + telefone + **template aprovado** | Meta Cloud API |
| SMS | *não implementado* — ver `politica.py` | — |

O `dispatcher` é tolerante a falha: o que não estiver configurado é ignorado sem
quebrar o agendamento.

---

## Deploy

- **App**: container no Render (veja `Dockerfile`). O **free tier hiberna após
  ~15 min** de inatividade e leva ~1 min para acordar — inaceitável para um salão
  em operação; use uma instância paga (sempre ativa + domínio próprio).
- **Lembretes**: o Render free não roda cron. Use **GitHub Actions cron**
  (grátis) — workflow em `.github/workflows/lembretes.yml` — apontando
  `DATABASE_URL` e credenciais como *secrets* do repositório.
- **⚠️ Fuso horário**: as datas de agendamento são hora local naive. A imagem
  base e os runners do GitHub rodam em **UTC**, então `TZ=America/Sao_Paulo` está
  fixado no `Dockerfile` e no workflow. Sem isso o app fica 3h deslocado **sem
  emitir erro algum**. Ao portar para outro provedor, garanta o mesmo.

### Checklist antes de entregar a um salão
```bash
python -m scripts.gerar_segredo   # gera SESSION_SECRET + senha do gestor
```
- [ ] 🔐 **`SESSION_SECRET`** trocado — **bloqueante**. O default (`dev-secret`)
      está no repositório e assina o cookie de sessão: com ele qualquer pessoa
      forja o login de qualquer usuário, inclusive o gestor. O app mostra um
      alerta na sidebar do gestor enquanto estiver no padrão.
- [ ] `[salao].nome` preenchido (aparece no app e em toda mensagem)
- [ ] `GESTOR_SENHA` trocada — o seed avisa se estiver na padrão
- [ ] SMTP configurado **e testado** (sem ele, tudo cai só no console)
- [ ] Login criado para cada cabeleireiro — senão eles não recebem os avisos
      de agenda, cancelamento e remarcação

---

## Roadmap (pós-MVP)
Confirmar presença no lembrete · lista de espera · fidelidade · SMS no lembrete
(canal já previsto em `politica.py`) · login com Google para clientes.

**Já entregue:** bloqueio de agenda (férias/folga) · NPS pós-atendimento ·
comunicação de mão dupla (cliente + profissional).
