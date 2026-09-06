type Area={x:number,y:number,width:number,height:number};
const $=(s:string)=>document.querySelector(s) as HTMLElement;
const field=(s:string)=>$(s) as HTMLInputElement;
let templates:any[]=[],current:any=null,image:HTMLImageElement|null=null,loadVersion=0,redraw=()=>{},loaded=false;
const picker=()=>$('#template-picker') as HTMLSelectElement;
function info(s:string,error=false){$('#template-message').textContent=s;$('#template-message').classList.toggle('error',error);}
function valid(){return current&&['x','y','slot_w','slot_h'].every(k=>Number.isInteger(current[k]))&&current.x>=0&&current.y>=0&&current.slot_w>=2&&current.slot_h>=2&&current.x+current.slot_w<=current.width&&current.y+current.slot_h<=current.height;}
export function templateReady(){return !current||(loaded&&valid());}
export function templatePayload(){return current?{id:current.id,name:current.name,x:current.x,y:current.y,slot_w:current.slot_w,slot_h:current.slot_h,fit:current.fit,layer:current.layer}:null;}
export function templateDescription(){return current?`${current.width} × ${current.height} · ${current.name}`:'';}
function sync(inputs=true){$('#template-stage').hidden=!current;$('#template-controls').hidden=!current;$('#no-template').hidden=!!current;
 if(current){if(inputs){field('#template-name').value=current.name;for(const k of ['x','y','slot_w','slot_h'])field('#slot-'+k).value=String(current[k]);($('#template-fit') as HTMLSelectElement).value=current.fit;($('#template-layer') as HTMLSelectElement).value=current.layer||'behind';}
 const box=$('#slot-box');box.style.left=current.x/current.width*100+'%';box.style.top=current.y/current.height*100+'%';box.style.width=current.slot_w/current.width*100+'%';box.style.height=current.slot_h/current.height*100+'%';}
 ($('#save-template') as HTMLButtonElement).disabled=!valid()||!current?.name?.trim();redraw();}
function list(){picker().replaceChildren(new Option('Sem template — exportar só o recorte',''));for(const t of templates)picker().add(new Option(t.name,t.id));picker().value=current?.id||'';}
async function choose(id:string,override:any=null){const v=++loadVersion;current=id?{...templates.find(t=>t.id===id),...override}:null;loaded=false;image=null;sync();if(!current)return;const img=new Image();img.onload=()=>{if(v!==loadVersion)return;image=img;loaded=true;sync();};img.onerror=()=>{if(v===loadVersion)info('Não foi possível abrir a arte.',true);};img.src='/api/templates?asset='+encodeURIComponent(id)+'&v='+encodeURIComponent(current.filename);try{localStorage.setItem('dark-active-template',id);}catch{}}
export async function restoreTemplate(snapshot:any){if(snapshot){await choose(snapshot.id,snapshot);picker().value=snapshot.id;}else{await choose('');picker().value='';}}
export function drawComposition(video:HTMLVideoElement,crop:Area,canDraw:boolean,target?:HTMLCanvasElement){
 const canvas=target||$('#composition') as HTMLCanvasElement;if(!canvas||!current)return;
 canvas.width=540;canvas.height=960;const ctx=canvas.getContext('2d')!;ctx.scale(.5,.5);ctx.fillStyle='#080b10';ctx.fillRect(0,0,current.width,current.height);if(image&&current.layer==='front')ctx.drawImage(image,0,0,current.width,current.height);
 if(!valid()){if(image)ctx.drawImage(image,0,0,current.width,current.height);return;}const {x,y,slot_w:w,slot_h:h}=current;
 if(canDraw&&video.readyState>=2){
 ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();
 if(current.fit==='cover'){const scale=Math.max(w/crop.width,h/crop.height),sw=w/scale,sh=h/scale;ctx.drawImage(video,crop.x+(crop.width-sw)/2,crop.y+(crop.height-sh)/2,sw,sh,x,y,w,h);}
 else{ctx.fillStyle='#000';ctx.fillRect(x,y,w,h);const scale=Math.min(w/crop.width,h/crop.height),dw=crop.width*scale,dh=crop.height*scale;ctx.drawImage(video,crop.x,crop.y,crop.width,crop.height,x+(w-dw)/2,y+(h-dh)/2,dw,dh);}
 ctx.restore();}else{ctx.fillStyle='#c0ef6c44';ctx.fillRect(x,y,w,h);}
 if(image&&current.layer!=='front')ctx.drawImage(image,0,0,current.width,current.height);
}
function constrain(c:any){const even=(v:number)=>Math.floor(v/2)*2,clamp=(v:number,a:number,b:number)=>Math.max(a,Math.min(b,v));c.x=clamp(even(c.x),0,current.width-2);c.y=clamp(even(c.y),0,current.height-2);c.slot_w=clamp(even(c.slot_w),2,current.width-c.x);c.slot_h=clamp(even(c.slot_h),2,current.height-c.y);return c;}
export async function initializeTemplates(onChange:()=>void){redraw=onChange;
 picker().addEventListener('change',()=>{choose(picker().value);if(!picker().value)try{localStorage.removeItem('dark-active-template');}catch{}});
 $('#upload-template').addEventListener('submit',async e=>{e.preventDefault();const upload=$('#upload-template-button') as HTMLButtonElement;upload.disabled=true;info('Importando arte…');try{const form=new FormData($('#upload-template') as HTMLFormElement),r=await fetch('/api/templates',{method:'POST',body:form}),data=await r.json();if(!r.ok)throw Error(data.error);templates.unshift(data);list();picker().value=data.id;await choose(data.id);info('Arte importada. Ajuste o espaço do vídeo e salve o template.');($('#upload-template') as HTMLFormElement).reset();}catch(e){info(e.message,true);}finally{upload.disabled=false;}});
 for(const k of ['x','y','slot_w','slot_h'])field('#slot-'+k).addEventListener('input',()=>{if(!current)return;current[k]=field('#slot-'+k).value===''?NaN:Number(field('#slot-'+k).value);sync(false);});
 field('#template-name').addEventListener('input',()=>{if(current){current.name=field('#template-name').value;sync(false);}});
 $('#template-fit').addEventListener('change',()=>{if(current){current.fit=($('#template-fit') as HTMLSelectElement).value;sync(false);}});
 $('#template-layer').addEventListener('change',()=>{if(current){current.layer=($('#template-layer') as HTMLSelectElement).value;sync(false);}});
 $('#save-template').addEventListener('click',async()=>{if(!valid())return;try{const r=await fetch('/api/templates',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(templatePayload())}),data=await r.json();if(!r.ok)throw Error(data.error);current=data;templates=templates.map(t=>t.id===data.id?data:t);list();sync();info('Template salvo no computador. Ele pode ser aplicado nos próximos vídeos.');}catch(e){info(e.message,true);}});
 const overlay=$('#slot-overlay'),box=$('#slot-box');let drag:any=null;
 const point=(e:PointerEvent)=>{const r=overlay.getBoundingClientRect();return {x:Math.max(0,Math.min(current.width,(e.clientX-r.left)/r.width*current.width)),y:Math.max(0,Math.min(current.height,(e.clientY-r.top)/r.height*current.height))};};
 overlay.addEventListener('pointerdown',e=>{if(!loaded||e.button!==0||!valid())return;e.preventDefault();const target=e.target as HTMLElement;drag={id:e.pointerId,p:point(e),o:{...current},mode:target.dataset.corner||(box.contains(target)?'move':'draw')};overlay.setPointerCapture(e.pointerId);});
 overlay.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;const p=point(e),o=drag.o;let c={...o};if(drag.mode==='move'){c.x=Math.max(0,Math.min(current.width-o.slot_w,o.x+p.x-drag.p.x));c.y=Math.max(0,Math.min(current.height-o.slot_h,o.y+p.y-drag.p.y));}else{const ax=drag.mode==='draw'?drag.p.x:drag.mode.includes('w')?o.x+o.slot_w:o.x,ay=drag.mode==='draw'?drag.p.y:drag.mode.includes('n')?o.y+o.slot_h:o.y;c.x=Math.min(ax,p.x);c.y=Math.min(ay,p.y);c.slot_w=Math.abs(ax-p.x);c.slot_h=Math.abs(ay-p.y);}current=constrain(c);sync();});
 for(const name of ['pointerup','pointercancel'])overlay.addEventListener(name,()=>drag=null);
 box.addEventListener('keydown',e=>{if(!valid())return;const d=e.shiftKey?10:2,move={ArrowLeft:[-d,0],ArrowRight:[d,0],ArrowUp:[0,-d],ArrowDown:[0,d]}[e.key];if(!move)return;e.preventDefault();current=constrain({...current,x:Math.max(0,Math.min(current.width-current.slot_w,current.x+move[0])),y:Math.max(0,Math.min(current.height-current.slot_h,current.y+move[1]))});sync();});
 $('#composition-play').addEventListener('click',()=>($('#play') as HTMLButtonElement).click());
 $('#export-composition').addEventListener('click',()=>($('#crop-form') as HTMLFormElement).requestSubmit());
 try{const r=await fetch('/api/templates'),data=await r.json();if(!r.ok)throw Error(data.error);templates=data.templates;list();let previous='';try{previous=localStorage.getItem('dark-active-template')||'';}catch{}if(templates.some(t=>t.id===previous)){picker().value=previous;await choose(previous);}else sync();}catch(e){info(e.message,true);}
}
