(() => {
  'use strict';

  const services = JSON.parse(document.getElementById('services-data').textContent);
  const dockerStates = new Map(services.map((service) => [service.id, { state: 'unknown', health: null }]));
  const healthStates = new Map();
  const inProgress = new Set();
  const state = { category: 'all', status: 'all', query: '' };
  const groupsNode = document.getElementById('service-groups');
  const dialog = document.getElementById('confirm-dialog');
  let pendingService = null;
  let refreshRunning = false;
  let hasShownInitialError = false;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function getState(service) {
    if (service.id === 'dashboard') return { state: 'running', health: 'managed' };
    return dockerStates.get(service.id) || { state: 'unknown', health: null };
  }

  function statusLabel(service) {
    const current = getState(service);
    if (current.state === 'running') return 'Em execução';
    if (current.state === 'starting') return 'Iniciando';
    if (current.state === 'error') return 'Com falha';
    if (current.state === 'stopped') return 'Parado';
    if (current.state === 'not_created') return 'Não criado';
    return 'Verificando';
  }

  function healthLabel(service) {
    const current = getState(service);
    if (service.id === 'dashboard') return 'Painel ativo';
    const health = healthStates.get(service.id);
    if (current.state === 'not_created') return 'Sem container';
    if (current.state !== 'running') return current.state === 'unknown' ? 'Estado indisponível' : 'Verificação inativa';
    if (health === 'online') return 'Respondendo';
    if (health === 'offline') return 'Sem resposta';
    if (current.health === 'healthy') return 'Saudável';
    if (current.health === 'unhealthy') return 'Com falha';
    if (current.health === 'starting') return 'Verificando saúde';
    return 'Ativo';
  }

  function visibleServices() {
    return services.filter((service) => {
      const current = getState(service).state;
      const matchesCategory = state.category === 'all' || service.category === state.category;
      const matchesStatus = state.status === 'all' ||
        (state.status === 'running' && current === 'running') ||
        (state.status === 'stopped' && ['stopped', 'not_created', 'error'].includes(current));
      const haystack = `${service.name} ${service.id} ${service.category} ${service.description}`.toLocaleLowerCase('pt-BR');
      return matchesCategory && matchesStatus && haystack.includes(state.query);
    });
  }

  function addActionButton(container, label, action, className, disabled, title) {
    const button = make('button', `button ${className}${disabled ? ' button-disabled' : ''}`, label);
    button.type = 'button';
    button.dataset.serviceAction = action;
    button.disabled = disabled;
    if (title) button.title = title;
    container.append(button);
  }

  function renderService(service) {
    const current = getState(service);
    const card = make('article', 'service-card');
    card.dataset.state = current.state;
    const top = make('div', 'card-top');
    const ident = make('div', 'service-ident');
    ident.append(make('span', 'service-icon', service.icon));
    const titleWrap = make('div', 'service-title-wrap');
    titleWrap.append(make('h3', 'service-title', service.name));
    titleWrap.append(make('div', 'service-id', service.id));
    ident.append(titleWrap);
    const badge = make('span', `status-pill ${current.state}`, statusLabel(service));
    top.append(ident, badge);
    card.append(top);

    card.append(make('p', 'service-description', service.description));
    const meta = make('div', 'card-meta');
    const port = make('span');
    port.append(document.createTextNode('Porta '));
    port.append(make('strong', '', String(service.port)));
    meta.append(port, make('span', '', healthLabel(service)));
    card.append(meta);

    const actions = make('div', 'card-actions');
    const busy = inProgress.has(service.id);
    const isDashboard = service.id === 'dashboard';
    const exists = current.state !== 'not_created' && current.state !== 'unknown';
    if (!isDashboard && current.state === 'running') {
      addActionButton(actions, busy ? 'Aguarde…' : 'Desligar', 'stop', 'button-stop', busy, 'Desligar este container');
    } else if (!isDashboard && ['stopped', 'error'].includes(current.state)) {
      addActionButton(actions, busy ? 'Aguarde…' : 'Ligar', 'start', 'button-start', busy, 'Iniciar este container');
    } else if (!isDashboard && current.state === 'starting') {
      addActionButton(actions, 'Iniciando…', 'start', 'button-start', true);
    } else if (!isDashboard) {
      addActionButton(actions, current.state === 'not_created' ? 'Não criado' : 'Aguardando Docker', 'start', 'button-start', true,
        current.state === 'not_created' ? 'Este serviço não foi criado pelo perfil Compose ativo.' : 'Aguardando o estado do Docker.');
    }
    if (service.has_ui && service.url) {
      const link = make('a', 'button button-link', 'Abrir serviço ↗');
      link.href = service.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      actions.append(link);
    } else if (!exists && !isDashboard) {
      // Reserve the available space so cards remain aligned while status loads.
    }
    if (isDashboard) {
      const selfLink = make('a', 'button button-link', 'Painel ativo');
      selfLink.href = service.url;
      actions.append(selfLink);
    }
    card.append(actions);
    return card;
  }

  function render() {
    const filtered = visibleServices();
    groupsNode.replaceChildren();
    const grouped = new Map();
    for (const service of filtered) {
      if (!grouped.has(service.category)) grouped.set(service.category, []);
      grouped.get(service.category).push(service);
    }
    for (const [category, entries] of grouped) {
      const section = make('section', 'category-group');
      section.setAttribute('aria-label', category);
      const heading = make('h3', 'category-heading');
      heading.append(document.createTextNode(category));
      heading.append(make('span', 'category-count', String(entries.length)));
      section.append(heading);
      const grid = make('div', 'service-grid');
      for (const service of entries) grid.append(renderService(service));
      section.append(grid);
      groupsNode.append(section);
    }
    document.getElementById('empty-state').hidden = filtered.length > 0;
    document.getElementById('results-count').textContent = `${filtered.length} de ${services.length} serviços`;

    const running = services.filter((item) => getState(item).state === 'running').length;
    const stopped = services.filter((item) => ['stopped', 'not_created', 'error'].includes(getState(item).state)).length;
    const healthy = services.filter((item) => healthStates.get(item.id) === 'online').length;
    document.getElementById('count-total').textContent = String(services.length);
    document.getElementById('count-running').textContent = String(running);
    document.getElementById('count-healthy').textContent = String(healthy);
    document.getElementById('count-stopped').textContent = String(stopped);
  }

  function showToast(message, isError = false) {
    const toast = make('div', `toast${isError ? ' error' : ''}`, message);
    document.getElementById('toast-region').append(toast);
    window.setTimeout(() => toast.remove(), 4200);
  }

  async function refreshStatus(showError = false) {
    if (refreshRunning) return;
    refreshRunning = true;
    const refreshButton = document.getElementById('refresh-button');
    refreshButton.classList.add('is-loading');
    const [healthResult, dockerResult] = await Promise.allSettled([
      fetch('/api/status', { cache: 'no-store' }).then((response) => {
        if (!response.ok) throw new Error('Não foi possível consultar a saúde dos serviços.');
        return response.json();
      }),
      fetch('/api/control/services', { cache: 'no-store' }).then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Docker indisponível.');
        return payload;
      }),
    ]);

    if (healthResult.status === 'fulfilled') {
      for (const [id, value] of Object.entries(healthResult.value)) healthStates.set(id, value);
    }
    if (dockerResult.status === 'fulfilled') {
      for (const [id, value] of Object.entries(dockerResult.value.services)) dockerStates.set(id, value);
      const updated = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date());
      document.getElementById('last-updated').textContent = `Docker conectado · ${updated}`;
      document.querySelector('.updated-label').classList.remove('is-error');
    } else {
      document.getElementById('last-updated').textContent = 'Docker indisponível';
      document.querySelector('.updated-label').classList.add('is-error');
      if (showError || !hasShownInitialError) showToast(dockerResult.reason.message, true);
      hasShownInitialError = true;
    }
    if (healthResult.status === 'rejected' && showError) showToast(healthResult.reason.message, true);
    render();
    refreshRunning = false;
    refreshButton.classList.remove('is-loading');
  }

  async function performAction(service, action) {
    if (inProgress.has(service.id)) return;
    inProgress.add(service.id);
    render();
    try {
      const response = await fetch(`/api/control/services/${encodeURIComponent(service.id)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível alterar o serviço.');
      showToast(`${service.name}: comando para ${action === 'start' ? 'ligar' : 'desligar'} enviado.`);
      await refreshStatus();
    } catch (error) {
      showToast(error.message || 'Falha ao controlar o serviço.', true);
    } finally {
      inProgress.delete(service.id);
      render();
    }
  }

  groupsNode.addEventListener('click', (event) => {
    const button = event.target.closest('[data-service-action]');
    if (!button || button.disabled) return;
    const card = button.closest('.service-card');
    const service = services.find((item) => item.id === card.querySelector('.service-id').textContent);
    if (!service) return;
    if (button.dataset.serviceAction === 'stop') {
      pendingService = service;
      document.getElementById('dialog-title').textContent = `Desligar ${service.name}?`;
      document.getElementById('dialog-copy').textContent = 'Aplicações que dependem deste serviço podem ficar indisponíveis até que ele seja iniciado novamente.';
      dialog.showModal();
    } else {
      performAction(service, 'start');
    }
  });

  dialog.addEventListener('close', () => {
    if (dialog.returnValue === 'confirm' && pendingService) performAction(pendingService, 'stop');
    pendingService = null;
  });
  document.getElementById('refresh-button').addEventListener('click', () => refreshStatus(true));
  document.getElementById('search-input').addEventListener('input', (event) => {
    state.query = event.target.value.trim().toLocaleLowerCase('pt-BR');
    render();
  });
  document.getElementById('category-filter').addEventListener('change', (event) => {
    state.category = event.target.value;
    render();
  });
  document.querySelector('.status-filters').addEventListener('click', (event) => {
    const button = event.target.closest('[data-filter]');
    if (!button) return;
    state.status = button.dataset.filter;
    document.querySelectorAll('.filter-chip').forEach((chip) => {
      const selected = chip === button;
      chip.classList.toggle('selected', selected);
      chip.setAttribute('aria-pressed', String(selected));
    });
    render();
  });

  const categorySelect = document.getElementById('category-filter');
  for (const category of new Set(services.map((service) => service.category))) {
    const option = make('option', '', category);
    option.value = category;
    categorySelect.append(option);
  }
  render();
  refreshStatus();
  window.setInterval(() => refreshStatus(), 15000);
})();
