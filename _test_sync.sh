#!/usr/bin/env bash
set -euo pipefail
SF="$HOME/.openclaw/workspace/sync_files"
TMP="$HOME/.openclaw/workspace/_cloud_sim"

# --- Simulate the CLOUD machine ---
rm -rf "$TMP"
git clone -q "git@github.com:Mahsh/files_sync.git" "$TMP"
cd "$TMP"
echo "written by cloud machine" > cloud-note.txt
git add -A && git commit -q -m "test: file from cloud machine" && git push -q origin main
echo "[cloud] pushed cloud-note.txt"

# --- LOCAL machine pulls it ---
cd "$SF"
bash sync.sh
test -f cloud-note.txt && echo "[local] PULL OK: cloud-note.txt arrived"

# --- LOCAL machine writes + pushes ---
echo "written by local windows machine" > local-note.txt
bash sync.sh
echo "[local] pushed local-note.txt"

# --- CLOUD machine pulls it ---
cd "$TMP"
git pull --rebase -q origin main
test -f local-note.txt && echo "[cloud] PULL OK: local-note.txt arrived"

# --- cleanup test files (propagate deletion) ---
cd "$SF" && rm -f cloud-note.txt local-note.txt && bash sync.sh
cd "$TMP" && git pull --rebase -q origin main && rm -rf "$TMP"
echo "== round-trip PASSED =="
