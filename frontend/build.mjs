import {mkdir,copyFile,writeFile} from 'node:fs/promises';
await mkdir('dist/assets',{recursive:true});
await copyFile('index.html','dist/index.html');
for(const file of ['style.css','app.js']) await copyFile(file,'dist/assets/'+file);
const base=process.env.API_BASE_URL || '';
if(base && !/^https?:\/\//.test(base)) throw Error('API_BASE_URL must start with https:// or http://');
await writeFile('dist/assets/config.js','window.APP_CONFIG = '+JSON.stringify({API_BASE_URL:base})+';\n');
