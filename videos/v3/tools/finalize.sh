#!/bin/bash
# Bangun index.html, render 1080p, normalisasi ke -14 LUFS (2 pass, TP -1.5). Jalankan dari akar repo:
#   bash videos/v3/tools/finalize.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
python3 videos/v3/tools/build.py
cd videos/v3
npx --yes hyperframes@0.8.146 check | sed 's/\x1b\[[0-9;]*m//g' | grep -E "Check (passed|failed)"
mkdir -p renders
npx --yes hyperframes@0.8.146 render --quiet --video-frame-format png -o renders/v3-raw.mp4
ffmpeg -hide_banner -i renders/v3-raw.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p' > renders/ln.json
F=$(python3 -c "
import json;m=json.load(open('renders/ln.json'))
print(f\"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true\")")
ffmpeg -v error -y -i renders/v3-raw.mp4 -c:v copy -af "$F,aresample=192000,alimiter=limit=0.79:attack=2:release=60:level=false,aresample=48000" -c:a aac -b:a 192k -ar 48000 -movflags +faststart renders/vedika-autentik-demo-v3-final.mp4
ffmpeg -i renders/vedika-autentik-demo-v3-final.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tail -3
ffprobe -v error -show_entries format=duration -of csv=p=0 renders/vedika-autentik-demo-v3-final.mp4
