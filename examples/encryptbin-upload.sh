#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 FILE [TITLE] [EXPIRE]"
  echo "Example: $0 logfile.txt 'Nightly build log' 30d"
  exit 1
fi

CONTENT_FILE="$1"
TITLE="${2:-Untitled}"
EXPIRE="${3:-30d}"
BURN="false"

# Generate random key (32 bytes)
KEY_B64=$(openssl rand -base64 32)
KEY_HEX=$(echo -n "$KEY_B64" | base64 -d | xxd -p -c 256)
IV_B64=$(openssl rand -base64 12)
IV_HEX=$(echo -n "$IV_B64" | base64 -d | xxd -p -c 256)

# Encrypt file content
CIPHERTEXT=$(openssl enc -aes-256-gcm -K "$KEY_HEX" -iv "$IV_HEX" \
  -in "$CONTENT_FILE" -out /dev/stdout -base64 2>/dev/null)

# Build JSON payload
PAYLOAD=$(jq -n \
  --arg ct "$CIPHERTEXT" \
  --arg iv "$IV_B64" \
  --arg title "$TITLE" \
  --arg exp "$EXPIRE" \
  --argjson burn $BURN \
  '{ciphertext_b64:$ct, iv_b64:$iv, alg:"AES-GCM", title:$title, expires:$exp, burn_after:$burn}')

# Post to EncryptBin server
RESP=$(curl -sk -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" https://localhost/api/paste_encrypted)

ID=$(echo "$RESP" | jq -r '.id')
URL=$(echo "$RESP" | jq -r '.url')

# Print shareable link with key in URL hash
KEY_URL=$(echo -n "$KEY_B64" | tr '+/' '-_' | tr -d '=')
echo "Shareable link: ${URL}#${KEY_URL}"
