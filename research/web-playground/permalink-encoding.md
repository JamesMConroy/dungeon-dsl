# Permalink encoding

Research for [issue 08](https://github.com/JamesMConroy/dungeon-dsl/issues/9). Researched 2026-11-05.

## TL;DR

`https://<pages-host>/<repo>/#1.<base64url(deflate-raw(utf8(yaml)))>`

- **Fragment, not query.** Fragments never reach the server or the `Referer`, so there's no server-side URL cap to hit and no YAML in GH Pages/CDN logs.
- **Native `CompressionStream('deflate-raw')`**, no library. Baseline since Safari 16.4 / Firefox 113 / Chrome 103.
- **Version in plaintext before the payload** (`1.`), so the decoder can dispatch on it before decompressing anything.
- **The real limit is chat apps, not browsers.** Discord's API caps a message at 2,000 chars, and Slack splits text around 4,000 chars. Browsers allow 1–2 MB. Show the link length, warn past ~2,000 chars, and always offer "Download YAML". Don't hard-block below browser limits.
- **Cap decompressed size on decode.** A hostile 136 KB fragment inflates to 100 MB (measured).

## 1. Length limits

### Browsers (primary sources)

| Browser | Limit | Source | Confidence |
|---|---|---|---|
| Chrome / Chromium (Edge too) | **2 MB** (`kMaxURLChars = 2 * 1024 * 1024`). "Chrome limits URLs to a maximum length of 2MB for practical reasons and to avoid causing denial-of-service problems in inter-process communication." | [`url/url_constants.h`](https://chromium.googlesource.com/chromium/src/+/main/url/url_constants.h), [URL display guidelines](https://chromium.googlesource.com/chromium/src/+/main/docs/security/url_display_guidelines/url_display_guidelines.md) | High (source code) |
| Firefox | **1 MB** for http(s) URLs (`network.standard-url.max-length = 1048576`). There's also a generic `network.url.max-length = 512 MB`. | [`StaticPrefList.yaml`](https://github.com/mozilla-firefox/firefox/blob/main/modules/libpref/init/StaticPrefList.yaml) | High (source code) |
| Safari / WebKit | No documented limit found. Community reports put it well above Chrome's, in the multi-MB range. | none primary | **Low.** Not verified. One manual test in Safari with a ~100 KB fragment would settle it for our purposes. |

The whole URL counts against these limits, including the fragment. Both are about 3 orders of magnitude above anything a sane Dungeon produces, so browsers aren't the binding constraint.

### Fragment vs. query string

- The fragment isn't sent in the HTTP request ([RFC 3986 §3.5](https://www.rfc-editor.org/rfc/rfc3986#section-3.5): the fragment is resolved client-side). The Fetch spec strips it from `Referer` ([Fetch: strip url for use as a referrer](https://fetch.spec.whatwg.org/#strip-url)). So the YAML never shows up in GH Pages/Fastly access logs or in third-party referrers.
- A query string *does* hit the server. [RFC 9110 §4.1](https://www.rfc-editor.org/rfc/rfc9110#section-4.1) only *recommends* supporting ≥8,000 octets, and GitHub Pages' actual request-line cap is undocumented (I found no primary source). It's an unknown limit we gain nothing by testing.
- Because the page is static, nothing server-side needs the YAML. **Use the fragment.**
- Link unfurlers (Slack, Discord, iMessage) fetch the URL server-side without the fragment, so every Permalink previews as the generic Playground page. That's harmless, and arguably fine: previews don't leak dungeon contents.

### Chat apps and other paste targets

| Target | Limit | Source | Confidence |
|---|---|---|---|
| Discord | Message content "up to 2000 characters" (API). Nitro users can send more (commonly cited as 4,000). | [Discord API: Message resource](https://discord.com/developers/docs/resources/message) | High for 2,000. The Nitro number is unverified (support article was behind a bot wall). |
| Slack | "For best results, limit the text field to 4,000 characters… Messages with longer text may be split into multiple messages of up to about 4,000 characters each. Slack will truncate messages containing more than 40,000 characters." | [chat.postMessage docs](https://docs.slack.dev/reference/methods/chat.postMessage) | Medium. This is the API doc. Composer behaviour in the client is undocumented, but a URL split at a message boundary is broken, so treat **~4,000** as the budget. |
| Microsoft Teams | ~100 KB per chat/channel post (80 KB recommended). | [Teams limits](https://learn.microsoft.com/en-us/microsoftteams/limits-specifications-teams) | High |
| iMessage / SMS | Undocumented. iMessage handles long links in practice. SMS fallback (green bubble) segments long messages, and some carriers/clients mangle them. | none | Low |
| Email | RFC 5322 caps lines at 998 chars, so clients wrap or quoted-printable-encode long URLs. Usually transparent, sometimes breaks plain-text copy. | [RFC 5322 §2.1.1](https://www.rfc-editor.org/rfc/rfc5322#section-2.1.1) | Medium |

**Budgets for the UI:** ≤2,000 chars works everywhere. 2,000–4,000 breaks Discord. Above ~4,000, Slack is risky. Above ~100 KB, only browsers will take it.

Linkifiers trim trailing punctuation like `.`, `)` and `?`. The base64url alphabet (`A-Z a-z 0-9 - _`, no `=` padding) contains none of them, so this isn't an issue. Don't append anything after the payload.

## 2. Compression

### Measured ratios

Script: [`permalink-scratch/measure.mjs`](permalink-scratch/measure.mjs) (Node 26.12, which uses the same `CompressionStream` API surface as browsers; Node's backend is zlib, as is Chromium's). Each figure is the **number of URL chars for the payload**, excluding origin and prefix.

| Input | Raw bytes | `encodeURIComponent` | b64url(raw) | **CS deflate-raw + b64url** | CS deflate (zlib) | CS gzip | fflate raw + preset dict | brotli q11 | lz-string `compressToEncodedURIComponent` |
|---|---|---|---|---|---|---|---|---|---|
| collision_test | 581 | 1123 | 775 | **256** | 264 | 280 | 208 | 243 | 391 |
| size_test | 1309 | 2261 | 1746 | **586** | 594 | 610 | 515 | 539 | 903 |
| diagonal_test | 1440 | 2560 | 1920 | **596** | 604 | 620 | 548 | 528 | 929 |
| **goblin_warren** | **1855** | 3331 | 2474 | **735** | 743 | 759 | 588 | 644 | 1204 |
| all 4 examples concat | 5185 | 9275 | 6914 | **1758** | 1766 | 1782 | 1647 | 1550 | 2796 |
| prose_25 (unique random prose) | 12008 | 20510 | 16011 | **4096** | 4104 | 4120 | 4070 | 3492 | 6148 |
| prose_100 | 48668 | 83272 | 64891 | **13911** | 13919 | 13935 | 14164 | 11780 | 20049 |
| synth_25 (repetitive vocab) | 10332 | 19282 | 13776 | **1132** | | | 970 | 931 | 3517 |
| synth_100 | 40753 | 76057 | 54338 | **3139** | | | 2920 | 2419 | 9504 |

The `synth_*` files use a 12-adjective/8-sentence vocabulary, which is unrealistically compressible. The `prose_*` files use random words from a 2,000-word pool, which is pessimistic (real English compresses better). Real authored Dungeons sit between the two and close to the examples, so plan on roughly **2.5–3× bytes→URL chars**.

Takeaways:
- goblin_warren becomes a **735-char payload**, about 790 chars as a full URL. It fits anywhere.
- At ~3×, the 2,000-char Discord budget covers about **5–6 KB of YAML** (≈3× goblin_warren, or 12–15 rooms with authored prose). The 4,000-char Slack budget covers about **11–12 KB**.
- `deflate` (zlib) and `gzip` only add 8/24 bytes of header and checksum to `deflate-raw`. The checksum is pointless here because a corrupt link fails YAML parsing anyway. `deflate-raw` is strictly smaller.
- **lz-string is 1.6× worse** than deflate-raw on goblin_warren (1,204 vs 735), and 2–3× worse on larger inputs. Its only advantages are a sync API and no base64 step. Reject it.
- **A preset dictionary** (zlib `FDICT`: ~30 lines of DSL keys and enum values, [`dict.txt`](permalink-scratch/dict.txt)) saves **15–20% on small files** (goblin 735→588). The gain fades with size, and a vocabulary-blind dictionary is noise on prose-heavy input. `CompressionStream` has no dictionary option, so it needs fflate (~8 KB min+gz) or pako, and the dictionary is frozen forever per format version. It's a good candidate for a future `2.` format, not v1.
- **Brotli** saves 10–25% on larger inputs, but per MDN BCD (v8.1.8, 2026-11-02) `CompressionStream('brotli')` ships in Firefox 147 and Safari 18.4 and **not in Chrome**. It would need a wasm decoder. Not worth it.

### Browser support (MDN browser-compat-data v8.1.8, pulled 2026-11-02)

| Feature | Chrome/Edge | Firefox | Safari (macOS/iOS) |
|---|---|---|---|
| `CompressionStream` / `DecompressionStream` | 80 | 113 | 16.4 |
| `'deflate-raw'` format | **103** | 113 | 16.4 |
| `'brotli'` | ✗ | 147 | 18.4 |
| `'zstd'` | ✗ | 138 (experimental) | ✗ |
| `Uint8Array.prototype.toBase64` / `Uint8Array.fromBase64` (with `{alphabet:'base64url', omitPadding:true}`) | 140 | 133 | 18.2 |

Source: [MDN CompressionStream](https://developer.mozilla.org/en-US/docs/Web/API/CompressionStream/CompressionStream) and [BCD raw data](https://unpkg.com/@mdn/browser-compat-data/data.json).

`deflate-raw` has been Baseline since Safari 16.4 (March 2023), well below what Pyodide (WebAssembly + modern JS) already demands. `toBase64` only reached Chrome in 140 (Sept 2025). Either accept that floor, or use a ~10-line `btoa`/`atob` helper with `+/`→`-_` and the padding stripped. **Use the helper.** It costs nothing, and the floor stays at "whatever Pyodide needs".

Determinism: deflate output can differ between implementations and versions. Safari doesn't use Chromium's zlib, though I have no primary source for which backend it does use. The same YAML may therefore produce different Permalinks in different browsers. Every encoder decodes every other's output (deflate is a spec, [RFC 1951](https://www.rfc-editor.org/rfc/rfc1951)), but **never use the encoded string as an identity or cache key.**

## 3. Versioning

Format: `#<version>.<payload>`

- `1.` = `base64url_nopad(deflate_raw(utf8(yaml_source_text)))`.
- Keep the version as plaintext ASCII in front of the payload, not as a byte inside the compressed stream. The decoder can then dispatch before touching `DecompressionStream`, a human can read it, and a future format (`2.` with a preset dict, brotli, etc.) is a new branch. It never has to reinterpret old bytes.
- The decoder keeps every past version forever. The encoder emits only the latest version.
- `.` isn't in the base64url alphabet, so the split is unambiguous. A missing version or an unknown version gets an error ("This link was made by a newer/older Playground") and no attempt to decode.
- Optionally reserve a plain mode such as `#0.<encodeURIComponent(yaml)>` for hand-crafted links in docs/READMEs. It's cheap and human-editable.
- Encode the YAML **text verbatim** (comments, ordering, whitespace) and don't round-trip it through the parser. Line-anchored errors (issue 05) and the editor need the user's exact text, and normalizing would only save a few percent after compression.
- If more fields are ever needed (e.g. a selected room or view state), use `#1.<payload>&room=entrance`, i.e. parse the remainder after the payload as `URLSearchParams`. Don't burn a format version on it.

## 4. Past the limit

No browser limit is reachable in practice. A 1 MB Firefox URL is ~3 MB of YAML, far beyond what the Pyodide render loop would tolerate (see the map's "Scale limits"). So the policy is UX, not a hard cap:

1. Always generate the Permalink, and show its length next to the copy button.
2. Above **2,000** chars, show a soft warning: "too long for Discord". Above **4,000**: "may break in Slack/chat; consider Download YAML".
3. **"Download YAML"** is always available, not only as a fallback. It's the lossless path, and it overlaps with the map's "Export" item.
4. Hard-refuse to encode only above ~1 MB (the Firefox cap), with the Download YAML path offered instead. This is defensive and should never trigger in practice.

### Decode safety (don't skip)

A Permalink is untrusted input. Deflate's maximum ratio is ~1032:1. Measured with [`permalink-scratch/bomb.mjs`](permalink-scratch/bomb.mjs):

- 1 MB of spaces → a **1,379-char** fragment.
- 100 MB → a **136K-char** fragment, which is under both browser caps.

Decode through a streaming reader and **abort once output exceeds a cap** (e.g. 1 MB, comfortably above any real Dungeon) before handing the text to the editor or Pyodide. `new Response(stream).text()` without a cap is a tab-killer.

## Sketch

```ts
const MAX_YAML = 1 << 20;
const b64u = (u8: Uint8Array) => btoa(String.fromCharCode(...u8)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
// for large inputs, chunk String.fromCharCode to avoid arg-count limits
async function encode(yaml: string) {
  const s = new Blob([yaml]).stream().pipeThrough(new CompressionStream('deflate-raw'));
  return '1.' + b64u(new Uint8Array(await new Response(s).arrayBuffer()));
}
async function decode(hash: string) {
  const [v, payload] = [hash.slice(0, hash.indexOf('.')), hash.slice(hash.indexOf('.') + 1)];
  if (v !== '1') throw new UnknownVersion(v);
  const bytes = Uint8Array.from(atob(payload.replace(/-/g,'+').replace(/_/g,'/')), c => c.charCodeAt(0));
  const r = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw')).getReader();
  const chunks: Uint8Array[] = []; let n = 0;
  for (;;) { const { done, value } = await r.read(); if (done) break;
    if ((n += value.length) > MAX_YAML) { await r.cancel(); throw new TooLarge(); } chunks.push(value); }
  return new TextDecoder('utf-8', { fatal: true }).decode(await new Blob(chunks).arrayBuffer());
}
```

Wire-up notes: update the hash with `history.replaceState` (debounced) so editing doesn't flood the back stack, and listen to `hashchange` for pasted links into an open tab.

## Confidence and gaps

- **High:** Chrome and Firefox limits (source code), API support (BCD), compression ratios (measured locally and round-trip verified), fragment privacy (RFCs/Fetch spec).
- **Medium:** Slack budget. The API docs say "split ~4,000 / truncate 40,000", but client composer behaviour is undocumented.
- **Low / unverified:** Safari URL cap, Discord Nitro limit, iMessage/SMS behaviour, and Safari's deflate backend. None of them change the recommendation. A 5-minute manual paste test (Safari, iMessage, Slack, Discord) with a ~3,000- and a ~10,000-char link would close them out.
- The ratios come from Node's zlib. Browser encoders may differ by a few percent, but decoders are interoperable.
