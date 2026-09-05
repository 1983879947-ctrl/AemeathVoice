#!/bin/bash
# 原位替换 v1.0.0 资产（链接 URL 不变）
set -u
cd /e/AemeathVoice

TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | \
  "C:/Users/27298/.workbuddy/binaries/PortableGit/versions/1.2.0/mingw64/bin/git-credential-manager.exe" get | \
  grep '^password=' | cut -d= -f2-)
[ -z "$TOKEN" ] && { echo "ERROR: no token"; exit 1; }

RID="382718210"
DIR="dist/release_v2"

# 1. 删除旧资产（part2/part3 复用同名，新 part1 覆盖同名同 hash）
echo "=== 删除旧资产 ==="
for ID in 544326399 544327899 544334415; do
  c=$(curl -s -o /tmp/del.txt -w "%{http_code}" --noproxy '*' -X DELETE \
    -H "Authorization: token $TOKEN" \
    "https://api.github.com/repos/1983879947-ctrl/AemeathVoice/releases/assets/$ID")
  echo "DELETE $ID -> HTTP $c"
done

# 2. 上传新资产
upload() {
  local f="$1"
  echo "=== uploading $(basename "$f") ($(du -m "$f" | cut -f1)MB) ==="
  for attempt in 1 2 3; do
    code=$(curl -s -o /tmp/upload_resp.json -w "%{http_code}" --noproxy '*' -X POST \
      -H "Authorization: token $TOKEN" \
      -H "Content-Type: application/zip" \
      -H "Content-Length: $(stat -c %s "$f")" \
      --data-binary "@$f" \
      "https://uploads.github.com/repos/1983879947-ctrl/AemeathVoice/releases/$RID/assets?name=$(basename "$f")")
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
upload "$DIR/AemeathVoice_v1.0.0_part2_models.zip"   || exit 1
upload "$DIR/AemeathVoice_v1.0.0_part3_g2pw_text.zip" || exit 1
echo "=== ALL REPLACED ==="