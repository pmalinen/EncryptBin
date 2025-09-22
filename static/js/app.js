/* Theme toggle */
(function(){
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  const set = (m)=>document.documentElement.classList.toggle('dark', m==='dark');
  set(localStorage.getItem('theme') || (prefersDark.matches?'dark':'light'));
  const btn = document.getElementById('themeToggle');
  if (btn) btn.addEventListener('click', ()=>{
    const d = document.documentElement.classList.contains('dark') ? 'light':'dark';
    localStorage.setItem('theme', d); set(d);
  });
})();

/* Base64 helpers */
function bytesToBase64(buf){
  if (buf instanceof Uint8Array) {
    return btoa(String.fromCharCode(...buf));
  }
  return btoa(String.fromCharCode(...new Uint8Array(buf)));
}
function base64ToBytes(b64){const bin=atob(b64);const bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);return bytes.buffer;}
function toBase64Url(b){return bytesToBase64(b).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
function fromBase64Url(s){const pad=s.length%4===2?'==':s.length%4===3?'=':'';return base64ToBytes(s.replace(/-/g,'+').replace(/_/g,'/')+pad);}

/* Highlight helpers */
function detectLanguage(sample){
  try { const det=hljs.highlightAuto(sample); return det.language || 'plaintext'; }
  catch(e){ return 'plaintext'; }
}
function highlightBlock(codeEl, lang){
  // 1) Reset: strip any previous <span> markup by re-setting textContent
  const raw = codeEl.textContent;
  codeEl.className = 'hljs';
  codeEl.textContent = raw;

  // 2) Plaintext => leave it plain (no syntax classes or spans)
  if (!lang || lang === 'plaintext') return;

  // 3) Known language => add class and highlight
  if (hljs.getLanguage(lang)) {
    codeEl.classList.add('language-' + lang);
    hljs.highlightElement(codeEl);
  }
}

/* ---------- New Paste Page (Write/Preview) ---------- */
function setupTabs(){
  const tabs = document.querySelectorAll('.tab');
  const writePane = document.getElementById('writePane');
  const previewPane = document.getElementById('previewPane');
  if (!tabs.length || !writePane || !previewPane) return;

  tabs.forEach(t=>t.addEventListener('click', ()=>{
    tabs.forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    if (t.dataset.tab==='write'){
      writePane.classList.remove('hidden');
      previewPane.classList.add('hidden');
    } else {
      writePane.classList.add('hidden');
      previewPane.classList.remove('hidden');
      buildPreviewFromInputs();
    }
  }));
}

function buildPreview(text, forcedLang){
  const trimmed = text.replace(/\n+$/,'');
  const pane = document.getElementById('previewCode');
  const sel = document.getElementById('langSelectNew');
  const detLbl = document.getElementById('detectedLangNew');
  if(!pane) return;

  pane.innerHTML='';
  const frag=document.createDocumentFragment();
  const lines = trimmed.split('\n');
  lines.forEach((line,i)=>{
    const row=document.createElement('div');
    row.className='row'+(line.startsWith('+')?' added':line.startsWith('-')?' removed':'');
    const ln=document.createElement('span'); ln.className='ln'; ln.textContent=String(i+1);
    const pre=document.createElement('pre'); const code=document.createElement('code'); code.textContent=line; pre.appendChild(code);
    row.appendChild(ln); row.appendChild(pre); frag.appendChild(row);
  });
  pane.appendChild(frag);

  const sample = trimmed.slice(0,2000);
  const detected = forcedLang || detectLanguage(sample);
  if (detLbl) detLbl.textContent = detected || 'plaintext';

  if (sel && (sel.dataset.filled!=='1' || forcedLang)){
    sel.innerHTML='';
    const langs = hljs.listLanguages ? hljs.listLanguages() : [];
    if (detected && !langs.includes(detected)) langs.unshift(detected);
    langs.forEach(l=>{
      const opt=document.createElement('option'); opt.value=l; opt.textContent=l; if(l===detected) opt.selected=true; sel.appendChild(opt);
    });
    sel.dataset.filled='1';
    sel.onchange = ()=>{ buildPreview(trimmed, sel.value); };
  }

  const lang = sel && sel.value ? sel.value : detected;
  pane.querySelectorAll('code').forEach(code=>highlightBlock(code, lang));
}

async function buildPreviewFromInputs(){
  const ta = document.getElementById('content');
  const fi = document.getElementById('file');
  let text = ta ? ta.value : '';
  if (fi && fi.files && fi.files[0]) {
    try { text = await fi.files[0].text(); } catch(e){}
  }
  buildPreview(text);
}

async function encryptAndSubmit(evt){
  evt.preventDefault();
  const title=(document.getElementById('title').value||'').trim();
  const exp=document.querySelector('input[name="expires"]:checked').value;
  const burn=(exp==='burn'); const expires=burn?'never':exp;

  const ta=document.getElementById('content');
  const fi=document.getElementById('file');
  let plaintext=(ta.value||'').trim();
  if(fi && fi.files && fi.files[0]){ plaintext = await fi.files[0].text(); }
  if(!plaintext){ alert('Please paste content or choose a file.'); return; }

  const K=crypto.getRandomValues(new Uint8Array(32));
  const key=await crypto.subtle.importKey('raw', K, 'AES-GCM', false, ['encrypt']);
  const iv=crypto.getRandomValues(new Uint8Array(12));
  const ct=await crypto.subtle.encrypt({name:'AES-GCM', iv}, key, new TextEncoder().encode(plaintext));
  const payload={ alg:'AES-GCM', iv_b64:bytesToBase64(iv), ciphertext_b64:bytesToBase64(new Uint8Array(ct)), title, expires, burn_after:burn };

  const res=await fetch('/api/paste_encrypted',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  if(!res.ok){ alert('Failed to create paste'); return; }

  const data=await res.json();
  try{ localStorage.setItem('edit:'+data.id, data.edit_key);}catch(e){}
  const keyUrl = toBase64Url(K.buffer);
  window.location.href = data.url + '#' + keyUrl;
}

/* ---------- View Paste Page ---------- */
function buildView(text, forcedLang){
  const trimmed = text.replace(/\n+$/,'');
  const pane = document.getElementById('code');
  const sel = document.getElementById('langSelect');
  const detLbl = document.getElementById('detectedLang');
  if(!pane) return;

  pane.innerHTML='';
  const frag=document.createDocumentFragment();
  const lines = trimmed.split('\n');
  lines.forEach((line,i)=>{
    const row=document.createElement('div');
    row.className='row'+(line.startsWith('+')?' added':line.startsWith('-')?' removed':'');
    const ln=document.createElement('span'); ln.className='ln'; ln.textContent=String(i+1);
    const pre=document.createElement('pre'); const code=document.createElement('code'); code.textContent=line; pre.appendChild(code);
    row.appendChild(ln); row.appendChild(pre); frag.appendChild(row);
  });
  pane.appendChild(frag);

  const sample = trimmed.slice(0,2000);
  const detected = forcedLang || detectLanguage(sample);
  if (detLbl) detLbl.textContent = detected || 'plaintext';

  if (sel){
    sel.innerHTML='';
    const langs = hljs.listLanguages ? hljs.listLanguages() : [];
    if (detected && !langs.includes(detected)) langs.unshift(detected);
    langs.forEach(l=>{
      const opt=document.createElement('option'); opt.value=l; opt.textContent=l; if(l===detected) opt.selected=true; sel.appendChild(opt);
    });
    sel.onchange = ()=>{
      const lang = sel.value;
      if (detLbl) detLbl.textContent = lang;
      pane.querySelectorAll('code').forEach(code=>highlightBlock(code, lang));
    };
  }

  const lang = sel && sel.value ? sel.value : detected;
  pane.querySelectorAll('code').forEach(code=>highlightBlock(code, lang));
}

async function renderView(){
  const enc = window.__ENCRYPTED__;
  const plain = window.__PLAINTEXT__;
  const pane=document.getElementById('code');
  if(!pane) return;

  if (enc && typeof enc === 'object' && Object.keys(enc).length > 0){
    const hash = location.hash.replace('#',''); if(!hash){ pane.textContent='[Missing key in URL]'; return; }
    try{
      const K = new Uint8Array(fromBase64Url(hash));
      const o = enc;
      const iv = new Uint8Array(base64ToBytes(o.iv_b64));
      const ct = new Uint8Array(base64ToBytes(o.ciphertext_b64));
      const key = await crypto.subtle.importKey('raw', K, 'AES-GCM', false, ['decrypt']);
      const pt = await crypto.subtle.decrypt({name:'AES-GCM', iv}, key, ct);
      const text = new TextDecoder().decode(pt);
      buildView(text);
    }catch(e){
      pane.textContent='[Decryption failed]';
    }
  } else {
    // Plaintext
    buildView(plain || '');
  }
}

/* ---------- Common Helpers ---------- */
function copyToClipboard(text, btn){
  navigator.clipboard.writeText(text).then(()=>{
    if(btn){ const old=btn.textContent; btn.textContent='Copied!'; setTimeout(()=>btn.textContent=old,1200); }
  });
}
function setupCopy(){
  const b1=document.getElementById('copyUrlSafeBtn');
  if(b1) b1.addEventListener('click', ()=>copyToClipboard(location.href, b1));
  const b2=document.getElementById('copyPasteBtn');
  if(b2) b2.addEventListener('click', ()=>{
    const text = Array.from(document.querySelectorAll('#code pre code')).map(c=>c.textContent).join('\n');
    copyToClipboard(text, b2);
  });
}

/* Inline title edit */
function setupEditTitle(){
  const titleEl=document.getElementById('pasteTitle');
  if(!titleEl) return;
  const key=localStorage.getItem('edit:'+window.__PASTE_ID__);
  if(!key) return;
  titleEl.addEventListener('blur', async ()=>{
    const newTitle=titleEl.textContent.trim();
    const res=await fetch('/api/paste/'+window.__PASTE_ID__,{
      method:'PATCH',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},
      body:JSON.stringify({title:newTitle})
    });
    if(!res.ok) alert('Failed to update title');
  });
}

/* Init */
document.addEventListener('DOMContentLoaded', ()=>{
  setupTabs();
  const form=document.getElementById('newPasteForm');
  if(form){ form.addEventListener('submit', encryptAndSubmit); }
  renderView();
  setupCopy();
  setupEditTitle();
});
