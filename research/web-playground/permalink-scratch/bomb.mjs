// How big can a hostile fragment inflate? 1 MB of zeros / 100 MB of spaces.
import zlib from 'node:zlib';
for (const n of [1<<20, 100<<20]) { const c = zlib.deflateRawSync(Buffer.alloc(n, 0x20), {level:9}); console.log(n, '->', Buffer.from(c).toString('base64url').length, 'b64url chars'); }
