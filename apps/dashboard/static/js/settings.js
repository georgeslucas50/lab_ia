(() => {
  'use strict';

  const services = JSON.parse(document.getElementById('settings-data').textContent);
  const list = document.getElementById('reset-service-list');
  const dialog = document.getElementById('reset-dialog');
  const input = document.getElementById('reset-confirm-input');
  const confirmButton = document.getElementById('reset-confirm-button');
  const progress = document.getElementById('reset-progress');
  const updateStatus = document.getElementById('update-status');
  const updateStatusText = document.getElementById('update-status-text');
  const updateVersion = document.getElementById('update-version');
  const updateProgress = document.getElementById('update-progress');
  const updateCheckButton = document.getElementById('check-updates-button');
  const updateApplyButton = document.getElementById('apply-update-button');
  const updateDialog = document.getElementById('update-dialog');
  const updateInput = document.getElementById('update-confirm-input');
  const updateConfirmButton = document.getElementById('update-confirm-button');
  let pendingReset = null;
  let activeJobId = null;
  let activeUpdateJobId = null;
  let currentUpdateStatus = null;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function showToast(message, isError = false) {
    const toast = make('div', `toast${isError ? ' error' : ''}`, message);
    document.getElementById('toast-region').append(toast);
    window.setTimeout(() => toast.remove(), 5000);
  }

  function showUpdateStatus(message, state = 'idle') {
    updateStatus.dataset.state = state;
    updateStatusText.textContent = message;
  }

  function renderUpdateStatus(status) {
    currentUpdateStatus = status;
    const failed = String(status.message || '').startsWith('Não foi possível');
    const state = status.canUpdate ? 'ready' : (status.dirty ? 'warning' : (failed ? 'error' : 'idle'));
    showUpdateStatus(status.message || 'Estado do Git atualizado.', state);
    const versions = [];
    if (status.branch) versions.push(`branch ${status.branch}`);
    if (status.currentCommit) versions.push(`local ${status.currentCommit}`);
    if (status.remoteCommit) versions.push(`GitHub ${status.remoteCommit}`);
    updateVersion.textContent = versions.join(' · ');
    updateVersion.hidden = versions.length === 0;
    updateApplyButton.disabled = !status.canUpdate || Boolean(activeUpdateJobId);
    updateApplyButton.textContent = status.pendingApply ? 'Tentar aplicar novamente' : 'Atualizar sistema';
  }

  function setUpdateBusy(busy) {
    updateCheckButton.disabled = busy;
    updateApplyButton.disabled = busy || !currentUpdateStatus?.canUpdate;
    updateCheckButton.textContent = busy ? 'Verificando…' : 'Verificar atualizações';
  }

  function setUpdateProgress(job, state = job.status) {
    updateProgress.hidden = false;
    updateProgress.dataset.state = state;
    document.getElementById('update-progress-phase').textContent = job.phase || 'Atualização em andamento';
    document.getElementById('update-progress-message').textContent = job.message || '';
  }

  function renderServices() {
    const grouped = new Map();
    for (const service of services) {
      if (!grouped.has(service.category)) grouped.set(service.category, []);
      grouped.get(service.category).push(service);
    }

    for (const [category, entries] of grouped) {
      const section = make('section', 'reset-category');
      section.setAttribute('aria-label', category);
      const heading = make('h3', 'category-heading', category);
      heading.append(make('span', 'category-count', String(entries.length)));
      section.append(heading);

      for (const service of entries) {
        const row = make('article', 'reset-service-row');
        const ident = make('div', 'reset-service-ident');
        ident.append(make('span', 'service-icon', service.icon));
        const text = make('div');
        text.append(make('h3', '', service.name), make('p', '', service.id));
        ident.append(text);

        const effect = make('p', `reset-service-effect${service.warning ? ' is-warning' : ''}`, service.description);
        const button = make('button', 'button button-stop', 'Zerar serviço');
        button.type = 'button';
        button.dataset.resetService = service.id;
        button.setAttribute('aria-label', `Zerar dados de ${service.name}`);
        row.append(ident, effect, button);
        section.append(row);
      }
      list.append(section);
    }
  }

  function openReset(scope, service = null) {
    pendingReset = { scope, service };
    const isFullReset = scope === 'all';
    const token = isFullReset ? 'ZERAR LABORATÓRIO' : `ZERAR ${service.id.toUpperCase()}`;
    document.getElementById('reset-dialog-title').textContent = isFullReset
      ? 'Zerar todo o laboratório?'
      : `Zerar ${service.name}?`;
    document.getElementById('reset-dialog-copy').textContent = isFullReset
      ? 'Esta ação apaga os dados de todos os serviços, incluindo notebooks, conversas, fluxos, bancos, coleções, caches e modelos locais. Ela não pode ser desfeita.'
      : service.description;

    const warning = document.getElementById('reset-dialog-warning');
    warning.textContent = service?.warning || (isFullReset
      ? 'Os serviços em execução serão parados durante a limpeza. O laboratório tentará restaurar o estado de execução anterior ao final.'
      : 'Os dados apagados não podem ser recuperados.');
    warning.hidden = false;
    document.getElementById('reset-confirm-token').textContent = token;
    document.getElementById('reset-input-error').hidden = true;
    input.value = '';
    confirmButton.disabled = true;
    confirmButton.textContent = isFullReset ? 'Zerar laboratório' : 'Zerar serviço';
    dialog.showModal();
    input.focus();
  }

  function setProgress(job, state = job.status) {
    progress.hidden = false;
    progress.dataset.state = state;
    document.getElementById('reset-progress-phase').textContent = job.phase || 'Reset em andamento';
    document.getElementById('reset-progress-message').textContent = job.message || '';
  }

  function setBusy(busy) {
    document.getElementById('reset-all-button').disabled = busy;
    list.querySelectorAll('[data-reset-service]').forEach((button) => {
      button.disabled = busy;
      if (busy) button.textContent = 'Aguarde…';
      else button.textContent = 'Zerar serviço';
    });
    if (busy) document.getElementById('reset-all-button').textContent = 'Reset em andamento…';
    else document.getElementById('reset-all-button').textContent = 'Zerar tudo';
  }

  async function watchJob(jobId) {
    activeJobId = jobId;
    setBusy(true);
    setProgress({ status: 'running', phase: 'Preparando o reset', message: 'Consultando o estado da operação.' });
    try {
      while (activeJobId === jobId) {
        await new Promise((resolve) => window.setTimeout(resolve, 1100));
        const response = await fetch(`/api/control/reset/jobs/${encodeURIComponent(jobId)}`, { cache: 'no-store' });
        const job = await response.json();
        if (!response.ok) throw new Error(job.detail || 'Não foi possível acompanhar o reset.');
        setProgress(job);
        if (['complete', 'partial', 'error'].includes(job.status)) {
          activeJobId = null;
          setBusy(false);
          if (job.status === 'complete') showToast(job.message || 'Reset concluído.');
          else showToast(job.message || 'O reset foi interrompido.', true);
          return;
        }
      }
    } catch (error) {
      activeJobId = null;
      setBusy(false);
      setProgress({ status: 'partial', phase: 'Acompanhamento interrompido', message: error.message || 'Recarregue a página para consultar a operação.' }, 'partial');
      showToast(error.message || 'Falha ao acompanhar o reset.', true);
    }
  }

  async function startReset(pending) {
    const confirmation = pending.scope === 'all'
      ? 'ZERAR LABORATÓRIO'
      : `ZERAR ${pending.service.id.toUpperCase()}`;
    const url = pending.scope === 'all'
      ? '/api/control/reset/all'
      : `/api/control/reset/service/${encodeURIComponent(pending.service.id)}`;
    setBusy(true);
    setProgress({ status: 'queued', phase: 'Solicitando reset', message: 'Aguarde enquanto o dashboard prepara a operação.' });
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível iniciar o reset.');
      await watchJob(payload.jobId);
    } catch (error) {
      setBusy(false);
      progress.dataset.state = 'error';
      document.getElementById('reset-progress-phase').textContent = 'Não foi possível iniciar';
      document.getElementById('reset-progress-message').textContent = error.message || 'Verifique o Docker e tente novamente.';
      showToast(error.message || 'Falha ao iniciar o reset.', true);
    }
  }

  async function refreshUpdateStatus(refresh = true) {
    setUpdateBusy(true);
    showUpdateStatus(refresh ? 'Consultando o branch remoto…' : 'Lendo o estado local do Git…');
    try {
      const suffix = refresh ? '?refresh=true' : '';
      const response = await fetch(`/api/control/updates/status${suffix}`, { cache: 'no-store' });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível consultar o GitHub.');
      renderUpdateStatus(payload);
      if (payload.job && ['queued', 'running'].includes(payload.job.status)) {
        await watchUpdateJob(payload.job.id);
      }
    } catch (error) {
      showUpdateStatus(error.message || 'Falha ao consultar atualizações.', 'error');
      updateApplyButton.disabled = true;
    } finally {
      updateCheckButton.disabled = Boolean(activeUpdateJobId);
      updateCheckButton.textContent = 'Verificar atualizações';
      if (!activeUpdateJobId) updateApplyButton.disabled = !currentUpdateStatus?.canUpdate;
    }
  }

  async function watchUpdateJob(jobId) {
    activeUpdateJobId = jobId;
    setUpdateBusy(true);
    setUpdateProgress({ status: 'running', phase: 'Preparando atualização', message: 'Acompanhando o processo. O dashboard pode reiniciar durante a aplicação.' });
    const deadline = Date.now() + 30 * 60 * 1000;
    try {
      while (activeUpdateJobId === jobId && Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, 1600));
        let response;
        let job;
        try {
          response = await fetch(`/api/control/updates/jobs/${encodeURIComponent(jobId)}`, { cache: 'no-store' });
          job = await response.json();
        } catch (_) {
          setUpdateProgress({ status: 'running', phase: 'Reconectando ao dashboard', message: 'O painel está reiniciando. A atualização continua em segundo plano.' });
          continue;
        }
        if (!response.ok) {
          if ([502, 503, 504].includes(response.status)) {
            setUpdateProgress({ status: 'running', phase: 'Reconectando ao serviço de atualização', message: 'O serviço está sendo atualizado e voltará a responder em instantes.' });
            continue;
          }
          throw new Error(job.detail || 'Não foi possível acompanhar a atualização.');
        }
        setUpdateProgress(job);
        if (['complete', 'error', 'partial'].includes(job.status)) {
          activeUpdateJobId = null;
          setUpdateBusy(false);
          if (job.status === 'complete') {
            showToast(job.message || 'Laboratório atualizado.');
            await refreshUpdateStatus(false);
          } else {
            showToast(job.message || 'A atualização foi interrompida.', true);
            await refreshUpdateStatus(false);
          }
          return;
        }
      }
      if (activeUpdateJobId === jobId) {
        activeUpdateJobId = null;
        setUpdateProgress({ status: 'error', phase: 'Acompanhamento expirado', message: 'O estado final não chegou ao painel. Verifique os containers e consulte as atualizações novamente.' }, 'error');
        setUpdateBusy(false);
      }
    } catch (error) {
      activeUpdateJobId = null;
      setUpdateProgress({ status: 'error', phase: 'Acompanhamento interrompido', message: error.message || 'Consulte novamente o estado do Git.' }, 'error');
      setUpdateBusy(false);
      showToast(error.message || 'Falha ao acompanhar a atualização.', true);
    }
  }

  async function startUpdate() {
    setUpdateBusy(true);
    setUpdateProgress({ status: 'queued', phase: 'Solicitando atualização', message: 'O atualizador vai sincronizar o Git e aplicar as alterações.' });
    try {
      const response = await fetch('/api/control/updates/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation: 'ATUALIZAR LABORATÓRIO' }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível iniciar a atualização.');
      await watchUpdateJob(payload.jobId);
    } catch (error) {
      setUpdateBusy(false);
      setUpdateProgress({ status: 'error', phase: 'Não foi possível iniciar', message: error.message || 'Verifique o Docker e tente novamente.' }, 'error');
      showToast(error.message || 'Falha ao iniciar a atualização.', true);
    }
  }

  document.getElementById('reset-all-button').addEventListener('click', () => openReset('all'));
  list.addEventListener('click', (event) => {
    const button = event.target.closest('[data-reset-service]');
    if (!button || button.disabled) return;
    const service = services.find((entry) => entry.id === button.dataset.resetService);
    if (service) openReset('service', service);
  });

  input.addEventListener('input', () => {
    const token = pendingReset?.scope === 'all'
      ? 'ZERAR LABORATÓRIO'
      : `ZERAR ${pendingReset?.service?.id.toUpperCase() || ''}`;
    confirmButton.disabled = input.value !== token;
    document.getElementById('reset-input-error').hidden = true;
  });

  confirmButton.addEventListener('click', () => {
    if (!pendingReset) return;
    const expected = pendingReset.scope === 'all'
      ? 'ZERAR LABORATÓRIO'
      : `ZERAR ${pendingReset.service.id.toUpperCase()}`;
    if (input.value !== expected) {
      document.getElementById('reset-input-error').hidden = false;
      return;
    }
    const selected = pendingReset;
    pendingReset = null;
    dialog.close('confirm');
    startReset(selected);
  });

  document.getElementById('reset-cancel-button').addEventListener('click', () => dialog.close('cancel'));
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close('cancel');
  });

  updateCheckButton.addEventListener('click', () => refreshUpdateStatus(true));
  updateApplyButton.addEventListener('click', () => {
    if (!currentUpdateStatus?.canUpdate) return;
    updateInput.value = '';
    updateConfirmButton.disabled = true;
    document.getElementById('update-input-error').hidden = true;
    updateDialog.showModal();
    updateInput.focus();
  });
  updateInput.addEventListener('input', () => {
    updateConfirmButton.disabled = updateInput.value !== 'ATUALIZAR LABORATÓRIO';
    document.getElementById('update-input-error').hidden = true;
  });
  updateConfirmButton.addEventListener('click', () => {
    if (updateInput.value !== 'ATUALIZAR LABORATÓRIO') {
      document.getElementById('update-input-error').hidden = false;
      return;
    }
    updateDialog.close('confirm');
    startUpdate();
  });
  document.getElementById('update-cancel-button').addEventListener('click', () => updateDialog.close('cancel'));
  updateDialog.addEventListener('click', (event) => {
    if (event.target === updateDialog) updateDialog.close('cancel');
  });

  async function restoreActiveJob() {
    try {
      const response = await fetch('/api/control/reset/current', { cache: 'no-store' });
      if (!response.ok) return;
      const payload = await response.json();
      if (payload.job && ['queued', 'running'].includes(payload.job.status)) {
        setProgress(payload.job);
        await watchJob(payload.job.id);
      }
    } catch (_) {
      // O estado dos serviços continua disponível mesmo se a consulta de reset falhar.
    }
  }

  renderServices();
  restoreActiveJob();
  refreshUpdateStatus(false);
})();
