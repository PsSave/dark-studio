import { getState } from '../../lib/collector.mjs';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { Readable } from 'node:stream';
export const GET = async ({url,request}) => {
 const {videos} = await getState();
 const video = videos.find(v=>v.id===url.searchParams.get('id') && v.status==='downloaded');
 if(!video) return new Response('Vídeo não encontrado',{status:404});
 const file = resolve('.data/media',video.filename);
 if(!file.startsWith(resolve('.data/media')+'/')) return new Response(null,{status:400});
 try {
 const {size} = await stat(file);
 const headers = {'Content-Type':'video/mp4','Accept-Ranges':'bytes','Cache-Control':'private, no-store'};
 if(url.searchParams.has('download')) headers['Content-Disposition'] = `attachment; filename="${video.id}.mp4"`;
 const range = request.headers.get('range');
 let start=0,end=size-1;
 if(range) {
 const m=/^bytes=(\d*)-(\d*)$/.exec(range);
 if(!m || (!m[1]&&!m[2])) return new Response(null,{status:416,headers:{'Content-Range':`bytes */${size}`}});
 if(!m[1]) start=Math.max(0,size-Number(m[2]));
 else {start=Number(m[1]);if(m[2]) end=Math.min(end,Number(m[2]));}
 if(start>end || start>=size) return new Response(null,{status:416,headers:{'Content-Range':`bytes */${size}`}});
 headers['Content-Range']=`bytes ${start}-${end}/${size}`;
 }
 headers['Content-Length']=String(end-start+1);
 return new Response(Readable.toWeb(createReadStream(file,{start,end})),{status:range?206:200,headers});
 }catch{return new Response('Arquivo indisponível. Retome a coleta.',{status:404});}
};
