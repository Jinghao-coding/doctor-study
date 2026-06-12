// Theme: respect saved preference, then system preference.
(function(){
  var savedTheme = localStorage.getItem('doctor-study-theme');
  if(savedTheme === 'light' || savedTheme === 'dark'){
    document.documentElement.setAttribute('data-theme', savedTheme);
  }
})();

// 全局轻量 toast，用于隐私模式 / 存储失败 / 导入导出反馈。
var __dsToastTimer = null;
function showStorageToast(msg){
  try {
    var toast = document.querySelector('.storage-toast');
    if(!toast){
      toast = document.createElement('div');
      toast.className = 'storage-toast';
      toast.setAttribute('role', 'status');
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    if(__dsToastTimer) clearTimeout(__dsToastTimer);
    __dsToastTimer = setTimeout(function(){ toast.classList.remove('show'); }, 3200);
  } catch(_) { /* DOM 还没准备好就放弃 */ }
}

// QA blocks already have inline onclick="this.classList.toggle('open')".
// Alt+E: expand / collapse all Q&A on current page.
document.addEventListener('keydown', function(e){
  if(e.key === 'e' && e.altKey){
    var qas = document.querySelectorAll('.qa');
    if(!qas.length) return;
    var allOpen = Array.from(qas).every(function(q){ return q.classList.contains('open'); });
    qas.forEach(function(q){
      allOpen ? q.classList.remove('open') : q.classList.add('open');
    });
  }
});

document.addEventListener('DOMContentLoaded', function(){
  var nav = document.querySelector('.topnav') || document.querySelector('.idx-home-nav');
  if(!nav) return;

  var toggle = document.createElement('button');
  toggle.className = 'theme-toggle';
  toggle.type = 'button';

  function currentTheme(){
    var explicit = document.documentElement.getAttribute('data-theme');
    if(explicit) return explicit;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function render(){
    var theme = currentTheme();
    toggle.textContent = theme === 'dark' ? '日间' : '夜间';
    toggle.setAttribute('aria-label', theme === 'dark' ? '切换到日间模式' : '切换到夜间模式');
  }

  toggle.addEventListener('click', function(){
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('doctor-study-theme', next); } catch(_) { /* 隐私模式静默 */ }
    render();
  });

  nav.appendChild(toggle);
  render();
});

// App shell: mobile sidebar, dropdown hygiene, and quick focus search.
document.addEventListener('DOMContentLoaded', function(){
  var sideToggle = document.querySelector('.side-toggle');
  var sideCollapse = document.querySelector('.side-collapse');
  var navMenus = Array.from(document.querySelectorAll('.nav-menu'));

  function setSideCollapsed(collapsed){
    document.body.classList.toggle('side-collapsed', collapsed);
    [sideToggle, sideCollapse].forEach(function(button){
      if(button) button.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
    });
    if(sideToggle) sideToggle.textContent = collapsed ? '展开主题' : '折叠主题';
  }

  [sideToggle, sideCollapse].forEach(function(button){
    if(!button) return;
    button.addEventListener('click', function(){
      setSideCollapsed(!document.body.classList.contains('side-collapsed'));
    });
  });

  document.addEventListener('click', function(e){
    navMenus.forEach(function(menu){
      if(!menu.contains(e.target)) menu.removeAttribute('open');
    });
  });

  document.querySelectorAll('[data-focus-tabs]').forEach(function(button){
    button.addEventListener('click', function(){
      var group = document.querySelector('[data-tabs]');
      if(group) group.classList.remove('module-collapsed');
      var input = document.querySelector('.tabs-filter');
      if(!input) return;
      setTimeout(function(){ input.focus(); }, 120);
    });
  });

  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape'){
      navMenus.forEach(function(menu){ menu.removeAttribute('open'); });
    }
  });
  setSideCollapsed(document.body.classList.contains('side-collapsed'));
});

document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('[data-tabs]').forEach(function(group){
    var buttons = Array.from(group.querySelectorAll('.tab-button'));
    var panels = Array.from(group.querySelectorAll('.tab-panel'));
    var filter = group.querySelector('.tabs-filter');
    var moduleToggle = group.querySelector('.module-toggle');
    var moduleCollapse = group.querySelector('.module-collapse');
    var moduleResizer = group.querySelector('.module-resizer');
    var currentTitle = group.querySelector('.module-current strong');
    if(!buttons.length || !panels.length) return;
    var widthKey = 'doctor-study-module-width';

    function clampWidth(value){
      var max = Math.min(420, Math.max(240, window.innerWidth * 0.42));
      return Math.max(180, Math.min(max, value));
    }

    function setModuleWidth(width){
      var clamped = clampWidth(width);
      group.style.setProperty('--module-nav-width', clamped + 'px');
      try { localStorage.setItem(widthKey, String(Math.round(clamped))); } catch(_) { /* 隐私模式静默 */ }
    }

    function setModuleCollapsed(collapsed){
      group.classList.toggle('module-collapsed', collapsed);
      [moduleToggle, moduleCollapse].forEach(function(button){
        if(button) button.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
      });
      if(moduleToggle) moduleToggle.textContent = collapsed ? '展开模块' : '折叠模块';
    }

    function updateCurrentTitle(){
      if(!currentTitle) return;
      var active = group.querySelector('.tab-button.active .tab-title');
      currentTitle.textContent = active ? active.textContent.trim() : '';
    }

    function activate(index){
      buttons.forEach(function(button, i){
        var active = i === index;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      panels.forEach(function(panel, i){
        var active = i === index;
        panel.classList.toggle('active', active);
        panel.hidden = !active;
      });
      updateCurrentTitle();
      document.dispatchEvent(new CustomEvent('tab:activated', {detail: {group: group}}));
    }

    function visibleButtons(){
      return buttons.filter(function(button){ return !button.hidden; });
    }

    buttons.forEach(function(button, index){
      button.addEventListener('click', function(){
        activate(index);
      });
      button.addEventListener('keydown', function(e){
        if(e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        var visible = visibleButtons();
        var current = visible.indexOf(button);
        if(current < 0 || !visible.length) return;
        var nextVisible = e.key === 'ArrowRight' ? current + 1 : current - 1;
        if(nextVisible < 0) nextVisible = visible.length - 1;
        if(nextVisible >= visible.length) nextVisible = 0;
        var nextButton = visible[nextVisible];
        var next = buttons.indexOf(nextButton);
        nextButton.focus();
        activate(next);
      });
    });

    if(filter){
      filter.addEventListener('input', function(){
        var query = filter.value.trim().toLowerCase();
        buttons.forEach(function(button){
          var text = button.textContent.replace(/\s+/g, ' ').toLowerCase();
          var match = !query || text.indexOf(query) !== -1;
          button.dataset.queryHidden = match ? '' : '1';
          button.hidden = !!button.dataset.queryHidden || !!button.dataset.levelHidden;
        });
        var active = group.querySelector('.tab-button.active');
        if(active && active.hidden){
          var firstVisible = visibleButtons()[0];
          if(firstVisible) activate(buttons.indexOf(firstVisible));
        }
      });
    }

    if(moduleToggle) moduleToggle.addEventListener('click', function(){
      setModuleCollapsed(!group.classList.contains('module-collapsed'));
    });
    if(moduleCollapse) moduleCollapse.addEventListener('click', function(){
      setModuleCollapsed(!group.classList.contains('module-collapsed'));
    });
    if(moduleResizer){
      var savedWidth = parseInt(localStorage.getItem(widthKey), 10);
      if(!Number.isNaN(savedWidth)) setModuleWidth(savedWidth);

      moduleResizer.addEventListener('pointerdown', function(e){
        if(group.classList.contains('module-collapsed')) return;
        e.preventDefault();
        moduleResizer.setPointerCapture(e.pointerId);
        group.classList.add('module-resizing');
        document.body.classList.add('resizing-module');
      });
      moduleResizer.addEventListener('pointermove', function(e){
        if(!group.classList.contains('module-resizing')) return;
        var rect = group.getBoundingClientRect();
        setModuleWidth(e.clientX - rect.left);
      });
      function stopResize(e){
        if(!group.classList.contains('module-resizing')) return;
        group.classList.remove('module-resizing');
        document.body.classList.remove('resizing-module');
        if(e && moduleResizer.hasPointerCapture && moduleResizer.hasPointerCapture(e.pointerId)){
          moduleResizer.releasePointerCapture(e.pointerId);
        }
      }
      moduleResizer.addEventListener('pointerup', stopResize);
      moduleResizer.addEventListener('pointercancel', stopResize);
    }

    // ===== 进度 / 级别筛选 / 分组折叠 / 上下篇 =====
    var pageKey = (location.pathname || 'index') + '#' + (group.dataset.tabsId || 'tabs');
    var progressKey = 'doctor-study-progress::' + pageKey;
    var groupKey = 'doctor-study-group::' + pageKey;
    var levelKey = 'doctor-study-level::' + pageKey;
    var progressBar = group.querySelector('.module-progress-fill');
    var progressText = group.querySelector('.module-progress-text');
    var levelChips = Array.from(group.querySelectorAll('.level-chip'));
    var detailGroups = Array.from(group.querySelectorAll('details.tab-group'));

    function loadProgress(){
      try { return JSON.parse(localStorage.getItem(progressKey) || '{}') || {}; }
      catch(_) { return {}; }
    }
    function saveProgress(state){
      try {
        localStorage.setItem(progressKey, JSON.stringify(state));
      } catch(err) {
        showStorageToast('当前浏览器禁用了本地存储，进度无法保存。');
      }
    }
    function formatRelativeTime(ts){
      if(!ts) return '';
      var diff = Date.now() - ts;
      if(diff < 0) diff = 0;
      var min = 60 * 1000;
      var hour = 60 * min;
      var day = 24 * hour;
      if(diff < min) return '刚刚';
      if(diff < hour) return Math.floor(diff / min) + ' 分钟前';
      if(diff < day) return Math.floor(diff / hour) + ' 小时前';
      var d = new Date(ts);
      var days = Math.floor(diff / day);
      if(days < 30) return days + ' 天前';
      return (d.getMonth() + 1) + '月' + d.getDate() + '日';
    }
    function syncProgress(){
      var state = loadProgress();
      var done = 0;
      buttons.forEach(function(btn){
        var mid = btn.dataset.mid;
        var isDone = !!(mid && state[mid]);
        btn.classList.toggle('is-done', isDone);
        if(isDone) done++;
      });
      panels.forEach(function(panel){
        var mid = panel.dataset.mid;
        var doneBtn = panel.querySelector('.tab-done');
        if(doneBtn){
          var isDone = !!(mid && state[mid]);
          doneBtn.setAttribute('aria-pressed', isDone ? 'true' : 'false');
          var label = doneBtn.querySelector('.tab-done-label');
          if(label) label.textContent = isDone ? '已浏览' : '标记为已浏览';
        }
        var lastSeen = panel.querySelector('.tab-last-seen');
        if(lastSeen){
          var ts = mid ? state[mid] : 0;
          if(ts){
            lastSeen.hidden = false;
            var staleDays = (Date.now() - ts) / (24 * 3600 * 1000);
            lastSeen.classList.toggle('is-stale', staleDays >= 7);
            var valueEl = lastSeen.querySelector('.tab-last-seen-value');
            if(valueEl) valueEl.textContent = formatRelativeTime(ts) + (staleDays >= 7 ? ' · 建议复习' : '');
          } else {
            lastSeen.hidden = true;
            lastSeen.classList.remove('is-stale');
          }
        }
      });
      var total = buttons.length;
      if(progressBar) progressBar.style.width = total ? (done * 100 / total) + '%' : '0%';
      if(progressText) progressText.textContent = done + ' / ' + total;
    }
    function toggleDone(mid){
      if(!mid) return;
      var state = loadProgress();
      if(state[mid]) delete state[mid]; else state[mid] = Date.now();
      saveProgress(state);
      syncProgress();
    }
    panels.forEach(function(panel){
      var doneBtn = panel.querySelector('.tab-done');
      if(doneBtn){
        doneBtn.addEventListener('click', function(){ toggleDone(panel.dataset.mid); });
      }
      panel.querySelectorAll('.tab-step').forEach(function(stepBtn){
        stepBtn.addEventListener('click', function(){
          var target = parseInt(stepBtn.dataset.stepTarget, 10);
          if(Number.isNaN(target)) return;
          activate(target - 1);
          var active = group.querySelector('.tab-button.active');
          if(active && typeof active.scrollIntoView === 'function'){
            active.scrollIntoView({block: 'nearest'});
          }
          var panelEl = group.querySelector('.tab-panel.active');
          if(panelEl) panelEl.scrollIntoView({behavior: 'smooth', block: 'start'});
        });
      });
    });

    // ===== 工具栏动作：导出 / 导入 / 重置 =====
    var actionBtns = Array.from(group.querySelectorAll('.module-action'));
    var importInput = group.querySelector('.module-import-input');
    function downloadJSON(filename, obj){
      try {
        var blob = new Blob([JSON.stringify(obj, null, 2)], {type: 'application/json'});
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click();
        document.body.removeChild(a);
        setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
      } catch(err) {
        showStorageToast('导出失败：' + (err && err.message ? err.message : err));
      }
    }
    function exportProgress(){
      var payload = {
        version: 1,
        exportedAt: new Date().toISOString(),
        page: location.pathname,
        progressKey: progressKey,
        progress: loadProgress()
      };
      var slug = (progressKey.split('::')[1] || 'progress').replace(/[^a-z0-9]+/gi, '-');
      downloadJSON('doctor-study-progress-' + slug + '.json', payload);
    }
    function importProgressFromText(text){
      try {
        var data = JSON.parse(text);
        var incoming = data && data.progress ? data.progress : data;
        if(!incoming || typeof incoming !== 'object'){
          showStorageToast('导入失败：JSON 格式不正确。');
          return;
        }
        var current = loadProgress();
        Object.keys(incoming).forEach(function(k){
          var v = incoming[k];
          if(typeof v === 'number' || typeof v === 'string'){
            current[k] = Number(v) || Date.now();
          } else if(v) {
            current[k] = Date.now();
          }
        });
        saveProgress(current);
        syncProgress();
        showStorageToast('已导入 ' + Object.keys(incoming).length + ' 条进度记录。');
      } catch(err) {
        showStorageToast('导入失败：' + (err && err.message ? err.message : err));
      }
    }
    function resetProgress(){
      if(!window.confirm('确认清空本页所有学习进度？此操作不可撤销。')) return;
      try {
        localStorage.removeItem(progressKey);
      } catch(_) { /* ignore */ }
      syncProgress();
      showStorageToast('已重置本页学习进度。');
    }
    actionBtns.forEach(function(btn){
      btn.addEventListener('click', function(){
        var action = btn.dataset.action;
        if(action === 'export') exportProgress();
        else if(action === 'reset') resetProgress();
        else if(action === 'import' && importInput) importInput.click();
      });
    });
    if(importInput){
      importInput.addEventListener('change', function(){
        var file = importInput.files && importInput.files[0];
        if(!file) return;
        var reader = new FileReader();
        reader.onload = function(){ importProgressFromText(String(reader.result || '')); importInput.value = ''; };
        reader.onerror = function(){ showStorageToast('读取文件失败。'); importInput.value = ''; };
        reader.readAsText(file);
      });
    }

    // 多 tab 跨页同步
    window.addEventListener('storage', function(e){
      if(!e.key) return;
      if(e.key === progressKey) syncProgress();
    });

    // 级别筛选
    function applyLevel(level){
      levelChips.forEach(function(c){ c.classList.toggle('active', c.dataset.level === level); });
      buttons.forEach(function(btn){
        var l = btn.dataset.level || '';
        var match = (level === 'all') || (l === level);
        btn.dataset.levelHidden = match ? '' : '1';
        applyVisibility(btn);
      });
      try { localStorage.setItem(levelKey, level); } catch(_) { /* 隐私模式静默 */ }
    }
    function applyVisibility(btn){
      btn.hidden = !!btn.dataset.levelHidden || !!btn.dataset.queryHidden;
    }
    levelChips.forEach(function(c){
      c.addEventListener('click', function(){ applyLevel(c.dataset.level); });
    });

    // 分组折叠状态记忆
    function loadGroupState(){
      try { return JSON.parse(localStorage.getItem(groupKey) || '{}') || {}; }
      catch(_) { return {}; }
    }
    function saveGroupState(state){
      try { localStorage.setItem(groupKey, JSON.stringify(state)); } catch(_) { /* 隐私模式静默 */ }
    }
    var savedGroupState = loadGroupState();
    detailGroups.forEach(function(d){
      var id = d.dataset.groupId;
      if(id && Object.prototype.hasOwnProperty.call(savedGroupState, id)){
        if(savedGroupState[id]) d.setAttribute('open', ''); else d.removeAttribute('open');
      }
      d.addEventListener('toggle', function(){
        if(!id) return;
        var state = loadGroupState();
        state[id] = d.open;
        saveGroupState(state);
      });
    });

    setModuleCollapsed(group.classList.contains('module-collapsed'));
    updateCurrentTitle();
    syncProgress();
    var savedLevel = localStorage.getItem(levelKey);
    if(savedLevel && levelChips.length) applyLevel(savedLevel);
  });
});

// Long pages get a hidden drawer table of contents. Tab pages rebuild it per active tab.
document.addEventListener('DOMContentLoaded', function(){
  var wrap = document.querySelector('.wrap');
  if(!wrap || !document.querySelector('.topnav')) return;

  var observer = null;
  var usedIds = {};

  function collectHeadings(){
    var activePanel = wrap.querySelector('.tab-panel.active');
    var scope = activePanel || wrap;
    var selector = activePanel ? '.tab-panel-body > h3, .tab-panel-body > h4, .tab-panel-body > .card > h3, .tab-panel-body > .card > h4' : 'h2, h3';
    var allHeadings = Array.from(scope.querySelectorAll(selector)).filter(function(heading){
      return heading.textContent.trim().length > 0;
    });
    if(activePanel) return allHeadings;
    var h2Headings = allHeadings.filter(function(heading){
      return heading.tagName.toLowerCase() === 'h2';
    });
    return h2Headings.length >= 2 ? h2Headings : allHeadings;
  }

  function ensureHeadingIds(headings){
    headings.forEach(function(heading, index){
      if(!heading.id){
        var base = 'section-' + Object.keys(usedIds).length + '-' + index;
        var id = base;
        var suffix = 2;
        while(usedIds[id] || document.getElementById(id)){
          id = base + '-' + suffix;
          suffix += 1;
        }
        heading.id = id;
      }
      usedIds[heading.id] = true;
    });
  }

  var toc = document.createElement('nav');
  toc.className = 'page-toc';
  toc.setAttribute('aria-label', '本页目录');
  toc.innerHTML = '<div class="toc-head"><div><div class="toc-title">本页目录</div><div class="toc-tip">Alt + E 展开问答</div></div><button class="toc-close" type="button" aria-label="关闭目录">\u00d7</button></div><div class="toc-links"></div>';

  var toggle = document.createElement('button');
  toggle.className = 'toc-toggle';
  toggle.type = 'button';
  toggle.textContent = '目录';
  toggle.setAttribute('aria-expanded', 'false');

  var backdrop = document.createElement('div');
  backdrop.className = 'toc-backdrop';

  var links = toc.querySelector('.toc-links');

  function setTocOpen(open){
    document.body.classList.toggle('toc-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  function rebuildToc(){
    var headings = collectHeadings();
    ensureHeadingIds(headings);
    links.innerHTML = '';
    if(headings.length < 3){
      toc.hidden = true;
      toggle.hidden = true;
      setTocOpen(false);
      return;
    }
    toc.hidden = false;
    toggle.hidden = false;
    headings.forEach(function(heading){
      var btn = document.createElement('button');
      btn.type = 'button';
      var tag = heading.tagName.toLowerCase();
      btn.className = tag === 'h4' ? 'toc-h3' : (tag === 'h3' ? 'toc-h2' : 'toc-h2');
      btn.textContent = heading.textContent.replace(/\s+/g, ' ').trim();
      btn.addEventListener('click', function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        heading.scrollIntoView({behavior: 'smooth', block: 'start'});
        if(heading.id) history.replaceState(null, '', '#' + heading.id);
        setTimeout(function(){ setTocOpen(false); }, 150);
      });
      links.appendChild(btn);
    });
    if(observer) observer.disconnect();
    if('IntersectionObserver' in window){
      var tocBtns = Array.from(links.querySelectorAll('button'));
      observer = new IntersectionObserver(function(entries){
        entries.forEach(function(entry){
          if(!entry.isIntersecting) return;
          var idx = headings.indexOf(entry.target);
          if(idx < 0) return;
          tocBtns.forEach(function(b){ b.classList.remove('active'); });
          if(tocBtns[idx]) tocBtns[idx].classList.add('active');
        });
      }, {rootMargin: '-30% 0px -60% 0px', threshold: 0});
      headings.forEach(function(h){ observer.observe(h); });
    }
  }

  document.body.appendChild(toc);
  document.body.appendChild(toggle);
  document.body.appendChild(backdrop);

  toggle.addEventListener('click', function(){
    setTocOpen(!document.body.classList.contains('toc-open'));
  });
  backdrop.addEventListener('click', function(){ setTocOpen(false); });
  toc.querySelector('.toc-close').addEventListener('click', function(){ setTocOpen(false); });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') setTocOpen(false);
  });

  rebuildToc();
  document.addEventListener('tab:activated', function(){ rebuildToc(); });
});

// 首页跨页面汇总：扫描所有 progress key，把每张卡片渲染成 已读 N / 总 M
document.addEventListener('DOMContentLoaded', function(){
  var cards = document.querySelectorAll('.idx-card[data-progress-key]');
  if(!cards.length) return;
  function loadCount(key){
    try {
      var raw = localStorage.getItem(key);
      if(!raw) return 0;
      var obj = JSON.parse(raw) || {};
      return Object.keys(obj).length;
    } catch(_) { return 0; }
  }
  function refresh(){
    cards.forEach(function(card){
      var key = card.dataset.progressKey;
      var total = parseInt(card.dataset.progressTotal, 10) || 0;
      var done = loadCount(key);
      var badge = card.querySelector('.idx-card-progress');
      var text = card.querySelector('.idx-card-progress-text');
      if(!badge || !text || total <= 0) return;
      badge.hidden = false;
      text.textContent = done + ' / ' + total;
      card.classList.toggle('is-started', done > 0);
      card.classList.toggle('is-complete', done >= total);
    });
  }
  refresh();
  window.addEventListener('storage', function(e){
    if(e.key && e.key.indexOf('doctor-study-progress::') === 0) refresh();
  });
});
