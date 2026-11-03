(() => {
  'use strict';

  const blocks = document.querySelectorAll('.code-block, .n8n-code');
  if (!blocks.length) return;

  const status = document.createElement('span');
  status.className = 'code-copy-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  document.body.append(status);

  async function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(value);
        return true;
      } catch {
        // Fall through to the selection-based copy for browsers that deny clipboard access.
      }
    }

    const textarea = document.createElement('textarea');
    textarea.value = value;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.append(textarea);
    textarea.select();
    let copied = false;
    try {
      copied = document.execCommand('copy');
    } finally {
      textarea.remove();
    }
    return copied;
  }

  blocks.forEach((block) => {
    const surface = document.createElement('div');
    surface.className = 'code-surface';
    block.before(surface);
    surface.append(block);

    const button = document.createElement('button');
    button.className = 'code-copy';
    button.type = 'button';
    button.textContent = 'Copiar';
    button.setAttribute('aria-label', 'Copiar exemplo de código');
    button.addEventListener('click', async () => {
      const code = block.querySelector('code')?.innerText ?? block.innerText ?? block.textContent ?? '';
      try {
        if (!await copyText(code.trim())) throw new Error('clipboard unavailable');
        button.textContent = 'Copiado';
        button.dataset.state = 'success';
        status.textContent = 'Exemplo copiado para a área de transferência.';
      } catch {
        button.textContent = 'Não copiou';
        button.dataset.state = 'error';
        status.textContent = 'Não foi possível copiar. Selecione o exemplo e copie manualmente.';
      }
      window.setTimeout(() => {
        button.textContent = 'Copiar';
        delete button.dataset.state;
      }, 1800);
    });
    surface.append(button);
  });
})();
