# 🚂 Deploy no Railway

Tutorial para subir o CreatorGate no [Railway.app](https://railway.app).

**Tempo estimado:** 10 minutos
**Custo:** $5 USD de crédito grátis/mês (suficiente para apps pequenos)

> 💡 Railway é o mais fácil dos três (Render/Railway/Fly). Não tem sleep, não tem hassle.

---

## 📋 O que você vai precisar

- Conta no [GitHub](https://github.com)
- Conta no [Railway](https://railway.app) (login com GitHub)
- Cartão de crédito (Railway exige para verificação, mas só cobra após estourar $5)

---

## 📤 Passo 1: Subir o código para o GitHub

Mesmo processo do tutorial do Render:

```bash
cd creatorgate
git init
git add .
git commit -m "CreatorGate MVP"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/creatorgate.git
git push -u origin main
```

---

## 🚀 Passo 2: Deploy no Railway

### 2.1 Criar novo projeto

1. Acesse [railway.app](https://railway.app) e faça login
2. Clique em **New Project**
3. Selecione **Deploy from GitHub repo**
4. Autorize o Railway a acessar seus repos
5. Selecione `creatorgate`
6. Railway **detecta automaticamente que é Python** e começa o build

### 2.2 Configurar Start Command

Por padrão Railway tenta `python main.py`. Vamos corrigir:

1. No painel do projeto, clique no card do serviço (geralmente `creatorgate`)
2. Vá na aba **Settings**
3. Em **Deploy** → **Custom Start Command**, coloque:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Salve

### 2.3 Variáveis de ambiente

1. Vá na aba **Variables**
2. Clique em **+ New Variable** para cada uma:

| Key | Value | Notas |
|-----|-------|-------|
| `ADMIN_USERNAME` | `admin` | |
| `ADMIN_PASSWORD` | `(senha forte)` | **TROQUE!** |
| `SESSION_SECRET` | `(string aleatória)` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `sqlite:///./data/app.db` | |
| `ALLOW_ADULT_CONTENT` | `true` | |
| `PLATFORM_COMMISSION_PERCENT` | `15` | |
| `BOT_TOKEN` | `(opcional)` | |
| `ENABLE_BOT` | `false` | mude para `true` quando quiser |
| `APP_BASE_URL` | `(deixe vazio por enquanto)` | preenche no passo 4 |

> 💡 **Atalho**: no Railway dá pra colar tudo de uma vez em formato `.env`. Clique em **Raw Editor** e cole o conteúdo do seu `.env`.

### 2.4 Gerar domínio

1. Aba **Settings** → **Networking** → **Public Networking**
2. Clique em **Generate Domain**
3. Aparece algo como `creatorgate-production.up.railway.app`
4. Copie a URL e atualize a variável `APP_BASE_URL` com ela (com `https://`)

### 2.5 Deploy

Railway redeploya automaticamente após qualquer mudança em vars.
Aguarde ~2min e acesse a URL gerada.

✅ Pronto! Seu app está online.

---

## 💾 Passo 3: Persistir dados (volume)

⚠️ **Sem volume, SQLite zera a cada deploy!**

### 3.1 Adicionar Volume

1. No painel do serviço → **Settings** → **Volumes**
2. Clique em **+ New Volume**
3. Preencha:
   - **Mount Path**: `/app/data`
   - **Size**: `1 GB`
4. Salve

### 3.2 Ajustar `DATABASE_URL`

Atualize a variável para apontar para o volume:
```
DATABASE_URL=sqlite:////app/data/app.db
```
(4 barras: `sqlite:///` + caminho absoluto `/app/data/app.db`)

### 3.3 (Alternativa) Usar PostgreSQL

Railway tem Postgres gerenciado super fácil:

1. No projeto, clique em **+ New** → **Database** → **Add PostgreSQL**
2. Pronto, o banco está criado
3. Clique no serviço Postgres → aba **Variables** → copie `DATABASE_URL`
4. Volte ao seu app → Variables → atualize `DATABASE_URL` com o valor copiado
5. **Importante**: troque o início para `postgresql+psycopg2://...` (Railway dá `postgresql://`)
6. Adicione `psycopg2-binary>=2.9.9` no `requirements.txt` e faça push

---

## 🤖 Passo 4: Ativar bot Telegram

Railway **não dorme** mesmo no plano grátis, então o bot funciona perfeito 24/7 (até estourar os $5 de crédito).

1. Crie o bot no [@BotFather](https://t.me/BotFather) e copie o token
2. Em **Variables**:
   - `BOT_TOKEN=seu_token_aqui`
   - `ENABLE_BOT=true`
3. Railway redeploya automaticamente
4. Procure seu bot no Telegram e mande `/start` ✅

---

## 🔄 Atualizando o app

Cada `git push` na branch `main` dispara redeploy automático.

```bash
git add .
git commit -m "feature: nova funcionalidade"
git push
```

---

## 💰 Custos

Railway dá **$5 de crédito grátis por mês**. Consumo típico:
- App pequeno (1-50 usuários/dia): ~$2-3/mês → cabe no free
- App médio (100-500 usuários/dia): ~$5-10/mês
- Postgres pequeno: +$5/mês

Após esgotar o crédito, é cobrado por uso (CPU+RAM+rede).

| Plano | Crédito | Notas |
|-------|---------|-------|
| Trial | $5 grátis (uma vez) | Sem cartão |
| Hobby | $5/mês de uso grátis | Cartão obrigatório |
| Pro | $20/mês + uso | Times, mais recursos |

> ⚠️ Diferente do Render Free, Railway **cobra mesmo sem tráfego** (CPU idle ainda usa créditos), mas em compensação não tem sleep e o bot funciona sempre.

---

## 🩺 Logs e monitoramento

- **Logs**: aba **Deployments** → clique no deploy ativo → **View Logs**
- **Métricas**: aba **Metrics** (CPU, RAM, rede)
- **Variáveis**: aba **Variables**
- **Domínios**: Settings → Networking

---

## 🐛 Problemas comuns

### ❌ "Failed to listen on port"
Você esqueceu de usar `$PORT` no start command. Confira:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### ❌ "Application crashed"
Veja em **View Logs** o stacktrace. Geralmente é variável faltando ou erro de import.

### ❌ Banco resetou
Falta o Volume montado em `/app/data` + `DATABASE_URL` apontando lá.

### ❌ Bot não responde
- `ENABLE_BOT=true`?
- `BOT_TOKEN` está sem espaços/aspas?
- Logs mostram "Telegram bot started in background"?

### ❌ "Out of credits"
Adicione cartão na conta para continuar usando, ou migre para o Render Free.

---

## 🆚 Railway vs Render

| Critério | Railway | Render |
|----------|---------|--------|
| Setup inicial | ✅ Mais simples | OK |
| Sleep no free | ✅ Não dorme | ❌ Dorme após 15min |
| Crédito grátis | $5/mês | Free tier com sleep |
| Postgres grátis | $5 (parte do crédito) | 90 dias gratuito |
| Volumes | ✅ Fácil | ❌ Só pago |
| Domínio customizado | ✅ | ✅ |
| Deploy automático | ✅ git push | ✅ git push |

**Recomendação:**
- **Bot 24/7 + simples** → Railway
- **App só web, mais barato** → Render Free + UptimeRobot
- **Produção séria** → Render Starter ($7) ou Railway Hobby

---

## ⏭️ Próximos passos

- 🐳 [Deploy com Docker](DEPLOY_DOCKER.md)
- 🖥️ [Deploy em VPS próprio](DEPLOY_VPS.md)
- 📘 [Voltar ao Local](DEPLOY_LOCAL.md)
