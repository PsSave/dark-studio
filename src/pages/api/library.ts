import {getState,startScan} from '../../lib/collector.mjs';
import {normalizeProfile} from '../../lib/profile.mjs';
export const GET = async () => {
 try { return Response.json(await getState(),{headers:{'Cache-Control':'no-store'}}); }
 catch {return Response.json({error:'Não foi possível ler a biblioteca local.'},{status:500});}
};
export const POST = async ({request,url}) => {
 if(request.headers.get('origin') !== url.origin) return new Response('Origem não permitida',{status:403});
 try {
 const body = await request.json();
 const profile = normalizeProfile(body.profile);
 const limit = body.limit ?? 10;
 if(![0,5,10,25,50].includes(limit)) return Response.json({error:'Limite inválido.'},{status:400});
 const state = await getState();
 if(state.jobs.some(j=>['scanning','downloading'].includes(j.status))) return Response.json({error:'Uma coleta já está em andamento.'},{status:409});
 await startScan(profile,limit);
 return Response.json({profile},{status:202});
 } catch(error) {return Response.json({error:error instanceof Error ? error.message : 'Não foi possível iniciar.'},{status:400});}
};
