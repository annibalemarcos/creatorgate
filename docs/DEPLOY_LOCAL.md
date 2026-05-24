# 💻 Rodando o CreatorGate Localmente

Tutorial completo para rodar o CreatorGate no seu PC (Windows, Mac ou Linux).

---

## ✅ Pré-requisitos

- **Python 3.10 ou superior** — [baixar aqui](https://www.python.org/downloads/)
- **pip** (geralmente vem com o Python)
- **Git** (opcional, mas recomendado) — [git-scm.com](https://git-scm.com/)

### Verificar instalação
```bash
python --version      # deve mostrar Python 3.10+
pip --version
```

> 💡 No Windows, talvez precise usar `python3` ou `py` no lugar de `python`.

---

## 📦 Passo 1: Obter o código

### Opção A — Baixar o zip
1. Baixe o `creatorgate.zip`
2. Extraia em uma pasta da sua escolha (ex: `C:\projetos\creatorgate` ou `~/projetos/creatorgate`)
3. Abra o terminal nessa pasta

### Opção B — Clonar do GitHub (se já está num repo)
```bash
git clone https://github.com/SEU_USUARIO/creatorgate.git
cd creatorgate
```

---

## 🐍 Passo 2: Criar ambiente virtual (recomendado)

Isso isola as dependências do projeto do seu Python global.

### Linux / Mac
```bash
python -m venv venv
source venv/bin/activate
```

### Windows (CMD)
```cmd
python -m venv venv
venv\Scripts\activate
```

### Windows (PowerShell)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

> Se aparecer erro de permissão no PowerShell, rode antes:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

Quando o venv estiver ativo, você verá `(venv)` no início da linha do terminal.

---

## 📥 Passo 3: Instalar dependências

```bash
pip install -r requirements.txt
```

Espere finalizar (pode demorar 1-2 minutos na primeira vez).

---

## ⚙️ Passo 4: Configurar o `.env`

O arquivo `.env` já vem preenchido com valores padrão. Abra-o em qualquer editor de texto (Notepad, VS Code etc) para personalizar:

```dotenv
BOT_TOKEN=                                    # token do bot (opcional agora)
ADMIN_USERNAME=admin                          # usuário do painel admin
ADMIN_PASSWORD=admin123                       # ⚠️ TROQUE em produção!
DATABASE_URL=sqlite:///./data/app.db          # banco SQLite local
APP_BASE_URL=http://localhost:5812            # URL pública do seu app
ALLOW_ADULT_CONTENT=true                      # permite área +18
PLATFORM_COMMISSION_PERCENT=15                # comissão padrão (%)
SESSION_SECRET=change-me-in-production-please # cookie de sessão (gere uma string longa aleatória)
PIX_KEY_DEFAULT=                              # chave Pix da plataforma
PIX_INSTRUCTIONS=Envie o valor exato e confirme com o suporte
ENABLE_BOT=false                              # mude para true quando tiver BOT_TOKEN
```

> 💡 Para gerar um `SESSION_SECRET` seguro: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## 🚀 Passo 5: Rodar o app

```bash
python run.py
```

Você verá algo como:
```
INFO: Uvicorn running on http://0.0.0.0:5812 (Press CTRL+C to quit)
INFO: Application startup complete.
```

Pronto! Abra o navegador em:

| URL | Descrição |
|-----|-----------|
| http://localhost:5812/api/ | 🏠 Loja pública |
| http://localhost:5812/api/login | 🔐 Painel admin (admin/admin123) |
| http://localhost:5812/api/s/loja-da-ana | 🏪 Loja de exemplo |

---

## 🎯 Removendo o prefixo `/api` (uso local)

Por padrão o app usa `/api` como prefixo (necessário na hospedagem Emergent). Para rodar localmente sem isso, edite `app/main.py`:

**Antes:**
```python
app.include_router(public_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")
app.include_router(seller_router.router, prefix="/api")
```

**Depois:**
```python
app.include_router(public_router.router)
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(seller_router.router)
```

E também ajuste o mount dos arquivos estáticos:
```python
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

E o `<link rel="stylesheet" href="/api/static/style.css">` no `base.html` para `/static/style.css`.

Agora você acessa diretamente: `http://localhost:5812/`, `http://localhost:5812/login`, `http://localhost:5812/admin`, etc.

---

## 🤖 Passo 6 (opcional): Ativar o bot Telegram

### Criar o bot
1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Escolha um nome (ex: "CreatorGate Demo")
4. Escolha um username terminado em `_bot` (ex: `creatorgate_demo_bot`)
5. Copie o token (algo como `7836271:AAH...`)

### Configurar
No `.env`, preencha:
```dotenv
BOT_TOKEN=7836271:AAH...
ENABLE_BOT=true
```

Reinicie o app (`Ctrl+C` e rode `python run.py` de novo).

Procure seu bot no Telegram pelo username e envie `/start` — deve aparecer o menu!

---

## 🐛 Problemas comuns

### ❌ `pip: command not found`
Use `python -m pip install ...` no lugar.

### ❌ `Address already in use: 5812`
Outra aplicação está usando a porta. Mude no `run.py`:
```python
uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

### ❌ `ModuleNotFoundError: No module named 'app'`
Você precisa rodar **de dentro da pasta `creatorgate/`**, não de outra pasta.

### ❌ Banco de dados sumiu
Os dados ficam em `data/app.db`. Se o arquivo for deletado, o app recria com dados de exemplo no próximo start.

### ❌ Reset do banco
Para começar do zero:
```bash
rm data/app.db        # Linux/Mac
del data\app.db       # Windows
python run.py         # recria automaticamente
```

---

## 🔄 Parar o app

`Ctrl + C` no terminal onde está rodando.

Para desativar o venv: `deactivate`

---

## ⏭️ Próximos passos

- 📘 [Deploy no Render](DEPLOY_RENDER.md)
- 🚂 [Deploy no Railway](DEPLOY_RAILWAY.md)
- 🐳 [Deploy com Docker](DEPLOY_DOCKER.md)
- 🖥️ [Deploy em VPS](DEPLOY_VPS.md)
