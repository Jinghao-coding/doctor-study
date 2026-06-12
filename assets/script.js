// Theme: respect saved preference, then system preference.
(function(){
  var savedTheme = localStorage.getItem('doctor-study-theme');
  if(savedTheme === 'light' || savedTheme === 'dark'){
    document.documentElement.setAttribute('data-theme', savedTheme);
  }
})();

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
    localStorage.setItem('doctor-study-theme', next);
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
      localStorage.setItem(widthKey, String(Math.round(clamped)));
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
      localStorage.setItem(progressKey, JSON.stringify(state));
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
          if(label) label.textContent = isDone ? '已学习' : '标记为已学习';
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

    // 级别筛选
    function applyLevel(level){
      levelChips.forEach(function(c){ c.classList.toggle('active', c.dataset.level === level); });
      buttons.forEach(function(btn){
        var l = btn.dataset.level || '';
        var match = (level === 'all') || (l === level);
        btn.dataset.levelHidden = match ? '' : '1';
        applyVisibility(btn);
      });
      localStorage.setItem(levelKey, level);
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
    function saveGroupState(state){ localStorage.setItem(groupKey, JSON.stringify(state)); }
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
