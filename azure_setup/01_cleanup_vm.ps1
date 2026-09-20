REM ============================================
REM STEP 1: SSH into VM and clean up uploaded files
REM Run this from PowerShell on your Windows machine
REM ============================================

REM SSH into the VM (run this first to check what's there)
ssh -i "D:\DL\JainVM_key.pem" azureuser@20.98.93.123 "ls -la ~ && du -sh ~/* 2>/dev/null"

REM Once you see what's there, delete the uploaded files:
REM (replace with actual filenames you see)
ssh -i "D:\DL\JainVM_key.pem" azureuser@20.98.93.123 "rm -rf ~/svk-corpus ~/jainLLM ~/.freebuff ~/Analysis.txt ~/Research.txt ~/jain_svk_*.md ~/jain_svk_*.csv ~/README.md 2>/dev/null; echo 'Cleaned up'"
