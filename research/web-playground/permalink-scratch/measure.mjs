import fs from 'node:fs'; import path from 'node:path'; import zlib from 'node:zlib';
import LZ from 'lz-string'; import * as fflate from 'fflate';
const b64url=u8=>Buffer.from(u8).toString('base64url');
async function cs(fmt,u8){const s=new Blob([u8]).stream().pipeThrough(new CompressionStream(fmt));return new Uint8Array(await new Response(s).arrayBuffer());}
async function ds(fmt,u8){const s=new Blob([u8]).stream().pipeThrough(new DecompressionStream(fmt));return new Uint8Array(await new Response(s).arrayBuffer());}
// Dictionary = keys + enum values from the DSL schema, most-common last (deflate prefers recent).
const dict=new TextEncoder().encode(fs.readFileSync('dict.txt','utf8'));
const files=process.argv.slice(2);
console.log('file|raw|encodeURIComponent|b64url(raw)|CS deflate-raw+b64url|CS deflate(zlib)+b64url|CS gzip+b64url|fflate lvl9 raw+b64url|fflate raw+dict+b64url|brotli q11+b64url|lz-string URI|ratio(CS raw)');
for(const f of files){const txt=fs.readFileSync(f,'utf8');const u8=new TextEncoder().encode(txt);
 const dr=await cs('deflate-raw',u8);const dz=await cs('deflate',u8);const gz=await cs('gzip',u8);
 const back=new TextDecoder().decode(await ds('deflate-raw',dr)); if(back!==txt) throw 'roundtrip';
 const ff=fflate.deflateSync(u8,{level:9});const ffd=fflate.deflateSync(u8,{level:9,dictionary:dict});
 if(new TextDecoder().decode(fflate.inflateSync(ffd,{dictionary:dict}))!==txt) throw 'dict rt';
 const br=zlib.brotliCompressSync(u8,{params:{[zlib.constants.BROTLI_PARAM_QUALITY]:11}});
 const lz=LZ.compressToEncodedURIComponent(txt); if(LZ.decompressFromEncodedURIComponent(lz)!==txt) throw 'lz rt';
 const row=[path.basename(f),u8.length,encodeURIComponent(txt).length,b64url(u8).length,b64url(dr).length,b64url(dz).length,b64url(gz).length,b64url(ff).length,b64url(ffd).length,b64url(br).length,lz.length,(u8.length/b64url(dr).length).toFixed(2)+'x'];
 console.log(row.join('|'));}
