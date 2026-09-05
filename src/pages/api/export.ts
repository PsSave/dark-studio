import { getState } from '../../lib/collector.mjs';
import { spawn } from 'node:child_process';
import { existsSync,createReadStream } from 'node:fs';
import { mkdtemp,rm,stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve,join } from 'node:path';
import { Readable } from 'node:stream';
export const GET = async () => {
 let folder:string|undefined;
 try {
 const {videos}=await getState();
 const files=videos.filter(v=>v.status==='downloaded').map(v=>v.filename);
 if(!files.length)return new Response('Nenhum vídeo disponível para exportar.',{status:409});
 folder=await mkdtemp(join(tmpdir(),'dark-export-'));
 const output=join(folder,'dark-studio-videos.zip');
 const python=process.env.COLLECTOR_PYTHON || (existsSync('.venv/bin/python')?resolve('.venv/bin/python'):'python3');
 await new Promise<void>((done,reject)=>{
  const child=spawn(python,[resolve('scripts/export_zip.py'),output],{stdio:['pipe','ignore','ignore']});
  const timer=setTimeout(()=>{child.kill();reject(new Error('Tempo excedido'));},120000);
  child.once('error',e=>{clearTimeout(timer);reject(e);});
  child.once('close',code=>{clearTimeout(timer);code===0?done():reject(new Error('Falha ao criar pacote'));});
  child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify(files));
 });
 const info=await stat(output), stream=createReadStream(output), cleanup=folder;
 stream.once('close',()=>{void rm(cleanup,{recursive:true,force:true});});
 return new Response(Readable.toWeb(stream) as ReadableStream,{headers:{'Content-Type':'application/zip','Content-Disposition':'attachment; filename="dark-studio-videos.zip"','Content-Length':String(info.size),'Cache-Control':'no-store'}});
 }catch{
 if(folder)await rm(folder,{recursive:true,force:true});
 return new Response('Não foi possível preparar o ZIP. Confira se os arquivos continuam no acervo e tente novamente.',{status:500});
 }
};
