(function(){'use strict';
const shell=document.querySelector('.app-shell'), sidebar=document.getElementById('sidebar');
const buttons=[document.getElementById('collapseSidebar'),document.getElementById('desktopMenuToggle')].filter(Boolean);
function setCollapsed(value){if(!shell)return;shell.classList.toggle('sidebar-compact',value);buttons.forEach(b=>{b.setAttribute('aria-label',value?'Mostrar menú':'Ocultar menú');b.setAttribute('title',value?'Mostrar menú':'Ocultar menú');b.setAttribute('aria-expanded',String(!value));b.textContent=value?'»':'«';});try{localStorage.setItem('biblioteca-menu-compacto',value?'1':'0');}catch(e){}}
try{setCollapsed(localStorage.getItem('biblioteca-menu-compacto')==='1');}catch(e){setCollapsed(false);}
buttons.forEach(b=>b.addEventListener('click',()=>{if(window.matchMedia('(max-width:760px)').matches){sidebar?.classList.toggle('open');return;}setCollapsed(!shell.classList.contains('sidebar-compact'));}));
const menu=document.getElementById('profileMenu'), trigger=document.getElementById('profileTrigger'), dropdown=document.getElementById('profileDropdown');
function close(){if(dropdown)dropdown.hidden=true;trigger?.setAttribute('aria-expanded','false');}
trigger?.addEventListener('click',()=>{const open=dropdown.hidden;dropdown.hidden=!open;trigger.setAttribute('aria-expanded',String(open));});
document.addEventListener('click',e=>{if(menu&&!menu.contains(e.target))close();});document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
})();