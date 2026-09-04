#!/usr/bin/env bash
# 上传 Release 资产到 GitHub（token 不落盘，运行时从 GCM 读取）
set -u
cd /e/AemeathVoice

RELEASE_ID="382718210"
REPO="1983879947-ctrl/AemeathVoice"
DIR="dist/release"

TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | \
  "C:/Users/27298/.workbuddy/binaries/PortableGit/versions/1.2.0/mingw64/bin/git-credential-manager.exe" get | \
  grep '^password=' | cut -d= -f2-)

if [ -z "$TOKEN" ]; then echo "ERROR: no token"; exit 1; fi

upload() {
  local f="$1"
  echo "=== uploading $(basename "$f") ($(du -m "$f" | cut -f1)MB) ==="
  for attempt in 1 2 3; do
    code=$(curl -s -o /tmp/upload_resp.json -w "%{http_code}" \
      -X POST \
      -H "Authorization: token $TOKEN" \
      -H "Content-Type: application/zip" \
      -H "Content-Length: $(stat -c %s "$f")" \
      --data-binary "@$f" \
      "https://uploads.github.com/repos/$REPO/releases/$RELEASE_ID/assets?name=$(basename "$f")")
    if [ "$code" = "201" ]; then
      echo "  [OK] attempt $attempt -> HTTP $code"
      return 0
    fi
    echo "  [RETRY] attempt $attempt -> HTTP $code: $(head -c 200 /tmp/upload_resp.json)"
    sleep 5
  done
  echo "  [FAIL] $(basename "$f")"
  return 1
}

upload "$DIR/AemeathVoice_v1.0.0_part1_runtime.zip" || exit 1
upload "$DIR/AemeathVoice_v1.0.0_part2_models.zip" || exit 1
upload "$DIR/AemeathVoice_v1.0.0_part3_g2pw_text.zip" || exit 1
echo "=== ALL UPLOADED ==="
