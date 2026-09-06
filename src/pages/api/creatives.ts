import {editor} from '../../lib/editor.mjs';
export const GET=async()=>{try{return Response.json(await editor('batch-state'),{headers:{'Cache-Control':'no-store'}});}catch{return Response.json({error:'Não foi possível carregar os criativos.'},{status:500});}};
export const POST=async({request,url})=>{
 if(request.headers.get('origin')!==url.origin)return new Response(null,{status:403});
 try{const payload=await request.json(),action=payload.action||'create';if(!['create','retry','approve'].includes(action))throw Error('Ação inválida.');return Response.json(await editor('batch-'+action,undefined,payload),{status:action==='create'?202:200});}catch(e){return Response.json({error:e.message||'Não foi possível processar o lote.'},{status:400});}
};
