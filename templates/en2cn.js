/* Sci Paper Reader — en2cn page logic */
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const paper = DATA.paper || {};
  const paperId = paper.id || 'paper';
  const STORE = 'spr:en2cn:' + paperId;
  const MODE_KEY = STORE + ':mode';
  const THEME_KEY = 'spr:theme';

  const marked = new Set(JSON.parse(localStorage.getItem(STORE + ':marks') || '[]'));
  let mode = localStorage.getItem(MODE_KEY) || 'compare';
  let query = '';
  let bookmarkOnly = false;

  const esc = (s) => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const saveMarks = () => localStorage.setItem(STORE + ':marks', JSON.stringify([...marked]));

  function iconStar(filled) {
    return `<svg class="icon" viewBox="0 0 24 24" fill="${filled ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="1.6"><path d="M12 3.5l2.6 5.5 6 .8-4.4 4.2 1.1 6-5.3-2.9-5.3 2.9 1.1-6L3.4 9.8l6-.8L12 3.5Z"/></svg>`;
  }

  function render() {
    const toc = $('#toc');
    const content = $('#content');
    let html = '';
    let tocHtml = '';
    let n = 0;
    DATA.sections.forEach((sec, si) => {
      const secId = 'sec-' + sec.id;
      tocHtml += `<a href="#${secId}" data-sec="${sec.id}"><span class="toc-num">${String(si + 1).padStart(2, '0')}</span><span>${esc(sec.title_zh || sec.title)}</span></a>`;
      html += `<section class="sec" id="${secId}" data-sec="${sec.id}">`;
      html += `<div class="section-head"><span class="s-num">${String(si + 1).padStart(2, '0')}</span><h2>${esc(sec.title_zh || sec.title)}</h2><span class="s-zh">${esc(sec.title)}</span></div>`;
      sec.paras.forEach((p) => {
        n += 1;
        const zh = p.zh && p.zh.trim() ? p.zh : '（本段待翻译）';
        html += `<article class="para${marked.has(p.id) ? ' is-marked' : ''}" id="p-${esc(p.id)}" data-pid="${esc(p.id)}" data-text="${esc((p.en + ' ' + zh).toLowerCase())}">
          <button class="bookmark-btn" data-bm="${esc(p.id)}" aria-label="书签" title="书签 (B)">${iconStar(marked.has(p.id))}</button>
          <div class="p-en"><div class="p-label"><span class="p-num">¶ ${String(n).padStart(2, '0')}</span><span>Original · p.${p.page || '?'}</span></div><div class="p-text">${esc(p.en)}</div></div>
          <div class="p-zh"><div class="p-label"><span>中文</span></div><div class="p-text">${esc(zh)}</div></div>
        </article>`;
      });
      html += '</section>';
    });
    content.innerHTML = html || '<div class="empty">没有抽取到正文段落。</div>';
    toc.innerHTML = tocHtml || '<div class="empty">无目录</div>';
    $('#paraCount').textContent = `${n} 段 · 英文 ${DATA.stats.words_en.toLocaleString()} 词 · 中文 ${DATA.stats.chars_zh.toLocaleString()} 字`;
    wire();
  }

  function wire() {
    $$('#toc a').forEach(a => a.addEventListener('click', (e) => {
      e.preventDefault();
      const el = document.getElementById(a.getAttribute('href').slice(1));
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      document.body.classList.remove('side-open');
    }));
    $$('.bookmark-btn').forEach(btn => btn.addEventListener('click', () => toggleMark(btn.dataset.bm)));
    $$('#bookmarkList .bookmark-item').forEach(el => el.addEventListener('click', (e) => {
      if (e.target.closest('.b-x')) { removeMark(el.dataset.bm); return; }
      jumpTo(el.dataset.bm);
    }));
  }

  function toggleMark(pid) {
    if (marked.has(pid)) marked.delete(pid); else marked.add(pid);
    saveMarks();
    const el = document.getElementById('p-' + pid);
    if (el) {
      el.classList.toggle('is-marked', marked.has(pid));
      const btn = el.querySelector('.bookmark-btn');
      if (btn) btn.innerHTML = iconStar(marked.has(pid));
    }
    renderBookmarks();
    toast(marked.has(pid) ? '已加入书签' : '已移除书签');
  }

  function removeMark(pid) {
    if (!marked.has(pid)) return;
    marked.delete(pid); saveMarks(); renderBookmarks();
    const el = document.getElementById('p-' + pid);
    if (el) { el.classList.remove('is-marked'); const b = el.querySelector('.bookmark-btn'); if (b) b.innerHTML = iconStar(false); }
  }

  function jumpTo(pid) {
    const el = document.getElementById('p-' + pid);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.style.transition = 'background .3s ease';
    el.style.background = 'var(--accent-soft)';
    setTimeout(() => { el.style.background = ''; }, 1200);
  }

  function renderBookmarks() {
    const list = $('#bookmarkList');
    const arr = [...marked];
    $('#bkCount').textContent = arr.length;
    $('#bkCount2').textContent = arr.length;
    if (!arr.length) {
      list.innerHTML = `<div class="side-hint">点击段落右上角的书签图标，或按 <span class="kbd">B</span> 标记当前段落。</div>`;
      return;
    }
    list.innerHTML = arr.map(pid => {
      const el = document.getElementById('p-' + pid);
      const p = el ? DATA.flat.find(x => x.id === pid) : null;
      const excerpt = p ? (p.zh || p.en).slice(0, 90) : pid;
      return `<div class="bookmark-item" data-bm="${esc(pid)}" title="跳转">
        <span class="b-text">${esc(excerpt)}</span>
        <span class="b-x" title="移除">×</span>
      </div>`;
    }).join('');
    $$('#bookmarkList .bookmark-item').forEach(item => item.addEventListener('click', (e) => {
      if (e.target.closest('.b-x')) { removeMark(item.dataset.bm); return; }
      jumpTo(item.dataset.bm);
    }));
  }

  function applyFilter() {
    let visible = 0;
    const q = query.trim().toLowerCase();
    $$('.para').forEach(el => {
      const hitQ = !q || (el.dataset.text || '').includes(q);
      const hitB = !bookmarkOnly || el.classList.contains('is-marked');
      const show = hitQ && hitB;
      el.classList.toggle('is-hidden', !show);
      if (show) visible += 1;
    });
    $$('.sec').forEach(sec => {
      const any = $$('.para', sec).some(p =>
        !p.classList.contains('is-hidden') && (!bookmarkOnly || p.classList.contains('is-marked'))
      );
      sec.style.display = any ? '' : 'none';
    });
    $('#paraCount').textContent = q || bookmarkOnly
      ? `显示 ${visible} 段 / 共 ${DATA.stats.paras} 段`
      : `${DATA.stats.paras} 段 · 英文 ${DATA.stats.words_en.toLocaleString()} 词 · 中文 ${DATA.stats.chars_zh.toLocaleString()} 字`;
  }

  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('show'), 1600);
  }

  function setMode(next) {
    mode = next;
    document.body.classList.remove('mode-compare', 'mode-zh', 'mode-en');
    document.body.classList.add('mode-' + next);
    $$('#modeSeg button').forEach(b => b.setAttribute('aria-pressed', b.dataset.mode === next ? 'true' : 'false'));
    localStorage.setItem(MODE_KEY, next);
  }

  function currentPara() {
    const list = $$('.para').filter(p => !p.classList.contains('is-hidden'));
    if (!list.length) return null;
    const y = window.scrollY + window.innerHeight * 0.4;
    let best = list[0], bestD = Infinity;
    list.forEach(p => {
      const r = p.getBoundingClientRect();
      const top = r.top + window.scrollY;
      const d = Math.abs(top - y);
      if (d < bestD) { bestD = d; best = p; }
    });
    return best;
  }

  function scrollProgress() {
    const h = document.documentElement.scrollHeight - window.innerHeight;
    const pct = h > 0 ? Math.min(100, Math.max(0, window.scrollY / h * 100)) : 0;
    $('#progress').style.width = pct + '%';
  }

  function spy() {
    const heads = $$('.section-head');
    let active = heads[0];
    const y = window.scrollY + 120;
    heads.forEach(h => { if (h.getBoundingClientRect().top + window.scrollY <= y) active = h; });
    const sec = active ? active.closest('.sec') : null;
    const id = sec ? sec.dataset.sec : null;
    $$('#toc a').forEach(a => a.classList.toggle('active', a.dataset.sec === id));
  }

  function initHero() {
    $('#paperTitle').innerHTML = esc(paper.title_zh || paper.title);
    $('#paperSubtitle').textContent = paper.title_zh ? paper.title : (paper.title_zh || '');
    $('#paperTitle').title = paper.title || '';
    $('#oneLiner').innerHTML = paper.one_liner
      ? `<b>一句话总结 · </b>${esc(paper.one_liner)}`
      : '';
    const meta = [];
    if (paper.journal) meta.push(`<span><b>期刊</b> ${esc(paper.journal)}</span>`);
    if (paper.year) meta.push(`<span><b>年份</b> ${esc(paper.year)}</span>`);
    if (paper.authors) meta.push(`<span><b>作者</b> ${esc(paper.authors)}</span>`);
    if (paper.doi) meta.push(`<span><b>DOI</b> <a href="https://doi.org/${encodeURI(paper.doi)}" target="_blank" rel="noopener">${esc(paper.doi)}</a></span>`);
    $('#heroMeta').innerHTML = meta.join('');
    $('#heroStats').innerHTML = [
      `<span class="stat"><b>${DATA.stats.sections}</b> 节</span>`,
      `<span class="stat"><b>${DATA.stats.paras}</b> 段对照</span>`,
      `<span class="stat"><b>${DATA.stats.words_en.toLocaleString()}</b> 英文词</span>`,
      `<span class="stat"><b>${DATA.stats.chars_zh.toLocaleString()}</b> 中文字</span>`,
      `<span class="stat"><b>≈ ${DATA.stats.minutes}</b> 分钟</span>`,
    ].join('');
    $('#sideMeta').innerHTML = `生成于 ${esc(paper.generated || '')}<br>${esc(paper.source_file || '')}`;
    $('#genStamp').textContent = paper.generated || '';
    $('#topTitle').textContent = paper.short_title || paper.title_zh || paper.title || '论文精读';
  }

  function init() {
    document.documentElement.dataset.theme = localStorage.getItem(THEME_KEY) || 'light';
    DATA.flat = DATA.sections.flatMap(s => s.paras);
    initHero();
    render();
    setMode(mode);
    renderBookmarks();

    $('#searchInput').addEventListener('input', (e) => { query = e.target.value; applyFilter(); });
    $('#modeSeg').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-mode]');
      if (b) setMode(b.dataset.mode);
    });
    $('#bookmarkFilterBtn').addEventListener('click', () => {
      bookmarkOnly = !bookmarkOnly;
      $('#bookmarkFilterBtn').setAttribute('aria-pressed', bookmarkOnly ? 'true' : 'false');
      document.body.classList.toggle('filter-bookmarks', bookmarkOnly);
      applyFilter();
      toast(bookmarkOnly ? '只看书签' : '显示全部段落');
    });
    $('#themeBtn').addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      localStorage.setItem(THEME_KEY, next);
    });
    $('#printBtn').addEventListener('click', () => window.print());
    $('#tocToggle').addEventListener('click', () => document.body.classList.toggle('side-open'));

    document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'j' || e.key === 'J') { e.preventDefault(); const p = currentPara(); const all = $$('.para').filter(x => !x.classList.contains('is-hidden')); const i = all.indexOf(p); if (all[i + 1]) all[i + 1].scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      else if (e.key === 'k' || e.key === 'K') { e.preventDefault(); const p = currentPara(); const all = $$('.para').filter(x => !x.classList.contains('is-hidden')); const i = all.indexOf(p); if (all[i - 1]) all[i - 1].scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      else if (e.key === 'b' || e.key === 'B') { e.preventDefault(); const p = currentPara(); if (p) toggleMark(p.dataset.pid); }
      else if (e.key === '/') { e.preventDefault(); $('#searchInput').focus(); }
      else if (e.key === 'Escape') {
        if (document.body.classList.contains('side-open')) document.body.classList.remove('side-open');
        else if (query) { query = ''; $('#searchInput').value = ''; applyFilter(); }
      }
    });

    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => { scrollProgress(); spy(); ticking = false; });
        ticking = true;
      }
    }, { passive: true });
    scrollProgress(); spy();
  }

  init();
})();
