#!/usr/bin/env bash
# Task 57 Phase 3: official ADC login for Colab CLI (run interactively by user/agent with TTY)
# Does NOT print tokens. Requires browser + paste-back of auth code.
set -euo pipefail
export PATH="/home/azureuser/.local/bin:/home/azureuser/google-cloud-sdk/bin:$PATH"

echo "Starting Google Application Default Credentials login..."
echo "You will open a URL in your browser, sign in as:"
echo "  priyanshulodha4747474747@gmail.com"
echo "Then paste the authorization code back into this terminal."
echo ""

gcloud auth application-default login \
  --no-launch-browser \
  --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory

echo ""
echo "ADC login complete. Verifying colab identity..."
colab --auth=adc whoami
