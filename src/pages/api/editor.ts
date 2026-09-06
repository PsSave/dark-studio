import {editor} from '../../lib/editor.mjs';
export const GET=async ({url})=>{
 try{return Response.json(await editor(url.searchParams.has('source')?'source':'state',url.searchParams.get('source')),{headers:{'Cache-Control':'no-store'}});}
 catch(e){return Response.json({error:e.message||'Não foi possível abrir o editor.'},{status:400});}
};
export const POST=async ({request,url})=>{
 if(request.headers.get('origin')!==url.origin)return new Response(null,{status:403});
 try{return Response.json(await editor('create',undefined,await request.json()),{status:202});}
 catch(e){return Response.json({error:e.message||'Não foi possível exportar o recorte.'},{status:400});}
};
