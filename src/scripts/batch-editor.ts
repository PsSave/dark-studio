import {drawComposition,templatePayload} from './templates';
type Recipe={normalizedCrop:any,muted:boolean,template:any};
export function initBatchEditor(getRecipe:()=>Recipe|null){
 const $=(s:string)=>document.querySelector(s) as HTMLElement;
 const dialog=$('#batch-dialog') as HTMLDialogElement,profile=$('#batch-profile') as HTMLSelectElement;
 const selected=new Set<string>();let videos:any[]=[],page=0,version=0,recipe:Recipe|null=null,requestId='',sending=false,players:HTMLVideoElement[]=[];
 const visible=()=>videos.filter(v=>!profile.value||v.profile===profile.value);
 const note=(s:string)=>$('#batch-message').textContent=s;
 function controls(){const count=selected.size;$('#batch-count').textContent=`${count} vídeos selecionados`;($('#batch-confirm') as HTMLButtonElement).disabled=!count||sending;$('#batch-confirm').textContent=sending?'Preparando lote…':`Gerar ${count} criativos`;}
 function cleanup(){players.forEach(v=>{v.pause();v.removeAttribute('src');v.load();});players=[];}
 function render(){const generation=++version;cleanup();const all=visible(),pages=Math.max(1,Math.ceil(all.length/6));page=Math.min(page,pages-1);$('#batch-page').textContent=`${page+1} / ${pages}`;($('#batch-prev') as HTMLButtonElement).disabled=page===0;($('#batch-next') as HTMLButtonElement).disabled=page===pages-1;
 const list=$('#batch-previews');list.replaceChildren();for(const item of all.slice(page*6,page*6+6)){
 const card=document.createElement('label');card.className='batch-preview';const check=document.createElement('input');check.type='checkbox';check.checked=selected.has(item.id);check.addEventListener('change',()=>{check.checked?selected.add(item.id):selected.delete(item.id);controls();});const title=document.createElement('span');title.textContent='@'+item.profile;const canvas=document.createElement('canvas'),status=document.createElement('small');status.textContent='Carregando prévia…';card.append(check,title,canvas,status);list.append(card);
 const video=document.createElement('video');video.muted=true;video.preload='auto';video.src='/api/media?id='+encodeURIComponent(item.id);players.push(video);
 const paint=()=>{if(generation!==version||!recipe)return;const n=recipe.normalizedCrop,w=video.videoWidth,h=video.videoHeight;const crop={x:Math.floor(n.x*w/2)*2,y:Math.floor(n.y*h/2)*2,width:Math.floor(n.width*w/2)*2,height:Math.floor(n.height*h/2)*2};
 if(!w||!h||crop.width<2||crop.height<2){status.textContent='Área incompatível; ajuste este vídeo no Editor.';return;}
 if(recipe.template)drawComposition(video,crop,true,canvas);else{canvas.width=320;canvas.height=Math.round(320*crop.height/crop.width);canvas.getContext('2d')!.drawImage(video,crop.x,crop.y,crop.width,crop.height,0,0,canvas.width,canvas.height);}
 status.textContent=`${crop.width} × ${crop.height} · ${Math.round(video.duration)} s · prévia de um quadro`;};
 video.addEventListener('loadeddata',()=>{paint();if(video.duration>.6)video.currentTime=.5;});video.addEventListener('seeked',paint);video.addEventListener('error',()=>{if(generation===version)status.textContent='Prévia indisponível. Confira no Editor.';});
 }controls();}
 for(const trigger of ['#apply-others','#apply-others-crop'])$(trigger).addEventListener('click',async()=>{recipe=getRecipe();if(!recipe)return;requestId=crypto.randomUUID();page=0;selected.clear();note('');dialog.showModal();try{const r=await fetch('/api/library'),data=await r.json();if(!r.ok)throw Error(data.error);videos=data.videos.filter(v=>v.status==='downloaded');profile.replaceChildren(new Option('Todos os perfis',''));for(const p of [...new Set(videos.map(v=>v.profile))] as string[])profile.add(new Option('@'+p,p));($('#batch-name') as HTMLInputElement).value=recipe.template?'Lote · '+recipe.template.name:'Lote de recortes';render();}catch(e){note(e.message);}});
 $('#batch-close').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>{version++;cleanup();});profile.addEventListener('change',()=>{page=0;render();});
 $('#batch-all').addEventListener('click',()=>{visible().forEach(v=>selected.add(v.id));render();});$('#batch-none').addEventListener('click',()=>{visible().forEach(v=>selected.delete(v.id));render();});
 $('#batch-prev').addEventListener('click',()=>{page--;render();});$('#batch-next').addEventListener('click',()=>{page++;render();});
 $('#batch-confirm').addEventListener('click',async()=>{if(!recipe||!selected.size||sending)return;const name=($('#batch-name') as HTMLInputElement).value.trim();if(!name){note('Dê um nome ao lote.');return;}sending=true;controls();try{const r=await fetch('/api/creatives',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'create',requestId,name,sourceIds:[...selected],...recipe})}),data=await r.json();if(!r.ok)throw Error(data.error);location.href='/criativos?batch='+encodeURIComponent(data.id);}catch(e){note(e.message);}finally{sending=false;controls();}});
}
