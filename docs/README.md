# 📚 Documentação do CreatorGate

Bem-vindo à documentação! Escolha como você quer rodar o app:

## 🚀 Tutoriais de Deploy

| Tutorial | Tempo | Custo | Dificuldade |
|----------|-------|-------|-------------|
| 💻 [Rodar Localmente](DEPLOY_LOCAL.md) | 10 min | Grátis | ⭐ Fácil |
| ☁️ [Render](DEPLOY_RENDER.md) | 15 min | $0-7/mês | ⭐⭐ Fácil |
| 🚂 [Railway](DEPLOY_RAILWAY.md) | 10 min | $5/mês crédito | ⭐⭐ Fácil |
| 🐳 [Docker](DEPLOY_DOCKER.md) | 15 min | Varia | ⭐⭐ Médio |
| 🖥️ [VPS próprio](DEPLOY_VPS.md) | 45 min | $4-6/mês | ⭐⭐⭐⭐ Avançado |

## 🎯 Qual escolher?

### Quero testar agora no meu PC
→ [DEPLOY_LOCAL.md](DEPLOY_LOCAL.md)

### Quero colocar online de graça (com algumas limitações)
→ [DEPLOY_RENDER.md](DEPLOY_RENDER.md) (free, mas app dorme após 15min)

### Quero o jeito mais fácil de subir online (com bot 24/7)
→ [DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md) ($5 grátis/mês, sem sleep)

### Quero portabilidade total (rodar em qualquer servidor)
→ [DEPLOY_DOCKER.md](DEPLOY_DOCKER.md)

### Quero controle total e barato a longo prazo
→ [DEPLOY_VPS.md](DEPLOY_VPS.md) (VPS Hetzner $4.50/mês com bot 24/7 + backups)

## 🤔 Comparativo rápido

| Critério | Local | Render Free | Render Starter | Railway | Docker/VPS |
|----------|-------|-------------|----------------|---------|------------|
| Custo | $0 | $0 | $7/mês | $5+/mês | $4-6/mês |
| Bot 24/7 | ✅ enquanto roda | ❌ dorme | ✅ | ✅ | ✅ |
| HTTPS automático | ❌ | ✅ | ✅ | ✅ | ✅ (Let's Encrypt) |
| Banco persiste | ✅ | ❌ (precisa Postgres) | ✅ | ✅ | ✅ |
| Domínio próprio | ❌ | ✅ | ✅ | ✅ | ✅ |
| Deploy automático (git push) | - | ✅ | ✅ | ✅ | ❌ manual |
| Performance | Sua máquina | Lenta (free) | Boa | Boa | Excelente |
| Backup automático | ❌ | ❌ | ❌ | ❌ | ✅ (você configura) |

## 📖 Outros recursos

- 📄 [README principal](../README.md) — visão geral e quickstart
- 🎨 Design system (cores, tipografia) em `app/static/style.css`
- 🤖 Bot Telegram: configure `BOT_TOKEN` no `.env` e `ENABLE_BOT=true`

## 💬 Suporte

Caso algo não funcione, verifique:
1. Logs do app (cada tutorial mostra como)
2. Variáveis de ambiente corretas
3. Banco de dados acessível
4. Porta correta no comando de start
