import {spawn} from 'node:child_process';
import {resolve} from 'node:path';
import {existsSync} from 'node:fs';
export function editor(command,argument,payload) {
 const python=process.env.COLLECTOR_PYTHON||(existsSync('.venv/bin/python')?resolve('.venv/bin/python'):'python3');
 return new Promise((done,reject)=>{
  const args=[resolve('scripts/editor.py'),command];if(argument)args.push(argument);
  const child=spawn(python,args,{stdio:['pipe','pipe','ignore']});let output='';
  const timer=setTimeout(()=>{child.kill();reject(new Error('O processamento demorou além do esperado.'));},30000);
  child.stdout.on('data',chunk=>{output+=chunk;if(output.length>8*1024*1024){child.kill();}});
  child.stdin.on('error',()=>{});child.stdin.end(payload?JSON.stringify(payload):'');
  child.once('error',()=>{clearTimeout(timer);reject(new Error('Não foi possível iniciar o editor local.'));});
  child.once('close',code=>{clearTimeout(timer);try{const data=JSON.parse(output);if(code!==0)throw new Error(data.error||'Não foi possível processar o recorte.');done(data);}catch(e){reject(e);}});
 });
}
