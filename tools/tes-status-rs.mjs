// Tes logika status RS (audit S-01, S-02). Jalankan: node tools/tes-status-rs.mjs
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { fileURLToPath } from "node:url";

const src = readFileSync(fileURLToPath(new URL("../data-v3.js", import.meta.url)), "utf8");
const window = {};
runInNewContext(src, { window, console, URLSearchParams, location: { search: "" } });
const D = window.DATA3;

let gagal = 0;
function cek(nama, nyata, harapan) {
  const ok = nyata === harapan;
  if (!ok) gagal++;
  console.log((ok ? "lulus " : "GAGAL ") + nama + (ok ? "" : ` — dapat "${nyata}", harap "${harapan}"`));
}

const { belum, klarifikasi, normal } = D.STATUS_RS;
cek("0 jawaban → Belum cukup jawaban", D.statusRs({ terjawab: 0, tidak_sesuai: 0 }), belum);
cek("2 jawaban, 2 tidak sesuai → Belum cukup jawaban", D.statusRs({ terjawab: 2, tidak_sesuai: 2 }), belum);
cek("3 jawaban, 0 tidak sesuai → Normal", D.statusRs({ terjawab: 3, tidak_sesuai: 0 }), normal);
cek("3 jawaban, 3 tidak sesuai → Perlu klarifikasi RS", D.statusRs({ terjawab: 3, tidak_sesuai: 3 }), klarifikasi);
cek("4 jawaban, 2 tidak sesuai (RS Melati awal) → Normal", D.statusRs({ terjawab: 4, tidak_sesuai: 2 }), normal);
cek("40 jawaban, 3 tidak sesuai (7,5%) → Normal", D.statusRs({ terjawab: 40, tidak_sesuai: 3 }), normal);
cek("30 jawaban, 3 tidak sesuai (10%) → Perlu klarifikasi RS", D.statusRs({ terjawab: 30, tidak_sesuai: 3 }), klarifikasi);
cek("data kosong → Belum cukup jawaban", D.statusRs({}), belum);

cek("progres 0 jawaban", D.progresRs({ terjawab: 0, tidak_sesuai: 0 }), "0 dari 3 jawaban minimal");
cek("progres RS Melati awal", D.progresRs({ terjawab: 4, tidak_sesuai: 2 }), "2 dari 3 tidak sesuai untuk klarifikasi");
cek("progres sudah klarifikasi", D.progresRs({ terjawab: 5, tidak_sesuai: 3 }), "");

const awal = D.ringkasanRs(Object.values(D.LATAR));
cek("data demo: RS tanpa jawaban tidak ada yang Normal", awal.filter((c) => c.terjawab === 0 && c.status === normal).length, 0);
cek("uji mandiri data-v3.js bersih", D.UJI.length, 0);

console.log(gagal ? `\n${gagal} tes gagal` : "\nsemua tes lulus");
process.exit(gagal ? 1 : 0);
