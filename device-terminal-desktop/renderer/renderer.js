const grid = document.getElementById('grid');

function newCard(){
  const card = document.createElement('section');
  card.className='card';
  card.innerHTML = `<div class="toolbar"><button class="close">Close</button></div><div class="term"></div>`;
  grid.prepend(card);
  const termDiv = card.querySelector('.term');
  const term = new window.Terminal({ convertEol:true, theme:{ background:'#141821', foreground:'#e6eaf2', cursor:'#a3bffa' } });
  term.open(termDiv);
  window.terminalAPI.create({}).then(({pid})=>{
    window.terminalAPI.onData(pid, data=> term.write(data));
    term.onData(data => window.terminalAPI.write(pid, data));
    const ro = new ResizeObserver(()=>{
      const cols = term.cols, rows = term.rows;
      window.terminalAPI.resize(pid,{cols,rows});
    });
    ro.observe(termDiv);
  });
  card.querySelector('.close').onclick=()=>card.remove();
}

window.addEventListener('DOMContentLoaded', ()=>{
  document.getElementById('new').onclick = newCard;
  newCard();
});
