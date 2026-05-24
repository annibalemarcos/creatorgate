# 🖥️ Deploy em VPS (Servidor próprio)

Tutorial completo para subir o CreatorGate em um servidor Linux (Ubuntu/Debian). Ideal para quem quer **controle total** e custo mais baixo a longo prazo.

**Tempo estimado:** 45 minutos
**Custo:** $4-6 USD/mês (Hetzner, Contabo, DigitalOcean, Vultr)

---

## 📋 O que você vai precisar

- Uma VPS com Ubuntu 22.04 LTS (recomendado)
  - **Mínimo**: 1 vCPU, 1 GB RAM, 20 GB disco
  - Provedores baratos: [Hetzner](https://hetzner.com) (~$4), [Contabo](https://contabo.com), [Vultr](https://vultr.com), [DigitalOcean](https://digitalocean.com)
- Um domínio (opcional mas recomendado) — [Namecheap](https://namecheap.com), [Cloudflare](https://cloudflare.com), [Registro.br](https://registro.br)
- Acesso SSH ao servidor

---

## 🎯 Arquitetura final

```
Internet → Cloudflare (DNS + HTTPS) → nginx (reverse proxy) → uvicorn (porta 5812)
                                                            ↓
                                                       SQLite ou Postgres
```

---

## 🚀 Passo 1: Acessar e atualizar o servidor

```bash
ssh root@SEU_IP

# Atualizar pacotes
apt update && apt upgrade -y

# Instalar utilitários básicos
apt install -y git curl ufw fail2ban
```

---

## 🔒 Passo 2: Segurança básica

### 2.1 Criar usuário não-root
```bash
adduser creatorgate
usermod -aG sudo creatorgate
```

### 2.2 Configurar SSH com chave (opcional mas recomendado)

Na sua máquina local:
```bash
ssh-copy-id creatorgate@SEU_IP
```

No servidor, edite `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
PermitRootLogin no
```

Reinicie:
```bash
systemctl restart ssh
```

### 2.3 Firewall
```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

A partir daqui, logue como `creatorgate`:
```bash
exit
ssh creatorgate@SEU_IP
```

---

## 🐍 Passo 3: Instalar Python e dependências

```bash
sudo apt install -y python3 python3-pip python3-venv

# Verificar versão (deve ser 3.10+)
python3 --version
```

---

## 📥 Passo 4: Baixar o código

### Via Git (recomendado)
```bash
cd ~
git clone https://github.com/SEU_USUARIO/creatorgate.git
cd creatorgate
```

### Via upload manual
Da sua máquina local:
```bash
scp creatorgate.zip creatorgate@SEU_IP:~/
```
No servidor:
```bash
unzip creatorgate.zip
cd creatorgate
```

---

## 🛠️ Passo 5: Configurar o app

```bash
# Criar venv
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
nano .env
```

Ajuste especialmente:
```dotenv
ADMIN_PASSWORD=senha-bem-forte-aqui
SESSION_SECRET=cole-aqui-uma-string-de-64-caracteres-aleatorios
APP_BASE_URL=https://seudominio.com
BOT_TOKEN=seu_token_telegram
ENABLE_BOT=true
```

Gerar SESSION_SECRET seguro:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Testar se sobe:
```bash
python run.py
# Ctrl+C para parar quando aparecer "Application startup complete"
```

---

## 🔄 Passo 6: Configurar systemd (rodar como serviço)

Para o app ficar rodando 24/7 e reiniciar automaticamente.

```bash
sudo nano /etc/systemd/system/creatorgate.service
```

Cole:
```ini
[Unit]
Description=CreatorGate FastAPI app
After=network.target

[Service]
Type=simple
User=creatorgate
Group=creatorgate
WorkingDirectory=/home/creatorgate/creatorgate
Environment="PATH=/home/creatorgate/creatorgate/venv/bin"
EnvironmentFile=/home/creatorgate/creatorgate/.env
ExecStart=/home/creatorgate/creatorgate/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 5812 --workers 2
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/creatorgate/app.log
StandardError=append:/var/log/creatorgate/app-error.log

[Install]
WantedBy=multi-user.target
```

Criar pasta de logs:
```bash
sudo mkdir -p /var/log/creatorgate
sudo chown creatorgate:creatorgate /var/log/creatorgate
```

Ativar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable creatorgate
sudo systemctl start creatorgate

# Verificar status
sudo systemctl status creatorgate

# Ver logs em tempo real
sudo tail -f /var/log/creatorgate/app.log
```

Teste local:
```bash
curl http://localhost:5812/api/health
# Deve retornar {"status":"ok","service":"CreatorGate"}
```

---

## 🌐 Passo 7: Configurar nginx (reverse proxy)

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/creatorgate
```

Cole:
```nginx
server {
    listen 80;
    server_name seudominio.com www.seudominio.com;

    client_max_body_size 60M;

    # Static files servidos diretamente pelo nginx (performance)
    location /api/static/ {
        alias /home/creatorgate/creatorgate/app/static/;
        expires 7d;
    }

    location /api/uploads/products/ {
        alias /home/creatorgate/creatorgate/uploads/products/;
        expires 30d;
    }

    # Tudo mais vai pro FastAPI
    location / {
        proxy_pass http://127.0.0.1:5812;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # Bloquear acesso direto a arquivos protegidos
    location /uploads/protected/ {
        deny all;
        return 403;
    }
}
```

Ativar:
```bash
sudo ln -s /etc/nginx/sites-available/creatorgate /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t                  # testar config
sudo systemctl restart nginx
```

Aponte seu domínio (registro A) para o IP da VPS no painel do seu provedor de domínio.

---

## 🔐 Passo 8: HTTPS gratuito com Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d seudominio.com -d www.seudominio.com
```

Siga as instruções. Vai pedir email e aceitar termos.

✅ HTTPS configurado! Acesse `https://seudominio.com` 🎉

Renovação automática (certbot já configura):
```bash
sudo systemctl status certbot.timer
```

---

## 🐘 Passo 9 (opcional): Migrar para PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib

# Criar usuário e banco
sudo -u postgres psql
```

Dentro do `psql`:
```sql
CREATE USER creatorgate WITH PASSWORD 'senha-do-banco';
CREATE DATABASE creatorgate_db OWNER creatorgate;
GRANT ALL PRIVILEGES ON DATABASE creatorgate_db TO creatorgate;
\q
```

No `.env`:
```
DATABASE_URL=postgresql+psycopg2://creatorgate:senha-do-banco@localhost/creatorgate_db
```

Instalar driver Python:
```bash
source venv/bin/activate
pip install psycopg2-binary
echo "psycopg2-binary>=2.9.9" >> requirements.txt
```

Reiniciar:
```bash
sudo systemctl restart creatorgate
```

---

## 💾 Passo 10: Backup automático

### Backup do banco e uploads

Crie `/home/creatorgate/backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR=/home/creatorgate/backups
mkdir -p $BACKUP_DIR

# SQLite
if [ -f /home/creatorgate/creatorgate/data/app.db ]; then
  cp /home/creatorgate/creatorgate/data/app.db $BACKUP_DIR/app-$DATE.db
fi

# Postgres (se estiver usando)
# pg_dump -U creatorgate creatorgate_db > $BACKUP_DIR/db-$DATE.sql

# Uploads
tar czf $BACKUP_DIR/uploads-$DATE.tar.gz -C /home/creatorgate/creatorgate uploads

# Limpar backups com mais de 30 dias
find $BACKUP_DIR -mtime +30 -delete

echo "Backup $DATE concluído"
```

Tornar executável e agendar:
```bash
chmod +x /home/creatorgate/backup.sh
crontab -e
```

Adicione (backup diário às 3h):
```
0 3 * * * /home/creatorgate/backup.sh >> /var/log/creatorgate/backup.log 2>&1
```

### Backup off-site (recomendado)

Configure `rclone` para enviar para Google Drive, S3, Backblaze B2 (super barato):

```bash
sudo apt install -y rclone
rclone config   # siga o wizard
```

Adicione ao backup.sh:
```bash
rclone copy $BACKUP_DIR/ remote:creatorgate-backups/
```

---

## 🔄 Atualizando o app

```bash
ssh creatorgate@SEU_IP
cd creatorgate
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart creatorgate
```

Ou crie um script `deploy.sh`:
```bash
#!/bin/bash
cd /home/creatorgate/creatorgate
git pull
./venv/bin/pip install -r requirements.txt
sudo systemctl restart creatorgate
echo "Deploy concluído"
```

---

## 🛡️ Segurança extra

### Fail2ban (já instalado)
Protege contra brute-force SSH e nginx.

```bash
sudo systemctl status fail2ban
```

### Cloudflare (recomendado)
1. Crie conta grátis em [cloudflare.com](https://cloudflare.com)
2. Adicione seu domínio
3. Mude os nameservers no provedor de domínio para os da Cloudflare
4. Ative:
   - SSL/TLS: **Full (strict)**
   - Security → Bot Fight Mode
   - Speed → Auto Minify (HTML/CSS/JS)
   - Caching → Browser Cache TTL: 4 horas

Bônus: protege contra DDoS automaticamente!

### Atualizações automáticas de segurança
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 📊 Monitoramento

### Uptime Kuma (auto-hospedado)
Lindo dashboard de monitoramento. Rode com Docker em outro container:
```bash
docker run -d -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma
```

### Healthchecks.io (grátis externo)
1. Conta em [healthchecks.io](https://healthchecks.io)
2. Crie um check com URL `https://seudominio.com/api/health`
3. Alerta por email/Telegram/Slack se cair

---

## 💰 Custos finais

| Item | Custo |
|------|-------|
| VPS Hetzner CX22 (4GB RAM) | $4.50/mês |
| Domínio .com | ~$10/ano |
| Cloudflare | Grátis |
| Let's Encrypt SSL | Grátis |
| Backup Backblaze B2 | ~$1/mês para 50GB |
| **Total** | **~$6/mês** |

Muito mais barato que Render/Railway para uso médio/alto, com controle total.

---

## 🐛 Problemas comuns

### ❌ Service falhando
```bash
sudo systemctl status creatorgate
sudo journalctl -u creatorgate -f
```

### ❌ 502 Bad Gateway no nginx
App não está rodando. Confira `systemctl status creatorgate`.

### ❌ 504 Gateway Timeout
Aumente o `proxy_read_timeout` no nginx para 300s.

### ❌ Permissão negada em uploads
```bash
sudo chown -R creatorgate:creatorgate /home/creatorgate/creatorgate/uploads
chmod -R 755 uploads
```

### ❌ Disk cheio
```bash
df -h
sudo du -sh /var/log/* /home/* | sort -h | tail -20
```

---

## 🎓 Comandos úteis do dia a dia

```bash
# Status
sudo systemctl status creatorgate nginx

# Logs
sudo tail -f /var/log/creatorgate/app.log
sudo tail -f /var/log/nginx/access.log

# Reiniciar
sudo systemctl restart creatorgate
sudo systemctl reload nginx

# Ver uso
htop                  # CPU e RAM
df -h                 # disco
sudo netstat -tlnp    # portas em uso
```

---

## ⏭️ Próximos passos

- 📘 [Voltar para Local](DEPLOY_LOCAL.md)
- ☁️ [Render](DEPLOY_RENDER.md) | 🚂 [Railway](DEPLOY_RAILWAY.md)
- 🐳 [Docker](DEPLOY_DOCKER.md)
