// QA blocks already have inline onclick="this.classList.toggle('open')".
// Alt+E: expand / collapse all Q&A on current page.
document.addEventListener('keydown', function(e){
  if(e.key === 'e' && e.altKey){
    var qas = document.querySelectorAll('.qa');
    if(!qas.length) return;
    var allOpen = [...qas].every(q => q.classList.contains('open'));
    qas.forEach(q => allOpen ? q.classList.remove('open') : q.classList.add('open'));
  }
});
