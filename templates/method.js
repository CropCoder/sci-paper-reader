/* Sci Paper Reader — methods page logic */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const paper = DATA.paper || {};
  const methods = DATA.methods || [];
  const route = DATA.route || [];
  const THEME_KEY = 'spr:theme';
  let activeCat = '全部';

  const esc = (s) => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const figLink = (label) => {
    const m = String(label).match(/(?:fig(?:ure)?|图)\s*\.?\s*(\d+)/i);
    if (!m) return null;
    return `job.fig.html#fig${m[1]}`;
  };

  function render() {
    const cats = ['全部', ...new Set(methods.map(m => m.category).filter(Boolean))];
    const routeHtml = route.length ? route.map((r, i) => `
      <div class="route-step">
        <div class="r-num">${esc(r.step || String(i + 1).padStart(2, '0'))}</div>
        <div class="r-body"><div class="r-name">${esc(r.name || '')}</div><div class="r-desc">${esc(r.desc || '')}</div></div>
      </div>`).join('') : '';

    const cards = methods.map((m, i) => {
      const cat = m.category || '其他';
      const used = (m.used_in || []).map(u => {
        const href = figLink(u);
        return href ? `<a class="chip accent" href="${esc(href)}">${esc(u)}</a>` : `<span class="chip">${esc(u)}</span>`;
      }).join('');
      const cite = m.citation || {};
      const url = cite.url || (cite.doi ? 'https://doi.org/' + encodeURI(cite.doi) : '');
      const citeHtml = (cite.text || cite.doi || cite.url) ? `
        <div class="cite-box">
          <span class="cite-label">原始文献</span>
          <span>${esc(cite.text || cite.doi || '见原文参考文献')}</span>
          ${cite.doi ? `<span class="chip">DOI ${esc(cite.doi)}</span>` : ''}
          ${url ? `<a class="cite-link" href="${esc(url)}" target="_blank" rel="noopener">打开原文 ↗</a>` : ''}
        </div>` : '';
      return `<article class="method-card" id="m-${esc(m.id || i)}" data-cat="${esc(cat)}">
        <div class="m-top">
          <span class="m-index">${String(i + 1).padStart(2, '0')}</span>
          <div style="min-width:0">
            <h3>${esc(m.name || '未命名方法')}</h3>
            ${m.name_en ? `<div class="m-en">${esc(m.name_en)}</div>` : ''}
          </div>
          <span class="chip accent m-cat">${esc(cat)}</span>
        </div>
        <div class="method-grid">
          ${m.what ? `<div class="m-field"><h4>原理 / 是什么</h4><p>${esc(m.what)}</p></div>` : ''}
          ${m.how ? `<div class="m-field"><h4>本文怎么用</h4><p>${esc(m.how)}</p></div>` : ''}
          ${m.params ? `<div class="m-field full"><h4>关键参数 / 实验设置</h4><p>${esc(m.params)}</p></div>` : ''}
          ${m.interpretation ? `<div class="m-field full"><h4>解读 / 为什么重要</h4><p>${esc(m.interpretation)}</p></div>` : ''}
        </div>
        ${citeHtml}
        ${used ? `<div class="used-in"><span>用于：</span>${used}</div>` : ''}
      </article>`;
    }).join('');

    $('#methodContent').innerHTML = `
      <section class="hero method-hero">
        <div class="hero-kicker">Materials & Methods · 方法拆解</div>
        <h1>${esc(paper.title_zh || paper.title)}</h1>
        <p class="subtitle">${esc(paper.one_liner || '按论文实际使用顺序，拆解每项技术“是什么、怎么用、为什么这样做”。')}</p>
        <div class="hero-meta">
          ${paper.journal ? `<span><b>期刊</b> ${esc(paper.journal)}</span>` : ''}
          ${paper.year ? `<span><b>年份</b> ${esc(paper.year)}</span>` : ''}
          <span><b>方法</b> ${methods.length} 项</span>
          ${paper.doi ? `<span><b>DOI</b> <a href="https://doi.org/${encodeURI(paper.doi)}" target="_blank" rel="noopener">${esc(paper.doi)}</a></span>` : ''}
        </div>
      </section>
      ${DATA.overview ? `<div class="callout"><span class="c-icon">◎</span><div>${esc(DATA.overview)}</div></div>` : ''}
      ${routeHtml ? `<div class="section-head"><span class="s-num">ROUTE</span><h2>技术路线</h2></div><div class="method-route">${routeHtml}</div>` : ''}
      <div class="section-head"><span class="s-num">METHODS</span><h2>逐项方法</h2></div>
      <div class="method-toolbar">
        <span class="filter-label">分类</span>
        ${cats.map(c => `<button class="method-filter" data-cat="${esc(c)}" aria-pressed="${c === '全部' ? 'true' : 'false'}">${esc(c)}</button>`).join('')}
      </div>
      <div id="methodList">${cards || '<div class="empty">没有整理到方法条目。</div>'}</div>
      ${(DATA.notes || []).length ? `<div class="callout warn" style="margin-top:26px"><span class="c-icon">!</span><div><b>使用注意：</b>${esc(DATA.notes.join('；'))}</div></div>` : ''}
      <div class="footer"><div>方法描述以原文 Materials & Methods 为准；解读为辅助理解。</div><div id="genStamp">${esc(paper.generated || '')}</div></div>`;

    // TOC
    $('#toc').innerHTML = methods.map((m, i) =>
      `<a href="#m-${esc(m.id || i)}" data-id="m-${esc(m.id || i)}"><span class="toc-num">${String(i + 1).padStart(2, '0')}</span><span>${esc(m.name || '方法')}</span></a>`
    ).join('') || '<div class="empty">无方法</div>';
    $$('#toc a').forEach(a => a.addEventListener('click', (e) => {
      e.preventDefault();
      const el = document.getElementById(a.dataset.id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      document.body.classList.remove('side-open');
    }));

    $$('.method-filter').forEach(b => b.addEventListener('click', () => {
      activeCat = b.dataset.cat;
      $$('.method-filter').forEach(x => x.setAttribute('aria-pressed', x.dataset.cat === activeCat ? 'true' : 'false'));
      $$('.method-card').forEach(c => c.classList.toggle('is-hidden', activeCat !== '全部' && c.dataset.cat !== activeCat));
      spy();
    }));

    $('#routeHint').textContent = route.length
      ? route.map(r => r.name).filter(Boolean).join(' → ')
      : '按正文顺序排列';
    $('#sideMeta').innerHTML = `生成于 ${esc(paper.generated || '')}<br>${esc(paper.source_file || '')}`;
    $('#topTitle').textContent = paper.short_title || paper.title_zh || paper.title || '方法拆解';
  }

  function spy() {
    const links = $$('#toc a');
    let active = null;
    const y = window.scrollY + 140;
    links.forEach(a => {
      const el = document.getElementById(a.dataset.id);
      if (el && el.getBoundingClientRect().top + window.scrollY <= y) active = a;
    });
    links.forEach(a => a.classList.toggle('active', a === active));
  }

  function progress() {
    const h = document.documentElement.scrollHeight - window.innerHeight;
    $('#progress').style.width = (h > 0 ? Math.min(100, Math.max(0, window.scrollY / h * 100)) : 0) + '%';
  }

  function init() {
    document.documentElement.dataset.theme = localStorage.getItem(THEME_KEY) || 'light';
    render();
    $('#themeBtn').addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      localStorage.setItem(THEME_KEY, next);
    });
    $('#printBtn').addEventListener('click', () => window.print());
    $('#tocToggle').addEventListener('click', () => document.body.classList.toggle('side-open'));
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) { requestAnimationFrame(() => { spy(); progress(); ticking = false; }); ticking = true; }
    }, { passive: true });
    spy(); progress();
  }

  init();
})();
