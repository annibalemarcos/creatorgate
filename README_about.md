# CreatorGate — visão geral do app

O **CreatorGate** é um **marketplace multi-vendedor de conteúdos digitais integrado ao Telegram**. Funciona como uma "Hotmart simplificada" onde criadores vendem produtos digitais (ebooks, packs, vídeos, áudios, cursos, fotos, assinaturas etc.) e a entrega acontece automaticamente pelo bot do Telegram.

---

## 🎯 O que ele resolve

1. **Para criadores**: lugar pronto para abrir uma "mini-loja" digital, cadastrar produtos, receber pagamento e entregar conteúdo sem precisar montar checkout, painel ou bot do zero.
2. **Para compradores**: marketplace centralizado onde descobrem criadores, compram pelo Telegram (familiar) e recebem o produto automaticamente na conversa do bot.
3. **Para o dono da plataforma (você)**: cobra **comissão por venda** (15% / 10% / 7% conforme plano) + **mensalidade do vendedor**, com painel completo de gestão e moderação.

---

## 👥 Três tipos de usuário

### 🛒 Comprador (via bot Telegram)
- Abre `t.me/SEU_BOT` → menu com: Ver lojas, Mais vendidos, Novidades, Buscar, Minhas compras, Quero vender, Suporte
- Clica em produto → confirma 18+ se for adulto → recebe Pix manual → admin confirma → **entrega automática** (texto, arquivo, link ou convite de grupo VIP)
- Pode **denunciar** produtos e **abrir tickets de suporte** pelo bot

### 🏪 Vendedor (painel web + bot)
- Cadastra-se em `/api/register` ou pelo bot — escolhe plano (Start R$ 29 / Pro R$ 59 / Elite R$ 99)
- Fica `pendente` até admin aprovar
- Painel próprio: dashboard, produtos, vendas, **carteira** (saldo pendente / disponível / bloqueado), **solicitar saque por Pix**, perfil
- Cada vendedor tem **mini-loja pública**: `/api/s/loja-da-ana` + deep link `t.me/BOT?start=seller_loja-da-ana`
- Cada produto tem deep link próprio: `t.me/BOT?start=product_123`
- Abre tickets de suporte para falar com a equipe

### 🛡 Staff (4 roles RBAC)
- **Super Admin**: tudo + gerencia equipe
- **Moderador**: produtos, denúncias, banir, tickets
- **Financeiro**: saques, pedidos, carteiras
- **Suporte**: só tickets + leitura geral

---

## ⚙️ Recursos principais

| Área | O que tem |
|------|-----------|
| **Vendedores** | Aprovar, suspender, banir, ajustar comissão, mudar plano |
| **Produtos** | 4 tipos de entrega (texto/arquivo/link/grupo Telegram), aprovação prévia, marcação +18, denúncias, suspensão automática para conteúdo crítico |
| **Pedidos** | Pix manual confirmado pelo admin (base pronta para Mercado Pago/Telegram Stars), cálculo automático de comissão + saldo do vendedor |
| **Carteira & Saques** | Saldo pendente → disponível em 7 dias (job APScheduler), saques via Pix com aprovação admin |
| **Moderação +18** | Confirmação obrigatória de 18+, aceite de termos, bloqueio automático de produtos com denúncia crítica (menor de idade, sem consentimento, ilegal) |
| **Tickets de suporte** | Threads com mensagens, categorias, prioridade, atribuição, notas internas, notificações por web (toast/badge) + push no Telegram |
| **Notificações** | Sino com badge, dropdown, toasts em tempo real (polling 20s) + push automático no bot |
| **Logs** | Moderação + acesso (auditoria) |
| **Páginas públicas** | Home, loja do vendedor, página do produto — todas indexáveis |

---

## 🛠 Stack técnica

- **Backend**: Python 3.11 · FastAPI · SQLAlchemy
- **Frontend**: Jinja2 + Bootstrap 5 (visual clean, terracota como cor primária)
- **DB**: SQLite (MVP)
- **Bot**: Aiogram 3 (rodando junto com FastAPI ou em processo separado)
- **Rotinas**: APScheduler (libera saldo pendente, futuras rotinas)
- **Porta padrão**: 5812

---

## 💰 Como você ganha dinheiro com isso

1. **Comissão por venda** (15% / 10% / 7% conforme plano do vendedor)
2. **Mensalidade do plano** (R$ 29 / R$ 59 / R$ 99)
3. **Possibilidade de cobrar destaque/anúncio** (não implementado, mas seria simples adicionar)

---

## 🚀 Em uma frase

> Plataforma SaaS onde criadores brasileiros montam loja digital em minutos, vendem pelo Telegram com Pix, e você cobra mensalidade + comissão — com painel admin profissional, equipe com permissões granulares e suporte por tickets integrado.

Quer que eu implemente o **dashboard de performance da equipe** ou outra evolução?