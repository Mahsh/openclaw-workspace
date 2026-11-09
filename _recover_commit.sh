#!/usr/bin/env bash
set -euo pipefail
WS="/c/Users/mahaishou/.openclaw/workspace"
cd "$WS"
# Guard: we must be in the workspace repo
[ "$(git rev-parse --show-toplevel)" = "C:/Users/mahaishou/.openclaw/workspace" ] || { echo "ABORT: wrong repo"; exit 1; }
git add -A
git commit -q -m "chore: 恢复误删的工作区文件 + 补回当日未提交内容（脚本事故，详见 memory/2026-11-09.md）" || echo "nothing to commit"
git push -q --force origin main
echo "== workspace repo main =="
git log --oneline -3
git ls-remote origin refs/heads/main | cut -f1
