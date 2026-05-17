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
  var nav = document.querySelector('.topnav');
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

document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('[data-tabs]').forEach(function(group){
    var buttons = Array.from(group.querySelectorAll('.tab-button'));
    var panels = Array.from(group.querySelectorAll('.tab-panel'));
    if(!buttons.length || !panels.length) return;

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
    }

    buttons.forEach(function(button, index){
      button.addEventListener('click', function(){ activate(index); });
      button.addEventListener('keydown', function(e){
        if(e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        var next = e.key === 'ArrowRight' ? index + 1 : index - 1;
        if(next < 0) next = buttons.length - 1;
        if(next >= buttons.length) next = 0;
        buttons[next].focus();
        activate(next);
      });
    });
  });
});

// Long pages get a hidden drawer table of contents from h2/h3.
document.addEventListener('DOMContentLoaded', function(){
  var wrap = document.querySelector('.wrap');
  if(!wrap || !document.querySelector('.topnav')) return;
  if(document.querySelector('[data-tabs]')) return;

  var allHeadings = Array.from(wrap.querySelectorAll('h2, h3')).filter(function(heading){
    return heading.textContent.trim().length > 0;
  });
  var h2Headings = allHeadings.filter(function(heading){
    return heading.tagName.toLowerCase() === 'h2';
  });
  var headings = h2Headings.length >= 2 ? h2Headings : allHeadings;
  if(headings.length < 3) return;

  var usedIds = {};
  headings.forEach(function(heading, index){
    if(!heading.id){
      var base = 'section-' + (index + 1);
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

  var toc = document.createElement('nav');
  toc.className = 'page-toc';
  toc.setAttribute('aria-label', '本页目录');
  toc.innerHTML = '<div class="toc-head"><div><div class="toc-title">本页目录</div><div class="toc-tip">Alt + E 展开问答</div></div><button class="toc-close" type="button" aria-label="关闭目录">×</button></div><div class="toc-links"></div>';

  var toggle = document.createElement('button');
  toggle.className = 'toc-toggle';
  toggle.type = 'button';
  toggle.textContent = '目录';
  toggle.setAttribute('aria-expanded', 'false');

  var backdrop = document.createElement('div');
  backdrop.className = 'toc-backdrop';

  var links = toc.querySelector('.toc-links');
  headings.forEach(function(heading){
    var link = document.createElement('a');
    link.href = '#' + heading.id;
    link.className = heading.tagName.toLowerCase() === 'h3' ? 'toc-h3' : 'toc-h2';
    link.textContent = heading.textContent.replace(/\s+/g, ' ').trim();
    links.appendChild(link);
  });

  var insertAfter = wrap.querySelector('.sub') || wrap.querySelector('h1');
  insertAfter.insertAdjacentElement('afterend', toc);
  document.body.appendChild(toggle);
  document.body.appendChild(backdrop);

  function setTocOpen(open){
    document.body.classList.toggle('toc-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  toggle.addEventListener('click', function(){
    setTocOpen(!document.body.classList.contains('toc-open'));
  });
  backdrop.addEventListener('click', function(){ setTocOpen(false); });
  toc.querySelector('.toc-close').addEventListener('click', function(){ setTocOpen(false); });
  links.addEventListener('click', function(e){
    if(e.target.tagName.toLowerCase() === 'a') setTocOpen(false);
  });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') setTocOpen(false);
  });

  if('IntersectionObserver' in window){
    var tocLinks = Array.from(links.querySelectorAll('a'));
    var observer = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(!entry.isIntersecting) return;
        tocLinks.forEach(function(link){ link.classList.remove('active'); });
        var active = links.querySelector('a[href="#' + entry.target.id + '"]');
        if(active) active.classList.add('active');
      });
    }, {rootMargin: '-30% 0px -60% 0px', threshold: 0});

    headings.forEach(function(heading){ observer.observe(heading); });
  }
});
