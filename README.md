# CreatorGate

**Marketplace de conteúdos digitais integrado ao Telegram** — multi-vendedor, com painel admin, painel do vendedor, lojas públicas e bot Telegram.

## ✨ Visão geral

- **Multi-vendedor**: cada criador tem sua mini-loja, produtos, saldo e painel
- **Bot Telegram (Aiogram)**: descoberta, compra, entrega automática
- **Painel web (FastAPI + Jinja2 + Bootstrap 5)**: admin completo + dashboard de vendedor
- **Pagamento Pix manual** confirmado pelo admin no MVP (base preparada para Mercado Pago)
- **Moderação +18, denúncias, logs e carteira/saques** completos

## 🛠 Stack

- Python 3.11+ • FastAPI • SQLAlchemy • SQLite
- Jinja2 + Bootstrap 5 (visual clean, cards brancos, terracota como cor primária)
- Aiogram 3 (bot Telegram)
- APScheduler (rotinas automáticas)

## 📦 Instalação

```bash
git clone <repo> creatorgate
cd creatorgate
pip install -r requirements.txt
cp .env.example .env       # edite suas variáveis
python run.py              # roda em http://localhost:5812
```

ou

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 5812
```

## ⚙️ Configuração (.env)

```dotenv
BOT_TOKEN=                      # token do bot via @BotFather
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
DATABASE_URL=sqlite:///./data/app.db
APP_BASE_URL=http://localhost:5812
ALLOW_ADULT_CONTENT=true
PLATFORM_COMMISSION_PERCENT=15
SESSION_SECRET=change-me
ENABLE_BOT=false                # mude para true após preencher BOT_TOKEN
```

## 🤖 Criar bot no Telegram

1. Abra [@BotFather](https://t.me/BotFather) no Telegram
2. Envie `/newbot`, escolha um nome e um username
3. Copie o token e cole em `BOT_TOKEN=` no `.env`
4. Defina `ENABLE_BOT=true`
5. Reinicie o app — o bot iniciará polling automaticamente em background

## 🚀 Como rodar

### Modo 1 — Tudo junto (bot + web)
```bash
python run.py
```
Acesse `http://localhost:5812`. O bot roda em background (lifespan).

### Modo 2 — Bot em processo separado (recomendado para produção)

No `.env`, deixe `ENABLE_BOT=false` e rode dois processos:

```bash
# Terminal 1 — Web
uvicorn app.main:app --host 0.0.0.0 --port 5812

# Terminal 2 — Bot
python -m app.bot
```

## 🔐 Acessos padrão

| Tipo | URL | Login | Senha |
|------|-----|-------|-------|
| **Admin** (URL oculta) | `/api/admin/login` | `admin` | `admin123` |
| Vendedor exemplo (ativo) | `/api/login` | `loja-da-ana` | `seller123` |
| Vendedor exemplo (pendente) | `/api/login` | `estudio-bruno` | `seller123` |
| **Novo cadastro de vendedor** | `/api/register` | — | — (você cria) |

> O slug do vendedor é usado como "usuário" no login. Veja em **Vendedores** no painel admin.
>
> 🔒 O login de admin **não aparece** nos links públicos — acesse direto pela URL `/api/admin/login`.

## 🧪 Fluxo completo para testar

### 1. Acessar admin
`http://localhost:5812/api/admin/login` → admin / admin123

### 2. Aprovar vendedor pendente
Menu **Vendedores** → clique em "Aprovar" no Estúdio Bruno.

### 3. Criar produto (como vendedor)
Logue como vendedor (slug + `seller123`) → **Meus produtos → Novo produto** → preencher e salvar.
Produtos +18 ou de vendedor sem produtos ativos ficam **pendentes**.

### 4. Aprovar produto
Volte ao admin → **Produtos** → "Aprovar".

### 5. Simular compra
- Abra a loja pública: `/api/s/{slug}` ou produto: `/api/p/{id}`
- Compre pelo bot do Telegram (deep link) **ou** simule manualmente:
  - O admin pode criar pedido via terminal/seed e usar **Marcar como pago** + **Entregar**.

### 6. Pagamento manual
- Comprador vê instruções Pix configuradas em **Configurações** do admin
- Admin marca pedido como **Pago** (`/api/admin/orders` → botão "Pago")
- Em seguida clica em **Entregar** → o bot envia automaticamente o conteúdo

### 7. Solicitar saque
Como vendedor → **Carteira** → preencher valor + chave Pix → solicitar.
Admin aprova em **Saques** e marca como **Pago**.

## 📂 Estrutura

```
creatorgate/
├── app/
│   ├── main.py            # FastAPI app + lifespan
│   ├── bot.py             # Aiogram bot
│   ├── config.py          # Settings (.env)
│   ├── database.py        # SQLAlchemy engine + Session
│   ├── models.py          # ORM models
│   ├── auth.py            # session-based auth
│   ├── seed.py            # dados iniciais
│   ├── scheduler.py       # APScheduler
│   ├── services/          # regras de negócio
│   ├── routers/           # endpoints FastAPI
│   ├── templates/         # Jinja2 (admin, seller, public)
│   └── static/            # CSS, JS
├── uploads/
│   ├── products/          # capas públicas
│   ├── previews/          # previews
│   └── protected/         # arquivos protegidos (entrega)
├── data/app.db
├── server.py              # entrypoint p/ uvicorn server:app (compat)
├── run.py                 # python run.py → porta 5812
├── requirements.txt
├── .env.example
└── README.md
```

## 🔒 Segurança e regras

- Arquivos protegidos ficam em `uploads/protected/` (não expostos por URL pública)
- Apenas extensões permitidas (`pdf, zip, mp3, mp4, jpg, ...`) e máximo 50 MB
- Vendedor suspenso/banido não pode criar produtos
- Produto inativo não pode ser comprado
- Usuário banido não pode comprar
- Denúncias críticas (menor de idade, sem consentimento, conteúdo ilegal) **suspendem o produto e bloqueiam o saldo do vendedor automaticamente**
- Logs em `moderation_logs` e `access_logs`

## 💰 Carteira e comissão

- Comissão padrão da plataforma: `PLATFORM_COMMISSION_PERCENT` (default 15%)
- Pode ser sobrescrita por **plano** (Start 15%, Pro 10%, Elite 7%) ou **comissão personalizada** pelo admin
- Quando o pedido é marcado como pago:
  1. valor líquido vai para o **saldo pendente** do vendedor
  2. após 7 dias (job APScheduler), passa para **disponível** automaticamente
  3. admin também pode mover manualmente

## 🛣 Próximos passos (roadmap)

- [ ] Mercado Pago Pix (preference + webhook) — endpoints base já existem em `services/orders.py`
- [ ] Telegram Stars como método alternativo
- [ ] Webhook do Telegram em vez de polling
- [ ] Upload de capas + galeria de produto
- [ ] Liberação automática 100% (cron + cron rules por plano)
- [ ] Stripe / PayPal para criadores internacionais
- [ ] Migração SQLite → Postgres (basta trocar `DATABASE_URL`)

## 🆘 Suporte

Em caso de dúvidas, abra uma issue ou contate o suporte.

---

**MVP funcional. Pronto para testes. 🎉**

---

## 📚 Tutoriais de Deploy

Veja a pasta [`docs/`](docs/) para tutoriais detalhados:

| Plataforma | Tempo | Custo |
|------------|-------|-------|
| 💻 [Local (PC)](docs/DEPLOY_LOCAL.md) | 10 min | Grátis |
| ☁️ [Render](docs/DEPLOY_RENDER.md) | 15 min | $0-7/mês |
| 🚂 [Railway](docs/DEPLOY_RAILWAY.md) | 10 min | $5/mês crédito |
| 🐳 [Docker](docs/DEPLOY_DOCKER.md) | 15 min | Varia |
| 🖥️ [VPS próprio](docs/DEPLOY_VPS.md) | 45 min | $4-6/mês |

Ou comece pelo [índice da documentação](docs/README.md).
