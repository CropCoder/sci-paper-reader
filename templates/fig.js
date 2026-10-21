/* Sci Paper Reader — figure gallery logic */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const paper = DATA.paper || {};
  const figures = DATA.figures || [];
  const overview = DATA.overview || {};
  const THEME_KEY = 'spr:theme';
  let current = 'overview';

  const esc = (s) => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const figById = (id) => figures.find(f => f.id === id);

  function imgTag(f, cls = '') {
    if (!f.image) return `<div class="empty" style="aspect-ratio:16/10">图像缺失</div>`;
    return `<img ${cls ? `class="${cls}"` : ''} src="${esc(f.image)}" alt="${esc(f.label + ' ' + (f.short || ''))}" loading="lazy" data-fig="${esc(f.id)}">`;
  }

  function renderNav() {
    const nav = $('#figNav');
    const buttons = [`<button class="nav-overview" data-target="overview" role="tab" aria-selected="false">总览</button>`];
    figures.forEach(f => {
      buttons.push(`<button data-target="${esc(f.id)}" role="tab" aria-selected="false">${esc(f.label)}</button>`);
    });
    nav.innerHTML = buttons.join('');
    nav.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-target]');
      if (b) show(b.dataset.target);
    });
  }

  function renderSidebar() {
    const toc = $('#figToc');
    if (!toc) return;
    const items = [{ id: 'overview', label: '总览 · 证据链', num: '00' }].concat(
      figures.map((f, i) => ({ id: f.id, label: f.label + ' · ' + (f.short || ''), num: String(i + 1).padStart(2, '0') }))
    );
    toc.innerHTML = items.map(it =>
      `<a href="#${esc(it.id)}" data-target="${esc(it.id)}"><span class="toc-num">${it.num}</span><span>${esc(it.label)}</span></a>`
    ).join('');
    $$('#figToc a').forEach(a => a.addEventListener('click', (e) => {
      e.preventDefault();
      show(a.dataset.target);
      document.body.classList.remove('side-open');
    }));
  }

  function renderOverview() {
    const pane = $('#overviewPane');
    const flow = overview.flow && overview.flow.length ? overview.flow : figures.map(f => ({
      label: f.label, title: f.short || '', desc: f.one_line || '',
    }));
    const flowHtml = flow.map((s, i) => `
      <div class="logic-step">
        <div class="l-tag">${esc(s.label || ('STEP ' + (i + 1)))}</div>
        <div class="l-title">${esc(s.title || '')}</div>
        <div class="l-desc">${esc(s.desc || '')}</div>
      </div>`).join('');
    const cards = figures.map(f => `
      <article class="fig-card" data-target="${esc(f.id)}" title="查看 ${esc(f.label)} 详解">
        <div class="thumb">${imgTag(f)}</div>
        <div class="fc-body">
          <div class="fc-tag">${esc(f.label)} · p.${esc(f.page || '?')}</div>
          <div class="fc-title">${esc(f.short || f.label)}</div>
          <div class="fc-desc">${esc(f.one_line || '')}</div>
          <div class="fc-foot"><span>${esc((f.tags || []).slice(0, 2).join(' · '))}</span><span>详解 →</span></div>
        </div>
      </article>`).join('');
    const panelCount = figures.reduce((n, f) => n + ((f.panels || []).length), 0);
    const readMin = Math.max(6, Math.round(figures.length * 2.2));
    pane.innerHTML = `
      <section class="hero">
        <div class="hero-kicker">Figure Story · 读图路线</div>
        <h1>${esc(paper.title_zh || paper.title)}</h1>
        <p class="subtitle">${esc(paper.title || '')}</p>
        <div class="hero-meta">
          ${paper.journal ? `<span><b>期刊</b> ${esc(paper.journal)}</span>` : ''}
          ${paper.year ? `<span><b>年份</b> ${esc(paper.year)}</span>` : ''}
          <span><b>主图</b> ${figures.length} 张</span>
          ${paper.doi ? `<span><b>DOI</b> <a href="https://doi.org/${encodeURI(paper.doi)}" target="_blank" rel="noopener">${esc(paper.doi)}</a></span>` : ''}
        </div>
        <div class="hero-stats">
          <span class="stat"><b>${figures.length}</b> 张主图</span>
          <span class="stat"><b>${panelCount}</b> 个面板</span>
          <span class="stat"><b>${flow.length}</b> 步证据链</span>
          <span class="stat"><b>≈ ${readMin}</b> 分钟</span>
        </div>
        <div class="one-liner"><b>一句话总结 · </b>${esc(paper.one_liner || '')}</div>
      </section>
      <p class="overview-lead">${esc(overview.lead || '先看整体逻辑，再逐图拆解每个面板。')}</p>
      <div class="section-head"><span class="s-num">LOGIC</span><h2>图与图的逻辑</h2><span class="s-zh">${flow.length} 步</span></div>
      ${overview.logic_summary ? `<p class="logic-caption">${esc(overview.logic_summary)}</p>` : ''}
      <div class="logic-flow">${flowHtml}</div>
      ${overview.note ? `<div class="overview-note"><b>阅读提示：</b>${esc(overview.note)}</div>` : ''}
      <div class="section-head"><span class="s-num">FIGURES</span><h2>逐图速览</h2><span class="s-zh">点击卡片进入单图详解</span></div>
      <div class="fig-grid">${cards}</div>`;
    $$('.fig-card', pane).forEach(c => c.addEventListener('click', () => show(c.dataset.target)));
    wireImages(pane);
  }

  function renderPanes() {
    const wrap = $('#figPanes');
    wrap.innerHTML = figures.map((f, i) => {
      const panels = (f.panels || []).map(p => `
        <div class="panel-item"><div class="p-tag">${esc(p.label || '')}</div><div>${esc(p.text || '')}</div></div>`).join('');
      const caveats = (f.caveats || []).map(c => `<li>${esc(c)}</li>`).join('');
      const tags = (f.tags || []).map(t => `<span class="chip accent">${esc(t)}</span>`).join('');
      const prev = figures[i - 1], next = figures[i + 1];
      return `<section class="fig-pane" id="pane-${esc(f.id)}" data-fig="${esc(f.id)}" role="tabpanel">
        <div class="section-head fig-section-head">
          <span class="s-num">${esc(f.label.replace(/^Figure\s*/, 'FIG. '))}</span>
          <h2>${esc(f.short || f.label)}</h2>
          <span class="s-zh">p.${esc(f.page || '?')}</span>
        </div>
        <div class="fig-layout">
          <div class="fig-visual">
            <div class="fig-frame">${imgTag(f)}<div class="frame-cap"><span>${esc(f.label)}</span><span>点击放大</span></div></div>
            <div class="fig-zoom-hint">点击图片全屏查看 · ← → 切换 Figure</div>
          </div>
          <div class="fig-detail">
            <div class="legend-box">
              <span class="lg-label">Original legend</span>
              <div class="lg-en">${esc(f.caption_en || '')}</div>
              ${f.legend_zh ? `<div class="lg-zh"><span class="lg-label">图例中译</span>${esc(f.legend_zh)}</div>` : ''}
            </div>
            ${f.one_line ? `<div class="fig-block conclusion"><h4><span class="dot"></span>一句话结论</h4><p>${esc(f.one_line)}</p></div>` : ''}
            ${f.what ? `<div class="fig-block"><h4><span class="dot"></span>图中看到什么</h4><p>${esc(f.what)}</p></div>` : ''}
            ${f.meaning ? `<div class="fig-block"><h4><span class="dot"></span>说明了什么</h4><p>${esc(f.meaning)}</p></div>` : ''}
            ${f.conclusion ? `<div class="fig-block"><h4><span class="dot"></span>结论与意义</h4><p>${esc(f.conclusion)}</p></div>` : ''}
            ${panels ? `<div class="fig-block"><h4><span class="dot"></span>分图 / 面板说明</h4><div class="panel-list">${panels}</div></div>` : ''}
            ${caveats ? `<div class="fig-block"><h4><span class="dot"></span>注意事项</h4><ul class="caveat-list">${caveats}</ul></div>` : ''}
            ${f.connection ? `<div class="fig-block"><h4><span class="dot"></span>与前后图的逻辑</h4><p>${esc(f.connection)}</p></div>` : ''}
            ${tags ? `<div class="chip-row">${tags}</div>` : ''}
            <div class="fig-nav-foot">
              <button class="btn" data-target="${prev ? esc(prev.id) : 'overview'}">← ${prev ? esc(prev.label) : '总览'}</button>
              <button class="btn" data-target="${next ? esc(next.id) : 'overview'}">${next ? esc(next.label) : '总览'} →</button>
            </div>
          </div>
        </div>
      </section>`;
    }).join('');
    $$('.fig-nav-foot button', wrap).forEach(b => b.addEventListener('click', () => show(b.dataset.target)));
    wireImages(wrap);
  }

  function wireImages(root) {
    $$('img[data-fig]', root).forEach(img => {
      img.addEventListener('error', () => {
        const parent = img.parentElement;
        img.remove();
        if (parent) parent.innerHTML = '<div class="empty" style="padding:40px 10px">图像未找到</div>';
      });
      img.addEventListener('click', () => openLightbox(img.dataset.fig));
    });
  }

  function openLightbox(id) {
    const f = figById(id);
    if (!f || !f.image) return;
    $('#lbImg').src = f.image;
    $('#lbImg').alt = f.label + ' ' + (f.short || '');
    $('#lbCap').textContent = `${f.label} · ${f.short || ''}（点击空白或按 Esc 关闭）`;
    $('#lightbox').classList.add('open');
  }

  function show(target) {
    current = target;
    const valid = target === 'overview' || !!figById(target);
    if (!valid) target = 'overview';
    $$('.fig-pane').forEach(p => p.classList.toggle('active', p.id === (target === 'overview' ? 'overviewPane' : 'pane-' + target)));
    $$('#figNav button').forEach(b => b.setAttribute('aria-selected', b.dataset.target === target ? 'true' : 'false'));
    $$('#figToc a').forEach(a => a.classList.toggle('active', a.dataset.target === target));
    if (target === 'overview') $('#overviewPane').classList.add('active');
    if (history.replaceState) history.replaceState(null, '', '#' + target);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function init() {
    document.documentElement.dataset.theme = localStorage.getItem(THEME_KEY) || 'light';
    $('#topTitle').textContent = paper.short_title || paper.title_zh || paper.title || 'Figure 图解';
    $('#genStamp').textContent = paper.generated || '';
    $('#sideMeta').innerHTML = `生成于 ${esc(paper.generated || '')}<br>${esc(paper.source_file || '')}`;
    renderNav();
    renderSidebar();
    renderOverview();
    renderPanes();

    const tocToggle = $('#tocToggle');
    if (tocToggle) tocToggle.addEventListener('click', () => document.body.classList.toggle('side-open'));
    $('#themeBtn').addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      localStorage.setItem(THEME_KEY, next);
    });
    $('#printBtn').addEventListener('click', () => window.print());
    $('#lbClose').addEventListener('click', () => $('#lightbox').classList.remove('open'));
    $('#lightbox').addEventListener('click', (e) => { if (e.target === $('#lightbox') || e.target === $('#lbImg')) $('#lightbox').classList.remove('open'); });

    document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      if (e.key === 'Escape') { $('#lightbox').classList.remove('open'); return; }
      if ($('#lightbox').classList.contains('open')) return;
      if (current === 'overview') return;
      const idx = figures.findIndex(f => f.id === current);
      if (e.key === 'ArrowRight' && idx >= 0 && figures[idx + 1]) show(figures[idx + 1].id);
      if (e.key === 'ArrowLeft' && idx > 0) show(figures[idx - 1].id);
    });

    const hash = (location.hash || '').replace('#', '');
    show(hash && (hash === 'overview' || figById(hash)) ? hash : 'overview');
  }

  window.__sprShow = show;
  window.addEventListener('hashchange', () => {
    const h = (location.hash || '').replace('#', '');
    if (h && (h === 'overview' || figById(h))) show(h);
  });
  init();
})();
