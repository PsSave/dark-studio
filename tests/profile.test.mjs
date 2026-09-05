import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeProfile} from '../src/lib/profile.mjs';
test('normaliza usuário e link de perfil',()=>{assert.equal(normalizeProfile(' @Meu.Perfil '),'meu.perfil');assert.equal(normalizeProfile('https://www.instagram.com/meu.perfil/?hl=pt'),'meu.perfil');});
test('rejeita comandos, outro domínio e links de publicação',()=>{for(const value of ['x;touch /tmp/a','https://evil.com/user','https://instagram.com/p/123','../../file','https://instagram.com:99/user',null,''])assert.throws(()=>normalizeProfile(value));});
