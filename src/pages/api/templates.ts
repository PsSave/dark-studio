import {editor} from '../../lib/editor.mjs';
import {mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {resolve} from 'node:path';
import {randomUUID} from 'node:crypto';
export const GET=async({url})=>{
 try{const data=await editor('templates');const id=url.searchParams.get('asset');if(!id)return Response.json(data,{headers:{'Cache-Control':'no-store'}});
 const template=data.templates.find(t=>t.id===id);if(!template)return new Response(null,{status:404});
 const base=resolve('.data/templates'),path=resolve(base,template.filename);if(!path.startsWith(base+'/'))return new Response(null,{status:400});
 return new Response(await readFile(path),{headers:{'Content-Type':'image/png','Cache-Control':'private, max-age=3600'}});
 }catch{return Response.json({error:'Não foi possível abrir os templates.'},{status:400});}
};
export const POST=async({request,url})=>{
 if(request.headers.get('origin')!==url.origin)return new Response(null,{status:403});
 let path;
 try{
 if(Number(request.headers.get('content-length'))>21*1024*1024)return Response.json({error:'Use uma imagem de até 20 MB.'},{status:413});
 const form=await request.formData(),file=form.get('image');
 if(!(file instanceof File)||file.size>20*1024*1024||!file.size)return Response.json({error:'Envie uma imagem de até 20 MB.'},{status:400});
 const token=randomUUID().replaceAll('-','');await mkdir(resolve('.data/template-inbox'),{recursive:true});path=resolve('.data/template-inbox',token);await writeFile(path,Buffer.from(await file.arrayBuffer()));
 return Response.json(await editor('template-upload',undefined,{token,name:form.get('name')||file.name.replace(/\.[^.]+$/,'').slice(0,100)}),{status:201});
 }catch(e){return Response.json({error:e.message||'Não foi possível importar a arte.'},{status:400});}
 finally{if(path)await rm(path,{force:true});}
};
export const PATCH=async({request,url})=>{
 if(request.headers.get('origin')!==url.origin)return new Response(null,{status:403});
 try{return Response.json(await editor('template-save',undefined,await request.json()));}catch(e){return Response.json({error:e.message||'Não foi possível salvar o template.'},{status:400});}
};
