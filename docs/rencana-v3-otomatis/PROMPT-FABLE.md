# Task: automatic patient calls from an Android line station (Vedika Autentik v3)

You are working in the `vedika-autentik` repo (the current directory). Build this whole feature in one go, end to end, without stopping to ask questions. Where this spec leaves a detail open, pick the simplest option that satisfies it and list that choice in your final report. Stop early only if something blocks all progress (for example, dependencies won't install).

This file is the authoritative spec. The two HTML files next to it are visual references. If they disagree with this file, follow this file.

## 0. Read first

1. `docs/rencana-v3-otomatis/rencana.html`: the plan (architecture, call simulator, tickets, hardware, risks). Open it in a browser.
2. `docs/rencana-v3-otomatis/prototipe-petugas.html`: the officer experience to reach. Its Indonesian copy and status-strip states are the target for the website.
3. `docs/prd-v3-konfirmasi-suara.md`: requirements R1–R5, the label table, and Lampiran B (WA text).
4. `docs/api-contract-v3.md`: Kontrak A (website ↔ API), B1 (agent ↔ API), B2 (API ↔ answer reader).
5. `docs/serah-terima-zahra.md`, `backend/README.md`, `ai-service/README.md`.
6. Every code file named below, before you edit it.

## 1. What exists today

- **Website** (`index.html` → `app-v3.js`, `api-v3.js`, `data-v3.js`, `app-v3.css`). Vanilla JS, hash routes, polls the API every second. Falls back to a hand-written simulation (`data-v3.js`) when the API is unhealthy.
- **Backend** (`backend/`, FastAPI + Supabase Postgres). Owns the queue, working hours, WA delay, retries, labels (`data-uji-konfirmasi/tools/aturan.py` via `app/aturan_v3.py`), retention and RS summary.
  - Agent logic: `app/agen.py`, `app/router_agen.py`. Website endpoints: `app/router_v3.py`, `app/tampilan_v3.py`. Data access: `app/repo_v3.py`.
  - The `pengaturan` table is key/value jsonb (`repo_v3.ambil_pengaturan` / `simpan_pengaturan`).
  - Demo reset: `scripts/seed_v3.reset_panggilan`, called by `POST /api/v1/demo/reset`.
- **ai-service** (`ai-service/`, FastAPI, uv). Serves the following; a Cloudflare Worker copy in `ai-service/worker/` serves the same.
  - `/v1/baca`: answer reader on Gemini text.
  - `/v1/suara/token`: Gemini Live credential.
  - The agent page `/voice/`: `web/voice-console.html` + `web/voice-agent.mjs`.
- **Agent page.** It polls `POST /api/v1/agen/ambil` every 3 s and runs Gemini Live in Chrome. It currently needs a human operator for each step:
  - type the backend URL and keys, and pick BlackHole devices;
  - open a wa.me link and press send in WhatsApp Web, then dial in WhatsApp Web;
  - click "Saya menelepon", and send the fallback chat by hand.

  Answer detection uses the recipient's first transcribed words. `runTask` in `voice-agent.mjs` drives Kontrak B1.
- **Stubs:**
  - `backend/stub_mesin` (fake reader);
  - `backend/scripts/stub_agen.py` (fake agent that replays scripted calls);
  - `ai-service/scripts/agent_e2e.mjs` (real Chrome + BlackHole + Gemini Live with a robot recipient).
- **One-command dev:** `./dev.sh` starts ai-service :8001, backend :8000 and website :8899. Supabase must be reachable; ports 5432/6543 are blocked on some networks, so use a phone hotspot there.

## 2. Final decisions (do not revisit)

1. **The phone line is an Android phone with an Indonesian SIM**, controlled over ADB by a local Phone helper on the station laptop. No Twilio or other CPaaS, no WhatsApp calling, no iPhone.
2. **WhatsApp carries messages only:** the pre-call notice (Lampiran B) and the fallback chat. The backend sends both through the **Meta WhatsApp Cloud API** directly.
3. **Calls are automatic and sequential.** Keep the existing one-active-call rule. "Panggilan otomatis" is **on by default**. "Telepon sekarang" becomes **"Dahulukan"**, which moves a patient to the front.
4. **Officers use only the website.** The agent page runs only on the station laptop, starts by itself, and needs no typing.
5. **The first acceptance target is local:** the whole stack on the station laptop. Running against the deployed Vercel backend is an optional final ticket (4.7).
6. **Two audio modes, chosen by env.**
   - `speaker` (default): the phone on speakerphone beside the laptop, default laptop mic and speakers, Chrome echo cancellation, noise suppression and auto-gain on.
   - `kabel`: USB audio interface + TRRS splitter, processing off as today.
7. **No database schema changes.** The station heartbeat lives in the existing `pengaturan` key/value table.
8. **Keep working:** the stubs, the website's simulation fallback, and v2 (do not touch `v2.html`, `app.js`, `data.js`, `api.js`).

## 3. Runtime topology (local)

```
Officer browser ──► website :8899 ──► backend :8000 ──► Supabase
                                         │  ├──► answer reader (MESIN_URL, ai-service :8001 or stub_mesin)
                                         │  └──► Meta Graph API (WA notice, fallback chat)
Station laptop:  Chrome app window ── /voice/ agent page (ai-service :8001, SALURAN_ADB=1)
                     │  ├──► backend :8000 (Kontrak B1: detak, ambil, status, transkrip, hasil)
                     │  ├──► /v1/suara/token → Gemini Live (audio in/out)
                     │  └──► /v1/saluran/* Phone helper ──adb──► Android phone ──cellular──► tester phone
```

## 4. Specification

### 4.1 Backend (`backend/`)

**a) WhatsApp sender: new `app/wa.py`**

- Main function: `kirim(nomor, jenis, teks, parameter) -> dict`.
  - `jenis` is `"pemberitahuan"` or `"cadangan"`.
  - Returns `{"status": "terkirim" | "simulasi" | "gagal", "pesan": str | None}`. `pesan` never contains a phone number.
- The mode comes from `META_WA_MODE`. If `META_WA_TOKEN` or `META_WA_PHONE_ID` is empty, the mode is always `log`.
  - `log`: no network call; return `simulasi` and write one log line without the number.
  - `teks`: `POST https://graph.facebook.com/{META_WA_API_VERSION}/{META_WA_PHONE_ID}/messages` with `{"messaging_product": "whatsapp", "to": <digits>, "type": "text", "text": {"body": teks}}`. This works only within 24 h after the recipient last messaged the business number; document that.
  - `template`: same endpoint, with `{"messaging_product": "whatsapp", "to": <digits>, "type": "template", "template": {"name": <name>, "language": {"code": META_WA_TEMPLATE_BAHASA or "id"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": v}, ...]}]}}`.
    - The template name comes from `META_WA_TEMPLATE_PEMBERITAHUAN` or `META_WA_TEMPLATE_CADANGAN`.
    - Parameter order (document it in the README for whoever writes the templates in Meta):
      - pemberitahuan: `[nama_penerima, jeda_menit, nomor_penelepon, nama_pasien, nama_rs, bulan]`
      - cadangan: `[nama_pasien, nama_rs, bulan]`
- Request details:
  - Header `Authorization: Bearer {META_WA_TOKEN}`.
  - `httpx` with a 10 s timeout and **one attempt**; the call must never wait on WhatsApp.
  - Any non-2xx response, timeout or connection error returns `gagal`.
  - `META_WA_API_VERSION` is required in `teks` and `template` modes. Don't hard-code a guessed default; the README should say to use the version shown in the Meta app dashboard.
- Recipient format: digits only, leading `0` becomes `62`, and a leading `+` is dropped. Extract this into a helper `nomor_internasional()` in `aturan_v3.py` and reuse it in `tautan_wa`.
- Never log tokens, phone numbers or message text.
- Tests: `tests/test_wa.py` with `httpx.MockTransport`, no DB. Cover:
  - mode selection;
  - payloads for both kinds in both modes;
  - number normalisation;
  - `gagal` on 4xx/5xx/timeout;
  - rendered Lampiran B text contains no link.

**b) The notice is sent by the backend at claim time** (`agen.ambil_tugas` / `susun_tugas`)

- After `kunci_tugas` returns an id, if that call is `antre` with `percobaan == 0` (first attempt):
  1. Render Lampiran B with `at.pesan_pemberitahuan`, with `nomor_penelepon = config.nomor_penelepon()`, which is the station SIM number.
  2. Send it with `wa.kirim`.
  3. **Whatever the result,** set `status = "wa_terkirim"` and `waktu_wa = now`, and write the log line `tambah_log(conn, id, "wa_terkirim", now, 1, f"wa:{status}")`. If it failed, append a short reason with no number.
  4. The existing WA delay then applies to `menelepon` unchanged.
- The `wa` object in the task payload becomes `{"lewati": true, "dikirim_server": true, "status": <"terkirim" | "simulasi" | "gagal" | null>, "teks": <text or null>}`.
  - `status` and `teks` are null on attempt 2, where no notice is sent.
  - Drop `tautan`. Keep `jeda_wa_menit`.

**c) A shared failed-attempt function, used three times**

Move the `tidak_diangkat` branch of `lapor_status` into `_gagal_satu_percobaan(conn, p, catatan)`.

- **Attempt 1:**
  - set status back to `antre`, with `coba_lagi_setelah = now + jeda_percobaan_menit`;
  - clear `diambil_pada`, `transkrip` and `tangkapan_sementara`;
  - log `menelepon` with the given `catatan`.
- **Attempt 2:**
  - set `tidak_terhubung` with label Tidak terhubung, exactly as today;
  - then send the fallback chat (`at.pesan_cadangan`) with `wa.kirim`;
  - set `chat_cadangan_terkirim = status in ("terkirim", "simulasi")`;
  - log `tidak_terhubung` with `catatan = f"chat:{status}"`.
  - The reply's `chat_cadangan` becomes `{"teks": ..., "dikirim_server": true, "status": ...}`, with no `tautan`.
- A `chat_cadangan_terkirim` report from an old agent must succeed idempotently: when the flag is already true, return the same reply instead of 409.

It is used by:
1. `lapor_status("tidak_diangkat")`;
2. the officer's cancel (e);
3. the stale-call release (f).

**d) Station heartbeat: new `POST /api/v1/agen/detak`** (requires `X-Kunci-Agen`, in `router_agen.py`)

- Body: `{"siap": bool, "alasan": str | null (max 200 chars), "perangkat": str | null}`. Reply 204.
- Store it as `pengaturan["stasiun"] = {"terakhir_terlihat": <iso>, "siap", "alasan", "perangkat"}`.
- `PUT /pengaturan` must still ignore and never overwrite this key (its validator already ignores unknown keys; keep it that way).
- `GET /antrean` returns `pengaturan.stasiun = {"aktif": <terakhir_terlihat within 30 s of server time>, "siap", "alasan", "perangkat", "terakhir_terlihat"}`, or `null` if the station has never been seen.

**e) Officer cancel: new `POST /api/v1/panggilan/{id}/batal`** (Kontrak A, no key, in `router_v3.py`)

- Allowed for status `wa_terkirim`, `menelepon`, `tersambung` or `merekam`: run `_gagal_satu_percobaan(..., "dibatalkan_verifikator")`.
- Allowed for `antre` with `diambil_pada` set: clear `diambil_pada` only.
- Anything else: 409 `tidak_bisa_dibatalkan`.
- Return the updated queue row.

**f) Stale-call release (automatic)**

- At the start of `ambil_tugas`, release any call stuck in `wa_terkirim`, `menelepon`, `tersambung` or `merekam` whose latest `panggilan_log.waktu` (or `diambil_pada`) is older than `KUNCI_MACET_MENIT = 5`. Use `_gagal_satu_percobaan(..., "macet")`.
- Do the same at the start of `GET /antrean`, so the website recovers even with no station polling.
- `membaca_jawaban` is never released this way.

**g) Defaults**

- `aturan_v3.BAWAAN_PENGATURAN["mode_otomatis"] = True`.
- `schema_v3.sql` inserts `'true'` for `mode_otomatis`. The insert stays `on conflict do nothing`, so existing DBs are unchanged until a reset.
- `seed_v3.reset_panggilan` sets `mode_otomatis` true and `jeda` false.
- Update any test that assumed false.

**h) Queue and detail fields**

`tampilan_v3.baris_antre` and `detail` add `coba_lagi_setelah` (ISO or null). The detail `log` already carries `catatan`; keep it.

**i) Contract, stub and tests**

- Update `docs/api-contract-v3.md`: add a short changelog at the top, then the changes to B1 (server-sent WA, the `wa` and `chat_cadangan` objects, `/agen/detak`, stale release) and A (`/batal`, `pengaturan.stasiun`, `coba_lagi_setelah`, default mode).
- `scripts/stub_agen.py`:
  - skip `wa_terkirim` when `task["wa"].get("dikirim_server")`;
  - skip `chat_cadangan_terkirim` when `chat_cadangan.get("dikirim_server")`;
  - post `/agen/detak {"siap": true, "perangkat": "stub"}` every loop.
  - Update `tests/test_stub_agen.py`.
- Extend `tests/test_api_v3_agen.py` and `tests/test_api_v3_tulis.py`. Monkeypatch `wa.kirim`, and use the existing `jam_palsu` clock helper. Cover:
  - notice sent at claim, with the log catatan;
  - no notice on attempt 2;
  - fallback chat on the second miss;
  - Meta failure still lets the call proceed;
  - `detak` stored and `antrean.pengaturan.stasiun.aktif` true, then false after 31 s;
  - `batal` from each allowed status, plus 409 otherwise;
  - stale release after 5 minutes;
  - `mode_otomatis` true after reset.
- The DB tests run against a rolled-back `uji3` schema in Supabase and take minutes. If Supabase is unreachable, still write them, run the tests that need no DB, and say so in the report.

### 4.2 ai-service: Phone helper (new `src/vedika_ai/saluran.py`, mounted from `main.py`)

**Enabling and access**
- Mounted only when env `SALURAN_ADB` is `1` or `palsu`; otherwise its routes don't exist (404).
- It is a separate `APIRouter` without the `X-Kunci-Layanan` dependency.
- Every route rejects clients other than `127.0.0.1` / `::1` with 403 `bukan_lokal`.
- Errors use the service's existing `{"galat": {"kode", "pesan"}}` shape.

**`SALURAN_ADB=1`: real adb**
- Calls `subprocess.run([adb_bin, *(["-s", serial] if serial else []), "shell", ...], capture_output=True, text=True, timeout=8)`.
  - `adb_bin` comes from `SALURAN_ADB_BIN` (default `adb`).
  - `serial` comes from `SALURAN_ADB_SERIAL`.
- If several devices are attached and no serial is set, report not ready with a clear reason.
- Inject the runner function so tests can fake it.

**`SALURAN_ADB=palsu`: in-memory fake phone, for tests and e2e**
- `panggil` sets the state to offhook and `tutup` sets it to idle.
- An extra `POST /v1/saluran/palsu/tutup-penerima` simulates the remote party hanging up.

**Endpoints**

- `GET /v1/saluran/kesehatan` returns `{"siap": bool, "alasan": str | null, "perangkat": str | null, "sim": str | null, "panggilan": "idle" | "offhook" | "ringing"}`. Checks, in order:
  1. `adb devices`: exactly one device in state `device`. `unauthorized` → `alasan = "Izinkan debugging USB di HP"`; none → `"HP tidak terhubung ke laptop"`.
  2. `getprop gsm.sim.state` contains `READY` (dual-SIM gives e.g. `READY,ABSENT`); otherwise `"SIM tidak siap"`.
  3. Call state is `idle`; otherwise `"HP sedang dalam panggilan"`.
  4. `perangkat` comes from `getprop ro.product.model`.
- `POST /v1/saluran/panggil {"nomor": str}`:
  - strip spaces and dashes, then validate `^\+?\d{8,15}$` (422 `nomor_tidak_valid`);
  - run `am start -a android.intent.action.CALL -d tel:<nomor>`;
  - return `{"ok": true}`, or 502 `adb_gagal`.
- `POST /v1/saluran/tutup`: runs `input keyevent KEYCODE_ENDCALL` and returns `{"ok": true}`. It is idempotent.
- `GET /v1/saluran/status` returns `{"panggilan": ...}`.
  - Parse every `mCallState=N` in `dumpsys telephony.registry` (one per SIM).
  - Any `2` means `offhook`, else any `1` means `ringing`, else `idle`.
- `GET /v1/saluran/konfigurasi` returns `{"api_url", "kunci_agen", "kunci_layanan", "audio", "input", "output"}`:
  - `api_url` from `SALURAN_API_URL` (default `http://localhost:8000`);
  - `kunci_agen` from `SALURAN_AGEN_KEY`;
  - `kunci_layanan` from `AI_SERVICE_KEY` or null;
  - `audio` from `SALURAN_AUDIO` (`speaker` default, or `kabel`);
  - `input` and `output` from `SALURAN_INPUT` / `SALURAN_OUTPUT`, as device label substrings or null.
  - This is the only path by which secrets reach the station browser, which is why the router is localhost-only.

**Rules**
- Log with loguru and **never log phone numbers**: "panggil diminta" is enough.
- Pure parsers (adb devices, mCallState, sim state, number validation) go in `tests/test_saluran.py`, plus endpoint tests through `TestClient` with an injected fake runner and the `palsu` mode.
- The Cloudflare Worker does **not** get this helper (station-only). `uv run pytest` must stay green, including `test_deployment_layout.py`.
- Add every new env var to `ai-service/.env.example` with a one-line comment.

### 4.3 Agent page becomes a station console (`ai-service/web/voice-console.html`, `voice-agent.mjs`)

**Boot**
- On load, fetch same-origin `/v1/saluran/konfigurasi`.
  - 404: show "Halaman ini hanya berjalan di laptop stasiun (SALURAN_ADB belum aktif)." and stop.
  - With `?mulai=1`: start the loop automatically.
  - Otherwise: show one "Mulai" button for debugging.
- Keep a "Hentikan" button. Remove all text inputs and the device-picker UI.

**Audio**
- Pick input and output devices whose label contains `konfigurasi.input` / `output`; when null, use the defaults.
- Add a session option `lineConstraints`. The default stays all-false, so existing tests hold.
  - `speaker` passes `{echoCancellation: true, noiseSuppression: true, autoGainControl: true}`.
  - `kabel` passes all false.
- Show the chosen device labels and the audio mode on screen.

**AudioContext**
- The launcher starts Chrome with `--autoplay-policy=no-user-gesture-required`.
- Create a fresh AudioContext per call (no click needed).
- If it is still suspended, show "Chrome memblokir audio; jalankan lewat stasiun.sh" and skip claiming tasks.

**Loop (every 3 s)**
1. `GET /v1/saluran/kesehatan`, then `POST {api_url}/api/v1/agen/detak` with `{siap, alasan, perangkat}`.
2. If `siap`, `POST /agen/ambil`. 204 means wait.
3. With a task, run `runTask` with the automatic operator below.
4. Never let one task's error stop the loop: show it, hang up, and continue.

**`runTask` changes (`voice-agent.mjs`)**
- If `task.wa.dikirim_server` is true, skip WA entirely. The old operator path stays for compatibility, but the station operator's `kirimWa` throws "tidak didukung".
- **Report `menelepon` first,** via `reportWhenAllowed`, which already waits out `409 jeda_belum_lewat`. **Then** call `operator.telepon(task)` to dial. Today it dials first; update the unit tests for the new order.
- Call `operator.kirimChatCadangan` only when `status.chat_cadangan && !status.chat_cadangan.dikirim_server`.
- If any report, transcript or result call returns 404 or 409 with `urutan_salah` / `bukan_berlangsung`, the officer cancelled or the backend released the call. Stop the session, hang up, log one line, and return normally.

**Automatic operator**
- `telepon(task)`: `POST /v1/saluran/panggil {nomor: task.no_tujuan}`.
- Start `VedikaVoiceSession` right after dialing, with `greetFirst: false` as today.
- **Answer detection** (replaces "first recipient fragment = answer"):
  - Give the session an option `acceptAnswer(teks) => bool`. Evaluate it when the **first recipient turn completes** (in `flushTurn`), not on the first fragment.
  - Fire `onAnswer` and reset the clock only when it returns true. Update the existing test "session treats the recipient's first words as the answer and restarts the clock" to match.
  - Export a pure `isOperatorAnnouncement(teks)`: case-insensitive, punctuation ignored. It matches at least: `nomor yang anda tuju`, `tidak dapat dihubungi`, `tidak aktif`, `sedang sibuk`, `di luar jangkauan`, `berada di luar`, `kotak suara`, `mailbox`, `silakan tinggalkan pesan`, `silakan coba`, `the number you`, `is not active`, `is busy`, `cannot be reached`.
  - `acceptAnswer = (t) => !isOperatorAnnouncement(t)`. On an announcement, stop immediately as `tidak_diangkat` and hang up.
  - Lines spoken before the answer are already held back by `runTask` (the `early` buffer) and are never sent for a no-answer.
- **No answer:**
  - no accepted recipient turn within 40 s of dialing gives `tidak_diangkat`;
  - helper status `idle` before an answer (busy, rejected or failed) gives `tidak_diangkat` immediately.
- **During a call:** poll `/v1/saluran/status` every second. `idle` after the answer means the patient hung up: stop the session and upload the result.
- **We hang up** (call `/v1/saluran/tutup`, then stop and upload) when either:
  - 3 s after an AI turn that closes the call. Export a pure `isClosingLine(teks)` that matches `selamat (pagi|siang|sore|malam)` near the end, or `sudah kami catat`.
  - 10 s pass with no speech from either side after an AI turn.

  The session's own `maks_durasi_detik` cap stays.
- Always call `/v1/saluran/tutup` in a `finally` block.

**UI**
- Indonesian copy, plain and small. Show:
  - station readiness (phone model, SIM, audio mode);
  - the current task id and patient name;
  - the call phase and live transcript;
  - the last error.
- Keep the "Simulasi" note.

**Tests** (`node --test ai-service/web/voice-agent.test.mjs`): cover
- the new report order;
- skipping server-sent WA;
- `isOperatorAnnouncement` and `isClosingLine`;
- the `acceptAnswer` path;
- remote hang-up, closing-line hang-up and silence hang-up (fake timers, fake helper);
- 409 or 404 handling;
- `lineConstraints` passthrough.

Then run `bun run build && bun test` in `ai-service/worker`, since the build copies these files.

### 4.4 Station launcher (new `stasiun.sh` at the repo root)

1. Check that `adb` exists (hint: `brew install android-platform-tools`) and that `adb devices` lists exactly one authorised device. Otherwise print the reason and exit 1.
2. Run `adb shell svc power stayon usb`.
3. Start the same three services as `dev.sh`. Reuse its port checks and Supabase reachability check, and start ai-service with `SALURAN_ADB=1` through `uv run --env-file .env`. Wait for health.
4. Keep the Mac awake with `caffeinate -dims` while the script runs.
5. Open the agent page in a dedicated Chrome profile:
   `open -na "Google Chrome" --args --user-data-dir="$HOME/.vedika-stasiun-chrome" --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required --app="http://localhost:8001/voice/?mulai=1"`
   Then open `http://localhost:8899` normally.
6. Print one line per check (phone model, SIM state, audio mode, Meta mode). Ctrl-C stops everything.

`dev.sh` stays as it is. Add `http://localhost:8001` (the agent page origin) to the default in `backend/app/config.py` `cors_origins()` and to `backend/.env.example`.

### 4.5 Website (`app-v3.js`, `api-v3.js`, `app-v3.css`)

Match the prototype's behaviour in API mode. Simulation mode only needs the copy changes.

- **Automatic mode** shows as on by default (it comes from the API).
- **Row button:** "Telepon sekarang" / "Telepon" becomes **"Dahulukan"** (existing `POST /panggilan/{id}/mulai`), with the tooltip "Pindahkan ke urutan berikutnya".
- **Status strip** above the KPI cards, showing exactly one state, first match wins:
  1. API down: a persistent **"Mode simulasi"** banner, not just a toast.
  2. Outside hours (`!pengaturan.dalam_jam`): "Di luar jam panggilan (09.00–17.00 WIB). Antrean dilanjutkan otomatis pada jam kerja."
  3. Station never seen or `!stasiun.aktif`: "Saluran telepon terputus sejak HH.MM". If `aktif && !siap`: "Saluran telepon belum siap: {alasan}".
  4. A call is running: "Sedang menelepon {pasien} · {status}", with a "Buka panggilan" button.
  5. Mode off: "Panggilan otomatis mati". Paused: "Dijeda".
  6. A retry is pending: "Siap menelepon · {pasien} dicoba lagi dalam m:ss", counting down from `coba_lagi_setelah`.
  7. Otherwise: "Panggilan otomatis aktif".

  Add health chips for API, Database, Pembaca jawaban (from `/kesehatan`) and Saluran telepon.
- **Recovery:** on a running row and on the call screen, show **"Batalkan panggilan"** when the station is inactive or the call's last log entry is older than 60 s. Confirm, then `POST /batal`, then show a toast.
- **Retry countdown** in the row status: "Coba lagi m:ss".
- **WA status on the call screen**, read from the log `catatan`:
  - `wa:terkirim` → "Pesan WA terkirim";
  - `wa:simulasi` → "Pesan WA (simulasi, Meta belum diatur)";
  - `wa:gagal` → "Pesan WA gagal terkirim".

  The WA phone mock shows `pesan_wa`, labelled "Dikirim otomatis oleh server".
- **No pre-recorded clips in API mode:** `api-v3.js` `kePasien` sets `suara_langsung: null`. Only the real recording plays, on the evidence card.
- **Copy:** remove the text "agen suara dan pembaca jawaban masih stub".
- `tests/alur.test.js` tests the old v2 flow and does not cover v3. Leave it alone. Add `tests/alur-v3.test.js` (Playwright, same style, simulation mode with no API). It must check:
  - the status strip renders;
  - rows show "Dahulukan";
  - S1 runs to its evidence card with 11 vs 3;
  - no horizontal scroll at 390 px width.

### 4.6 Docs (Indonesian; match the tone of existing docs)

- **`docs/rencana-v3-otomatis/STASIUN.md`** covers:
  - hardware for speaker mode and for the cable kit;
  - phone settings: USB debugging, authorising the laptop, a default SIM for calls, Do Not Disturb, stay awake;
  - every env var;
  - `stasiun.sh`;
  - Meta setup: app, test number, registering up to 5 recipient numbers, the 24 h text window, templates and their parameter order;
  - a troubleshooting table: unauthorised device, SIM not ready, a SIM chooser appears, no audio, echo, announcement misdetected, Chrome blocks audio.
- **`docs/rencana-v3-otomatis/UJI-HP.md`**: a checklist the team runs later with the real phone.
  - The day-one ADB checks: `adb devices`; dial with `am start ... CALL`; `mCallState` reads 2 then 0; `KEYCODE_ENDCALL`; audio both ways; a Meta test message.
  - Then S1–S8, each with what the tester should say (from `data-uji-konfirmasi/transkrip_uji/` and `skenario_uji.json`), the expected label, and the expected RS summary.
  - An announcement case (call a switched-off number).
  - Pass/fail boxes, plus what to record: screenshots and transcript accuracy against R3.6's ≥90% gate.
- Update `ai-service/README.md`: the station replaces the WhatsApp Web / BlackHole call setup; keep a two-line "archived" note.
- Update `backend/README.md`: WA env and the new endpoints.

### 4.7 Optional, last: run against the deployed backend

Only after everything above passes:
- Store recordings in a private Supabase Storage bucket. Today `app/penyimpanan.py` writes to local disk, which Vercel doesn't keep.
- Verify that `BackgroundTasks` reading finishes on Vercel; if it doesn't, read synchronously inside `/hasil`.

If you don't do this, list it as not done.

## 5. Acceptance

**Automated checks.** Run each and report the exact command and result:
- `cd ai-service && uv run pytest && uv run ruff check .`
- `node --test ai-service/web/voice-agent.test.mjs`
- `cd ai-service/worker && bun run build && bun test`
- `cd backend && .venv/bin/pytest` (needs Supabase; if unreachable, run the no-DB tests and say so)
- `node tests/alur-v3.test.js` (new), and `TARGET_URL=http://localhost:8899/v2.html node tests/alur.test.js` to show v2 still works. If the v2 test already failed before your changes, say so instead of fixing it.
- Adapt `ai-service/scripts/agent_e2e.mjs` to the station flow, keeping the robot recipient on BlackHole. Use `SALURAN_ADB=palsu` with `SALURAN_AUDIO=kabel`, input BlackHole 2ch and output BlackHole 16ch. Required outcomes:
  - **S1:** label `tidak_sesuai`.
  - **S5:** two attempts with fallback chat logged, label `tidak_terhubung`.
  - **Announcement:** the robot says "Nomor yang Anda tuju tidak dapat dihubungi"; the call never reaches `tersambung` and attempt 2 is scheduled.

  If BlackHole or Gemini Live isn't available to you, still make the script runnable and say it wasn't run.

**Behaviour.** Verify at least with backend + `stub_mesin` + `stub_agen` + website, within hours (use `PUT /pengaturan` to widen hours for testing):
- After "Mulai ulang demo":
  - automatic mode is on and S1 starts with no click;
  - the notice is logged with `wa:simulasi` when Meta isn't configured;
  - the card shows 11 vs 3;
  - RS Melati becomes Perlu klarifikasi RS (3 of 5).
- If the agent is killed mid-call:
  - the website shows the station offline within 30 s, plus "Batalkan panggilan";
  - pressing it schedules attempt 2 and the queue continues;
  - untouched, the call is released automatically after 5 minutes.
- "Dahulukan" moves a patient to the front.

**Expected scenario outcomes** (`data-uji-konfirmasi/skenario_uji.json`):

| Scenario | Patient (recipient) | Expected |
|---|---|---|
| S1 | Andi Pratama | Tidak sesuai, 11 billed vs 3 |
| S2 | Siti Rahmawati (Dewi, child) | Tidak sesuai + tanda bahaya `tanda_tangan_tanpa_layanan` |
| S3 | Budi Santoso | Sesuai |
| S4 | Karti Lestari (Bayu, child) | Tidak yakin |
| S5 | Joko Prasetyo | Tidak terhubung after 2 attempts, fallback chat sent |
| S6 | Slamet Riyadi | Tidak sesuai |
| S7 | Rina Marlina | Never queued (only indicator I3) |
| S8 | Hendra Wijaya | Menolak |

The RS summary must match `data-uji-konfirmasi/expected_ringkasan_rs.json`, before S1 and after all scenarios.

**Real-phone testing** isn't possible for you. Produce `UJI-HP.md` so the team can run it.

## 6. Hard constraints

- Labels and the RS summary are computed only by the backend with `aturan.py`. The agent, the helper and the reader never send a label.
- At most two attempts. The WA delay, retry delay and working hours are decided by the server clock, never the browser.
- Call script rules (R3.3) are unchanged:
  - the AI says it is an automated assistant;
  - it never asks for NIK, OTP, bank details or money;
  - it never says "curang" or "fraud".
- WA text is exactly Lampiran B, with no links.
- A person decides. "Pilih tindakan lain" always requires a written reason.
- Recipient identity never appears in data shared with hospitals. Every screen keeps the "Simulasi" label. No BPJS logo. Synthetic data only. Prototype calls and messages go only to `NOMOR_PENGUJI`.
- Secrets (`GEMINI_API_KEY`, `AGEN_KEY`, `AI_SERVICE_KEY`, `META_WA_TOKEN`, database URL) never appear in the officer's browser, in git, or in logs. The station browser gets the agent key only through the localhost-only config route.
- Never commit or read `data-uji-konfirmasi/kunci_kebenaran_*.csv` in product code.

## 7. Working rules

- Work on a new branch `v3-stasiun-android` from `main`.
- Commit per logical step, in the format `<type>(<scope>): <what changed>`, e.g. `feat(backend): kirim pemberitahuan WA dari server`.
  - No co-author trailer or any Claude attribution in commits.
  - Never push or force-push, and never skip hooks.
  - Don't commit `.env` files, tokens, `backend/uploads/`, recordings, or the scratch output of e2e runs.
- Style:
  - Python uses `uv`, functions over classes, f-strings. ai-service logs with loguru; backend keeps its existing `logging`.
  - JS uses `const` and arrow functions, `async`/`await`, no namespace imports; `bun` for the worker.
  - Follow each folder's naming: Indonesian identifiers in backend and website, English in ai-service as today.
  - Minimal comments, and no new dependencies unless unavoidable (`httpx` is already in both services).
- Read before you edit, keep diffs focused, and don't touch v2 files.

## 8. Final report

Reply with:
1. What you built, per section 4.1–4.7.
2. Every command you ran and its result, with failures quoted.
3. What you couldn't run and why.
4. Decisions you made where this spec was open.
5. The five things most likely to need adjusting on the real phone.
6. How to start the station, in three lines.
