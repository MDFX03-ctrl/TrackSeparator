(() => {
  const $ = id => document.getElementById(id);
  const names = ['vocals', 'drums', 'bass', 'guitar', 'piano', 'other'];
  const label = name => name[0].toUpperCase() + name.slice(1);
  let selected = null, songs = [], active = null, modelReady = false;
  let signature = '', polling = false, uploading = false, stopped = false;
  const message = (text, error=false) => { $('message').textContent=text; $('message').classList.toggle('error',error); };
  async function api(path, payload, method='POST') {
    const response = await fetch(path, payload===undefined?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Request failed');
    return result;
  }
  function button(text, action, quiet=false) {
    const el = document.createElement('button'); el.textContent=text; el.type='button';
    if(quiet) el.className='quiet';
    el.onclick=()=>Promise.resolve().then(action).catch(e=>message(e.message,true));
    return el;
  }
  function audioUrl(stem) {
    return '/api/audio?'+new URLSearchParams({id:selected,stem});
  }
  function select(id) {
    selected=id;
    const song=songs.find(s=>s.id===id);
    $('audio').pause(); $('audio').removeAttribute('src'); $('audio').load();
    $('listen').hidden=!song?.ready;
    if(!song?.ready)return;
    $('trackTitle').textContent=song.title;
    $('lane').replaceChildren();
    for(const name of ['input',...names]) {
      const option=document.createElement('option');option.value=name;option.textContent=name==='input'?'Full mix':label(name);$('lane').append(option);
    }
    $('audio').src=audioUrl('input');
    $('stemFolder').textContent=song.folder;
  }
  async function separate(id) {
    await api('/api/separate',{id});message('Separating the track. You can close this tab and return later.');await poll();
  }
  async function upload(file) {
    if(!file)return;
    if(uploading)throw new Error('An import is already in progress');
    uploading=true;$('file').disabled=true;
    try {
      message('Importing '+file.name+'…');
      const response=await fetch('/api/import?'+new URLSearchParams({filename:file.name}),{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Track-Separator-Upload':'1'},body:file});
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Import failed');
      await poll();
      if(modelReady && !active)await separate(result.id);
      else message('Imported. '+(modelReady?'Choose Separate when processing finishes.':'Download the model, then choose Separate.'));
    } finally {uploading=false;$('file').disabled=false;$('file').value='';}
  }
  async function poll() {
    if(polling || stopped)return;polling=true;
    try {
      const [library,jobs,setup]=await Promise.all([api('/api/library'),api('/api/jobs'),api('/api/setup')]);
      songs=library.songs;active=jobs.active;modelReady=setup.ready;
      $('modelState').textContent=setup.message;$('model').textContent=modelReady?'Repair model':'Download model (about 52 MB)';$('model').disabled=!!active;
      if(document.activeElement!==$('libraryPath'))$('libraryPath').value=library.settings.library;
      const job=jobs.jobs.find(j=>j.id===active)||jobs.jobs[0];
      if(job) {
        const elapsed=Math.max(0,Math.round((job.finished||Date.now()/1000)-(job.started||job.created)));
        const progress=job.progress||{};
        $('job').textContent=`${job.status} · ${job.stage} · ${elapsed}s`+(progress.total?` · ${Math.round((progress.downloaded||0)/progress.total*100)}%`:'')+(job.error?'\n'+job.error:'');
      } else $('job').textContent='No processing jobs.';
      $('cancel').hidden=!active;
      const next=JSON.stringify([songs,active,modelReady,jobs.jobs.map(j=>[j.id,j.status,j.attempt])]);
      if(next===signature)return;signature=next;
      $('library').replaceChildren();
      for(const song of songs) {
        const row=document.createElement('div');row.className='track';
        const title=document.createElement('span');title.textContent=song.title;
        const state=document.createElement('small');state.textContent=song.error||(song.ready?'Six stems ready':'Ready to separate');title.append(state);
        const actions=document.createElement('div');actions.className='actions';
        const open=song.ready?button('Open stems',()=>select(song.id)):button('Separate',()=>separate(song.id));
        if(!song.ready)open.disabled=!!active||!modelReady;
        const remove=button('Remove',async()=>{
          const response=await fetch('/api/tracks?'+new URLSearchParams({id:song.id}),{method:'DELETE'});
          const result=await response.json();if(!response.ok)throw new Error(result.error||'Could not remove track');
          if(selected===song.id)select(null);await poll();message('Moved to recoverable trash.');
        },true);remove.disabled=!!active;
        actions.append(open,remove);row.append(title,actions);$('library').append(row);
      }
      if(!songs.length)$('library').textContent='Your imported tracks will appear here.';
      $('retries').replaceChildren();
      for(const job of jobs.jobs.filter(j=>['failed','cancelled','interrupted'].includes(j.status))) {
        const row=document.createElement('div');row.className='track';const text=document.createElement('span');text.textContent=job.error||job.status;
        const retry=button('Retry',()=>api('/api/jobs/retry',{id:job.id}).then(poll));retry.disabled=!!active;row.append(text,retry);$('retries').append(row);
      }
      if(selected && !songs.some(s=>s.id===selected))select(null);
      if(!selected && !active && songs.some(s=>s.ready))select(songs.find(s=>s.ready).id);
    } finally {polling=false;}
  }
  async function trash() {
    const result=await api('/api/trash');$('trash').replaceChildren();
    for(const item of result.items) {
      const row=document.createElement('div');row.className='track';const title=document.createElement('span');title.textContent=item.title;
      row.append(title,button('Restore',async()=>{await api('/api/trash/restore',{ticket:item.ticket});await poll();await trash();}));$('trash').append(row);
    }
    if(!result.items.length)$('trash').textContent='Trash is empty.';
  }
  $('file').onchange=e=>upload(e.target.files[0]).catch(e=>message(e.message,true));
  $('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('over');};
  $('drop').ondragleave=()=>$('drop').classList.remove('over');
  $('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('over');if(e.dataTransfer.files.length!==1){message('Choose one track at a time.',true);return;}upload(e.dataTransfer.files[0]).catch(e=>message(e.message,true));};
  $('openFolder').onclick=()=>api('/api/open-folder',{id:selected}).then(()=>message('Opened the local stems folder.')).catch(e=>message(e.message,true));
  $('lane').onchange=()=>{$('audio').pause();$('audio').src=audioUrl($('lane').value);$('audio').load();};
  $('model').onclick=()=>api('/api/setup',{}).then(poll).catch(e=>message(e.message,true));
  $('cancel').onclick=()=>api('/api/jobs/cancel',{id:active}).then(poll).catch(e=>message(e.message,true));
  $('showTrash').onclick=()=>trash().catch(e=>message(e.message,true));
  $('changeLibrary').onclick=()=>api('/api/settings',{library:$('libraryPath').value}).then(()=>location.reload()).catch(e=>message(e.message,true));
  $('quit').onclick=()=>api('/api/shutdown',{}).then(()=>{stopped=true;$('audio').pause();message('App stopped. Close this tab.');}).catch(e=>message(e.message,true));
  poll().catch(e=>message(e.message,true));setInterval(()=>poll().catch(e=>message(e.message,true)),2000);
})();
