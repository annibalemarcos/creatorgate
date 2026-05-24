# ☁️ Deploy no Render

Tutorial completo para subir o CreatorGate no [Render.com](https://render.com).

**Tempo estimado:** 15 minutos
**Custo:** Grátis (com limitações) ou $7/mês (Starter)

---

## 📋 O que você vai precisar

- Conta no [GitHub](https://github.com) (grátis)
- Conta no [Render](https://render.com) (grátis, cadastro com GitHub)
- O código do CreatorGate

---

## 📤 Passo 1: Subir código para o GitHub

### 1.1 Criar repositório
1. Acesse [github.com/new](https://github.com/new)
2. Nome: `creatorgate` (ou outro)
3. Marque **Private** (recomendado)
4. **NÃO** marque "Initialize with README"
5. Clique em **Create repository**

### 1.2 Subir o código

Na pasta do projeto:

```bash
cd creatorgate

# Inicializar git (se ainda não estiver)
git init
git add .
git commit -m "CreatorGate MVP"

# Conectar ao seu repositório
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/creatorgate.git
git push -u origin main
```

Se pedir login, use:
- **Username**: seu usuário GitHub
- **Password**: um **Personal Access Token** (gere em [github.com/settings/tokens](https://github.com/settings/tokens))

---

## 🚀 Passo 2: Deploy no Render

### Opção A — Deploy automático com `render.yaml` (recomendado)

O projeto já vem com um `render.yaml` pronto. Basta:

1. Acesse [render.com](https://render.com) e faça login
2. Clique em **New +** → **Blueprint**
3. Conecte sua conta GitHub se ainda não conectou
4. Selecione o repositório `creatorgate`
5. Render lê o `render.yaml` automaticamente e mostra os serviços
6. Clique em **Apply**
7. ✅ Render faz tudo: build, configura variáveis e deploya

### Opção B — Configuração manual

1. Acesse [render.com](https://render.com)
2. Clique em **New +** → **Web Service**
3. Conecte sua conta GitHub e selecione o repositório `creatorgate`
4. Preencha:

| Campo | Valor |
|-------|-------|
| **Name** | `creatorgate` |
| **Region** | Oregon (US) ou São Paulo (se quiser, mas é pago) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` (ou `Starter` $7/mês se quiser bot 24/7) |

5. Em **Environment Variables**, adicione:

| Key | Value | Notas |
|-----|-------|-------|
| `ADMIN_USERNAME` | `admin` | seu usuário |
| `ADMIN_PASSWORD` | `(senha forte)` | **TROQUE!** |
| `SESSION_SECRET` | `(string aleatória 64+ chars)` | gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `sqlite:///./data/app.db` | ou Postgres (veja abaixo) |
| `APP_BASE_URL` | `https://creatorgate.onrender.com` | sua URL Render |
| `ALLOW_ADULT_CONTENT` | `true` | ou `false` |
| `PLATFORM_COMMISSION_PERCENT` | `15` | |
| `BOT_TOKEN` | `(seu token do BotFather)` | opcional |
| `ENABLE_BOT` | `false` | só ative se for plano Starter |

6. Clique em **Create Web Service**

Aguarde 3-5 minutos. Quando aparecer "Live" em verde, está no ar!

---

## 💾 Passo 3: Persistir dados (IMPORTANTE!)

⚠️ **Sem disco persistente, o SQLite zera a cada deploy!**

### 3.1 Adicionar Disk no Render

1. No serviço criado, vá em **Settings** → **Disks**
2. Clique em **Add Disk**
3. Preencha:
   - **Name**: `creatorgate-data`
   - **Mount Path**: `/opt/render/project/src/data`
   - **Size**: `1 GB` (suficiente para muito uso)
4. Salve

> ⚠️ Adicionar disco **só funciona no plano Starter ($7/mês)** ou superior. No plano Free, considere usar Postgres (próximo passo).

### 3.2 (Alternativa Free) Usar Postgres em vez de SQLite

1. No Render, clique em **New +** → **PostgreSQL**
2. Plan: **Free** (90 dias) ou **Starter** ($7/mês)
3. Nome: `creatorgate-db`
4. Após criado, copie a **Internal Database URL**
5. Volte ao seu Web Service → **Environment Variables**
6. Atualize: `DATABASE_URL=postgresql+psycopg2://...` (a URL copiada)
7. Adicione `psycopg2-binary` no `requirements.txt`:
   ```
   psycopg2-binary>=2.9.9
   ```
8. Faça commit + push — Render redeploya automaticamente.

---

## 🌐 Passo 4: Acessar seu app

Sua URL será algo como: `https://creatorgate.onrender.com`

- 🏠 Loja: `https://creatorgate.onrender.com/api/`
- 🔐 Admin: `https://creatorgate.onrender.com/api/login`

⚠️ No plano **Free**, o app **dorme após 15min sem tráfego**. Ao acessar, leva ~30s para acordar. Isso é normal.

---

## 🤖 Passo 5: Ativar o bot Telegram

⚠️ **No plano Free, o bot vai parar de responder quando o serviço dormir.** Soluções:

### Solução A — Plano Starter ($7/mês)
Não dorme nunca. Bot fica ativo 24/7.

### Solução B — Keep-alive com UptimeRobot (gambiarra que funciona)
1. Acesse [uptimerobot.com](https://uptimerobot.com) (grátis)
2. **Add New Monitor**:
   - Type: `HTTP(s)`
   - URL: `https://creatorgate.onrender.com/api/health`
   - Interval: `5 minutes`
3. Pronto — vai fazer ping a cada 5min e impedir o sleep.

### Solução C — Webhook do Telegram (mais profissional)
Em vez de polling, o Telegram envia POSTs ao seu app. Mais complexo, mas é o jeito certo em produção. Eu posso te ajudar a implementar se você pedir.

### Habilitar bot
1. Crie o bot no [@BotFather](https://t.me/BotFather)
2. No Render → **Environment Variables**:
   - `BOT_TOKEN=7836271:AAH...`
   - `ENABLE_BOT=true`
3. Save → Render redeploya automaticamente
4. Procure seu bot no Telegram → `/start` ✅

---

## 🔄 Atualizando o app

Cada `git push` na branch `main` dispara um redeploy automático no Render.

```bash
# alterar código...
git add .
git commit -m "minha alteração"
git push
# Render detecta e redeploya em ~3 min
```

---

## 🩺 Monitoramento e logs

- **Logs em tempo real**: No serviço → aba **Logs**
- **Métricas**: aba **Metrics** (CPU, memória)
- **Health check**: Render automaticamente verifica `/api/health` (ajustável em Settings)

---

## 💰 Custos resumidos

| Recurso | Plano Free | Plano Starter |
|---------|-----------|---------------|
| Web Service | Grátis, dorme após 15min | $7/mês, sempre ativo |
| PostgreSQL | Grátis 90 dias, 256MB | $7/mês, 1GB |
| Disk persistente | ❌ não disponível | ✅ incluído |
| Bot Telegram 24/7 | Só com keep-alive | ✅ nativo |
| Domínio customizado | ✅ grátis | ✅ grátis |

**Setup mínimo decente:** Free + UptimeRobot = $0/mês
**Setup recomendado:** Starter + Postgres Free = $7/mês

---

## 🐛 Problemas comuns

### ❌ Build falha com "could not find pip"
No `Build Command`, use: `python -m pip install -r requirements.txt`

### ❌ "Application failed to respond"
Veja em **Logs** o erro real. Geralmente:
- Falta uma variável de ambiente
- Erro de sintaxe Python
- Banco não acessível

### ❌ Banco zerou após deploy
Você esqueceu de adicionar o **Disk persistente** ou migrar para Postgres.

### ❌ Bot não responde
- Verifique se `ENABLE_BOT=true` está setado
- Verifique se o `BOT_TOKEN` está correto (cole sem espaços)
- No plano Free, configure UptimeRobot

### ❌ "Module not found: psycopg2"
Adicione `psycopg2-binary>=2.9.9` no `requirements.txt` e faça push.

---

## ⏭️ Próximos passos

- 🚂 [Deploy no Railway](DEPLOY_RAILWAY.md) (alternativa ao Render, mais simples)
- 🐳 [Deploy com Docker](DEPLOY_DOCKER.md)
- 🖥️ [Deploy em VPS](DEPLOY_VPS.md)
