/* Sci Paper Reader — shared top navigation: page tabs + in-page module jump */
(() => {
  const root = document.getElementById('siteNav');
  if (!root) return;
  const page = document.body.dataset.page || 'en2cn';
  const esc = (s) => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const pages = [
    { id: 'en2cn', href: 'job.en2cn.html', label: '逐段精读' },
    { id: 'fig', href: 'job.fig.html', label: '图解' },
    { id: 'method', href: 'job.method.html', label: '方法' },
  ];

  let items = [];
  let heading = '本页模块';
  if (page === 'en2cn') {
    heading = '章节跳转';
    items = (DATA.sections || []).map((s, i) => ({
      label: (i + 1) + '. ' + (s.title_zh || s.title),
      target: 'sec-' + s.id,
    }));
  } else if (page === 'fig') {
    heading = 'Figure 跳转';
    items = [{ label: '总览：图与图的逻辑', target: 'overview' }].concat(
      (DATA.figures || []).map((f) => ({ label: f.label + ' · ' + (f.short || ''), target: f.id }))
    );
  } else if (page === 'method') {
    heading = '方法跳转';
    items = (DATA.methods || []).map((m, i) => ({
      label: (i + 1) + '. ' + (m.name || '方法'),
      target: 'm-' + (m.id || i),
    }));
  }

  const tabs = pages.map((p) => {
    const active = p.id === page;
    return `<a class="page-tab${active ? ' active' : ''}" href="${p.href}"${active ? ' aria-current="page"' : ''}>${esc(p.label)}</a>`;
  }).join('');

  root.innerHTML = `
    <div class="page-tabs" role="tablist" aria-label="页面切换">${tabs}</div>
    <div class="module-picker">
      <button class="module-btn" id="moduleBtn" aria-expanded="false" aria-controls="moduleMenu">
        <span>${esc(heading)}</span><span class="caret">▼</span>
      </button>
      <div class="module-menu" id="moduleMenu" role="menu">
        <div class="mm-label">${esc(heading)}</div>
        ${items.length ? items.map((it, i) => `
          <a class="module-item" href="#${esc(it.target)}" data-target="${esc(it.target)}" role="menuitem">
            <span class="mi-num">${String(i + 1).padStart(2, '0')}</span><span>${esc(it.label)}</span>
          </a>`).join('') : '<div class="module-empty">本页没有可跳转模块</div>'}
      </div>
    </div>`;

  const btn = document.getElementById('moduleBtn');
  const menu = document.getElementById('moduleMenu');
  const close = () => { menu.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); };
  const open = () => {
    menu.classList.add('open'); btn.setAttribute('aria-expanded', 'true');
    const first = menu.querySelector('.module-item');
    if (first) first.focus({ preventScroll: true });
  };
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (menu.classList.contains('open')) close(); else open();
  });
  document.addEventListener('click', (e) => { if (!e.target.closest('.module-picker')) close(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

  menu.addEventListener('click', (e) => {
    const a = e.target.closest('.module-item');
    if (!a) return;
    e.preventDefault();
    const target = a.dataset.target;
    close();
    if (page === 'fig') {
      if (window.__sprShow) window.__sprShow(target);
      else location.hash = target;
      return;
    }
    if (page === 'method') {
      const all = document.querySelector('.method-filter[data-cat="全部"]');
      if (all) all.click();
    }
    const el = document.getElementById(target);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    else location.hash = target;
  });
})();
