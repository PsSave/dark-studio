import {execFile, spawn} from 'node:child_process';
import {promisify} from 'node:util';
import {resolve} from 'node:path';
import {existsSync} from 'node:fs';
const exec = promisify(execFile);
const script = resolve('scripts/collector.py');
const python = process.env.COLLECTOR_PYTHON || (existsSync('.venv/bin/python') ? resolve('.venv/bin/python') : 'python3');
export async function getState() {
 const {stdout} = await exec(python,[script,'state'],{maxBuffer:32*1024*1024,timeout:15000});
 return JSON.parse(stdout);
}
export function startScan(profile, limit=10) {
 const child = spawn(python,[resolve('scripts/browser_collector.py'),profile,String(limit)],{stdio:'ignore',detached:true,env:{...process.env,PLAYWRIGHT_BROWSERS_PATH:resolve('.data/browsers')}});
 return new Promise((resolve,reject)=>{child.once('error',reject);child.once('spawn',()=>{child.unref();resolve();});});
}
