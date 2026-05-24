# 🐳 Deploy com Docker

Tutorial para rodar o CreatorGate com Docker (localmente ou em qualquer servidor).

**Vantagem:** funciona igual em qualquer lugar (PC, VPS, AWS, Google Cloud, etc).

---

## 📋 Pré-requisitos

- **Docker** instalado — [docker.com/get-started](https://www.docker.com/get-started/)
- **Docker Compose** (vem junto com Docker Desktop)

### Verificar
```bash
docker --version
docker compose version
```

---

## 🚀 Modo rápido (com `docker compose`)

### Passo 1: Garanta que estes arquivos existem na raiz do projeto

O projeto já vem com `Dockerfile` e `docker-compose.yml`. Se não tiver, veja a seção [Criar do zero](#criar-arquivos-do-zero) abaixo.

### Passo 2: Configurar `.env`

Edite o `.env` com suas variáveis (especialmente `ADMIN_PASSWORD`, `SESSION_SECRET`, `BOT_TOKEN`).

### Passo 3: Subir os containers

```bash
cd creatorgate
docker compose up -d
```

Aguarde uns 30s. Veja os logs:
```bash
docker compose logs -f
```

### Passo 4: Acessar

- 🏠 http://localhost:5812/api/
- 🔐 http://localhost:5812/api/login

### Comandos úteis

```bash
docker compose ps              # ver containers rodando
docker compose logs -f         # ver logs em tempo real
docker compose restart         # reiniciar
docker compose down            # parar e remover containers
docker compose down -v         # parar e remover TUDO incluindo o banco
docker compose up -d --build   # rebuildar imagem (após mudanças no código)
```

---

## 🐘 Usando PostgreSQL em vez de SQLite

Edite o `docker-compose.yml` (já vem com a opção comentada):

```yaml
services:
  app:
    # ... config existente
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+psycopg2://creatorgate:senha@db:5432/creatorgate

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: creatorgate
      POSTGRES_PASSWORD: senha
      POSTGRES_DB: creatorgate
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

E adicione no `requirements.txt`:
```
psycopg2-binary>=2.9.9
```

Suba tudo:
```bash
docker compose up -d --build
```

---

## 📦 Buildar e publicar a imagem (Docker Hub)

Útil para deploy em servidores remotos sem precisar do código fonte.

```bash
# Login no Docker Hub
docker login

# Buildar
docker build -t SEU_USUARIO/creatorgate:latest .

# Publicar
docker push SEU_USUARIO/creatorgate:latest
```

No servidor remoto:
```bash
docker pull SEU_USUARIO/creatorgate:latest
docker run -d -p 5812:5812 --env-file .env -v $(pwd)/data:/app/data SEU_USUARIO/creatorgate:latest
```

---

## ☁️ Deploy em servidores cloud com Docker

### Fly.io (ótima opção)
```bash
# Instalar CLI: https://fly.io/docs/hands-on/install-flyctl/
fly launch          # detecta o Dockerfile automaticamente
fly deploy
fly secrets set ADMIN_PASSWORD=xxx SESSION_SECRET=yyy
```

### Google Cloud Run
```bash
gcloud run deploy creatorgate \
  --source . \
  --port 5812 \
  --region us-central1 \
  --allow-unauthenticated
```

### AWS App Runner
1. Console AWS → App Runner → Create Service
2. Source: Repository → conecte GitHub
3. Build: usa o Dockerfile automaticamente
4. Configure variáveis de ambiente
5. Deploy

### DigitalOcean App Platform
1. Console DO → Apps → Create App
2. Conecte GitHub
3. Detecta Dockerfile
4. Configure variáveis + recursos
5. Deploy

---

## 🔧 Criar arquivos do zero

Se você precisar criar manualmente:

### `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema (necessárias para algumas libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (aproveitar cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p data uploads/products uploads/previews uploads/protected

EXPOSE 5812

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5812/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5812"]
```

### `docker-compose.yml`
```yaml
services:
  app:
    build: .
    container_name: creatorgate
    ports:
      - "5812:5812"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    restart: unless-stopped
```

### `.dockerignore`
```
__pycache__
*.pyc
*.pyo
.venv
venv
data/*.db
.git
.github
.vscode
.idea
node_modules
*.log
```

---

## 🐛 Problemas comuns

### ❌ "permission denied" ao montar volume
No Linux, ajuste permissões:
```bash
sudo chown -R 1000:1000 ./data ./uploads
```

### ❌ "port already in use"
Mude a porta no `docker-compose.yml`:
```yaml
ports:
  - "8080:5812"   # acessa em :8080
```

### ❌ Container reinicia em loop
Veja os logs:
```bash
docker compose logs --tail 50 app
```

### ❌ Mudei o código e não atualiza
Imagem precisa ser rebuildada:
```bash
docker compose up -d --build
```

Ou use hot reload em dev: monte o código como volume:
```yaml
volumes:
  - .:/app
```
e ajuste o CMD para `uvicorn app.main:app --host 0.0.0.0 --port 5812 --reload`.

### ❌ Banco SQLite "database is locked"
SQLite + Docker + concorrência alta = problema. Use Postgres.

---

## 🔒 Produção com Docker

Checklist antes de ir para produção:

- [ ] `.env` com `SESSION_SECRET` aleatório e longo
- [ ] `ADMIN_PASSWORD` forte
- [ ] PostgreSQL em vez de SQLite
- [ ] Reverse proxy (nginx/Caddy) com HTTPS na frente
- [ ] Backup automático do volume de dados
- [ ] Logs centralizados (volume montado em `/var/log` ou serviço como Loki)
- [ ] Monitoramento (Uptime Kuma, Healthchecks.io)
- [ ] Rate limiting na frente (Cloudflare grátis funciona bem)

Exemplo de Caddy como reverse proxy (`Caddyfile`):
```
seudominio.com {
    reverse_proxy localhost:5812
}
```

Caddy faz HTTPS automático com Let's Encrypt!

---

## ⏭️ Próximos passos

- 🖥️ [Deploy em VPS próprio (passo a passo)](DEPLOY_VPS.md)
- 📘 [Voltar para Local](DEPLOY_LOCAL.md)
- ☁️ [Render](DEPLOY_RENDER.md) | 🚂 [Railway](DEPLOY_RAILWAY.md)
