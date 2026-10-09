// Renderiza reels (MP4) e stories (MP4 animado + PNG do quadro final) com Remotion.
// Uso: node render.mjs <pauta.json> <pasta_saida> <pasta_fotos> [pasta_capas]
//   pauta.json: { "reels": [{ "post_id": 1, "scenes": [...] }], "stories": [...] }
//   As fotos sao referenciadas pelo nome do arquivo (ex: "masp.jpg"); as capas dos stories "Post novo" por "card": "post_01/slide_01.jpg".
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const [pautaPath, outDir, fotosDir, capasDir] = process.argv.slice(2);
if (!pautaPath || !outDir || !fotosDir) {
  console.error("uso: node render.mjs pauta.json pasta_saida pasta_fotos [pasta_capas]");
  process.exit(1);
}
const pauta = JSON.parse(fs.readFileSync(pautaPath, "utf8"));

// copia fotos e capas para public/ (o Remotion so serve arquivos de la)
const pub = path.join(here, "public");
for (const [src, name] of [[fotosDir, "fotos"], [capasDir, "capas"]]) {
  const dst = path.join(pub, name);
  fs.rmSync(dst, { recursive: true, force: true });
  if (src && fs.existsSync(src)) fs.cpSync(src, dst, { recursive: true });
}
const fixPhoto = (p) => (p ? { ...p, src: p.src.includes("/") ? p.src : `fotos/${p.src}` } : p);

// navegador: usa o Chromium headless do ambiente se existir; senao o Remotion baixa o dele
let browserExecutable = process.env.REMOTION_CHROME || null;
if (!browserExecutable && fs.existsSync("/opt/pw-browsers")) {
  for (const d of fs.readdirSync("/opt/pw-browsers")) {
    const c = path.join("/opt/pw-browsers", d, "chrome-linux", "headless_shell");
    if (d.startsWith("chromium_headless_shell") && fs.existsSync(c)) browserExecutable = c;
  }
}

fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.join(here, "src", "index.jsx") });
const common = { serveUrl, browserExecutable, chromiumOptions: { gl: "swangle" } };

for (const [i, reel] of (pauta.reels || []).entries()) {
  const scenes = reel.scenes.map((s) => ({ ...s, photo: fixPhoto(s.photo) }));
  const inputProps = { scenes };
  const composition = await selectComposition({ ...common, id: "Reel", inputProps });
  const out = path.join(outDir, `reel_${String(reel.post_id ?? i + 1).padStart(2, "0")}.mp4`);
  await renderMedia({ ...common, composition, inputProps, codec: "h264", outputLocation: out, muted: true, crf: 18 });
  console.log("reel", out);
}

const storyDir = path.join(outDir, "stories");
fs.mkdirSync(storyDir, { recursive: true });
for (const [i, st] of (pauta.stories || []).entries()) {
  const inputProps = { ...st, photo: fixPhoto(st.photo), card: st.card ? `capas/${st.card}` : undefined };
  const composition = await selectComposition({ ...common, id: "Story", inputProps });
  const base = path.join(storyDir, `story_${String(i + 1).padStart(2, "0")}`);
  await renderMedia({ ...common, composition, inputProps, codec: "h264", outputLocation: `${base}.mp4`, muted: true, crf: 18 });
  await renderStill({ ...common, composition, inputProps, output: `${base}.png`, frame: composition.durationInFrames - 1 });
  console.log("story", base);
}
