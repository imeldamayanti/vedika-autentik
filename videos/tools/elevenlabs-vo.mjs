#!/usr/bin/env node
// Bikin semua suara narasi lewat ElevenLabs dari videos/tools/vo.json.
// Kunci API dibaca dari environment, tidak pernah ditulis ke file:
//   ELEVENLABS_API_KEY=...  ELEVENLABS_VOICE_ID=...  node videos/tools/elevenlabs-vo.mjs
// Opsional: ELEVENLABS_MODEL (default eleven_multilingual_v2), ONLY=o1,d3 untuk membuat ulang sebagian.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const key = process.env.ELEVENLABS_API_KEY;
const voice = process.env.ELEVENLABS_VOICE_ID;
const model = process.env.ELEVENLABS_MODEL || "eleven_multilingual_v2";
if (!key || !voice) {
  console.error("Isi ELEVENLABS_API_KEY dan ELEVENLABS_VOICE_ID dulu.");
  process.exit(1);
}

const vo = JSON.parse(readFileSync(join(here, "vo.json"), "utf8"));
const only = process.env.ONLY ? process.env.ONLY.split(",") : null;
const outDir = process.env.OUT_DIR || join(root, "demo/assets/vo");
mkdirSync(outDir, { recursive: true });
const durFile = join(here, "vo-durations.json");
const dur = JSON.parse(readFileSync(durFile, "utf8"));

for (const [id, text] of Object.entries(vo)) {
  if (only && !only.includes(id)) continue;
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}?output_format=mp3_44100_128`, {
    method: "POST",
    headers: { "xi-api-key": key, "content-type": "application/json" },
    body: JSON.stringify({
      text,
      model_id: model,
      ...(/v2_5|turbo|flash/.test(model) ? { language_code: "id" } : {}),
      voice_settings: { stability: +(process.env.STABILITY ?? 0.5), similarity_boost: 0.8, style: +(process.env.STYLE ?? 0.2), use_speaker_boost: true, speed: +(process.env.SPEED ?? 1.0) },
    }),
  });
  if (!res.ok) {
    console.error(id, res.status, (await res.text()).slice(0, 300));
    process.exit(1);
  }
  const mp3 = join(outDir, `${id}.mp3`);
  writeFileSync(mp3, Buffer.from(await res.arrayBuffer()));
  const wav = join(outDir, `${id}.wav`);
  execFileSync("ffmpeg", ["-v", "error", "-y", "-i", mp3, "-ar", "44100", "-ac", "1", wav]);
  dur[id] = +parseFloat(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]).toString()).toFixed(2);
  console.log(id, dur[id]);
}
writeFileSync(durFile, JSON.stringify(dur, null, 1));
console.log("Selesai. Jalankan: python3 videos/tools/build.py");
