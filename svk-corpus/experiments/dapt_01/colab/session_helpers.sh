#!/usr/bin/env bash
# Safe session lifecycle — NEVER run two colab session mutations in parallel.
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/google-cloud-sdk/bin:$PATH"
CMD="${1:-}"
SESSION="${SESSION:-dapt57}"
case "$CMD" in
  start)
    colab --auth=adc new -s "$SESSION" --gpu T4
    colab --auth=adc status -s "$SESSION"
    ;;
  status)
    colab --auth=adc status -s "$SESSION"
    colab --auth=adc usage
    ;;
  exec)
    shift
    colab --auth=adc exec -s "$SESSION" "$@"
    ;;
  upload)
    shift
    colab --auth=adc upload -s "$SESSION" "$@"
    ;;
  download)
    shift
    colab --auth=adc download -s "$SESSION" "$@"
    ;;
  stop)
    colab --auth=adc stop -s "$SESSION"
    ;;
  *)
    echo "usage: $0 start|status|exec|upload|download|stop"; exit 1;;
esac
