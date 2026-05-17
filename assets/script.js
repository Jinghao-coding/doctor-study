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

// Long pages get a hidden drawer table of contents from h2/h3.
document.addEventListener('DOMContentLoaded', function(){
  var wrap = document.querySelector('.wrap');
  if(!wrap || !document.querySelector('.topnav')) return;

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
