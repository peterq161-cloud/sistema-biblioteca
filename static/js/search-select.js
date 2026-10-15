document.addEventListener('DOMContentLoaded', () => {
  const combos = [...document.querySelectorAll('[data-combobox]')];
  if (!combos.length) return;
  const formulario = combos[0].closest('form');
  combos.forEach(wrap => {
    const entrada = wrap.querySelector('input[role="combobox"]');
    const oculto = wrap.querySelector('input[type="hidden"]');
    const lista = wrap.querySelector('[role="listbox"]');
    const error = wrap.querySelector('.autocomplete-error');
    let opciones = [], indice = -1, temporizador, controlador, elegido = false;
    const cerrar = () => { lista.hidden = true; entrada.setAttribute('aria-expanded', 'false'); indice = -1; };
    const marcar = () => [...lista.children].forEach((n, i) => { n.setAttribute('aria-selected', i === indice ? 'true' : 'false'); n.style.background = i === indice ? '#e8f5ef' : ''; });
    const elegir = o => { if(o.deshabilitado)return; oculto.value = o.id; entrada.value = o.texto; elegido = true; error.hidden = true; cerrar(); };
    function mostrar(datos){ opciones = datos; lista.replaceChildren(); indice = -1;
      datos.forEach((o, i) => { const n = document.createElement('div'); n.setAttribute('role','option'); n.textContent = o.texto; n.style.cssText = 'padding:10px 12px;cursor:pointer;border-bottom:1px solid #edf1f4;font-size:13px'; if(o.deshabilitado){n.style.opacity='.5';n.style.cursor='not-allowed';n.setAttribute('aria-disabled','true');} n.addEventListener('mousedown',e=>{e.preventDefault();elegir(o);}); lista.append(n); });
      if(!datos.length){const n=document.createElement('div');n.textContent='No se encontraron coincidencias';n.style.padding='12px';lista.append(n);} lista.hidden=false;entrada.setAttribute('aria-expanded','true'); }
    entrada.addEventListener('input', () => { elegido = false; oculto.value = ''; error.hidden = true; clearTimeout(temporizador); if(controlador)controlador.abort(); const q=entrada.value.trim();if(!q){cerrar();return;}temporizador=setTimeout(async()=>{controlador=new AbortController();try{const r=await fetch(wrap.dataset.endpoint+'?q='+encodeURIComponent(q),{signal:controlador.signal,credentials:'same-origin'});if(!r.ok)return;const d=await r.json();if(entrada.value.trim()===q)mostrar(d.resultados||[]);}catch(e){if(e.name!=='AbortError')cerrar();}},200); });
    entrada.addEventListener('keydown', e=>{if(e.key==='Escape'){cerrar();return;}if(lista.hidden)return;const habilitadas=opciones.map((o,i)=>o.deshabilitado?-1:i).filter(i=>i>=0);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(!habilitadas.length)return;let pos=habilitadas.indexOf(indice);pos=(pos+(e.key==='ArrowDown'?1:-1)+habilitadas.length)%habilitadas.length;indice=habilitadas[pos];marcar();}else if(e.key==='Enter'){e.preventDefault();if(indice>=0)elegir(opciones[indice]);}});
    entrada.addEventListener('blur',()=>setTimeout(cerrar,150));
    wrap.validar=()=>{const ok=elegido&&oculto.value;error.hidden=!!ok;if(!ok)entrada.setAttribute('aria-invalid','true');else entrada.removeAttribute('aria-invalid');return !!ok;};
  });
  formulario.addEventListener('submit',e=>{let primero=null;combos.forEach(w=>{if(!w.validar()&&!primero)primero=w.querySelector('input[role="combobox"]');});if(primero){e.preventDefault();primero.focus();}});
});
