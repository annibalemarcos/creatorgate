// CreatorGate — notification polling + toast
(function() {
  const base = window.CG_NOTIF_BASE;
  if (!base) return;

  const bell = document.getElementById('notifBtn');
  const countEl = document.getElementById('notif-count');
  const ticketsBadge = document.getElementById('tickets-badge');
  const panel = document.getElementById('notifPanel');
  const list = document.getElementById('notifList');
  const markAllBtn = document.getElementById('notifMarkAll');
  if (!bell) return;

  let lastIds = new Set();

  async function fetchFeed() {
    try {
      const r = await fetch(base + '/notifications/feed', { credentials: 'same-origin' });
      if (!r.ok) return;
      const data = await r.json();
      renderCount(data.count);
      renderList(data.items);
      toastNew(data.items);
    } catch (e) { /* silent */ }
  }

  function renderCount(n) {
    if (n > 0) {
      countEl.style.display = '';
      countEl.textContent = n > 99 ? '99+' : n;
      if (ticketsBadge) {
        ticketsBadge.style.display = '';
        ticketsBadge.textContent = n;
      }
    } else {
      countEl.style.display = 'none';
      if (ticketsBadge) ticketsBadge.style.display = 'none';
    }
  }

  function renderList(items) {
    if (!list) return;
    if (!items.length) {
      list.innerHTML = '<div class="text-muted small p-2">Sem notificações novas.</div>';
      return;
    }
    list.innerHTML = items.map(n => `
      <a href="${n.link || '#'}" class="cg-notif-item" data-id="${n.id}">
        <div class="cg-notif-title">${escapeHtml(n.title)}</div>
        <div class="cg-notif-body">${escapeHtml(n.body || '')}</div>
        <div class="cg-notif-time">${new Date(n.created_at).toLocaleString('pt-BR')}</div>
      </a>
    `).join('');
    list.querySelectorAll('.cg-notif-item').forEach(el => {
      el.addEventListener('click', () => {
        fetch(base + '/notifications/' + el.dataset.id + '/read',
              { method: 'POST', credentials: 'same-origin' });
      });
    });
  }

  function toastNew(items) {
    items.forEach(n => {
      if (lastIds.has(n.id)) return;
      lastIds.add(n.id);
      if (lastIds.size > 200) lastIds = new Set([...lastIds].slice(-100));
      showToast(n);
    });
  }

  function showToast(n) {
    const container = ensureToastContainer();
    const el = document.createElement('div');
    el.className = 'cg-toast';
    el.innerHTML = `
      <div class="cg-toast-title"><i class="bi bi-bell-fill"></i> ${escapeHtml(n.title)}</div>
      <div class="cg-toast-body">${escapeHtml((n.body || '').slice(0, 120))}</div>
      ${n.link ? `<a href="${n.link}" class="cg-toast-link">Ver detalhes</a>` : ''}
    `;
    container.appendChild(el);
    setTimeout(() => el.classList.add('cg-toast-show'), 10);
    setTimeout(() => {
      el.classList.remove('cg-toast-show');
      setTimeout(() => el.remove(), 300);
    }, 6000);
  }

  function ensureToastContainer() {
    let c = document.getElementById('cg-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'cg-toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[c]));
  }

  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    if (panel) panel.style.display = (panel.style.display === 'none' ? 'block' : 'none');
  });
  document.addEventListener('click', (e) => {
    if (panel && !panel.contains(e.target) && e.target !== bell) panel.style.display = 'none';
  });
  if (markAllBtn) {
    markAllBtn.addEventListener('click', async () => {
      await fetch(base + '/notifications/read-all',
                  { method: 'POST', credentials: 'same-origin' });
      fetchFeed();
    });
  }

  // Initial load + poll every 20 seconds
  fetchFeed();
  setInterval(fetchFeed, 20000);
})();
