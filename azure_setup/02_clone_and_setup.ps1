REM ============================================
REM STEP 2: Clone repo + setup on Azure VM
REM Run this from PowerShell on your Windows machine
REM ============================================

$SSH = 'ssh -i "D:\DL\JainVM_key.pem" azureuser@20.98.93.123'

# --- Part A: Clone the repo on the VM ---
Write-Host "=== Cloning repo on VM ===" -ForegroundColor Cyan
Invoke-Expression "$SSH `"cd ~ && git clone https://github.com/Priyanshu-47/jainLLM.git && echo 'Clone complete' && ls -la jainLLM/`""

# --- Part B: Install system dependencies on the VM ---
Write-Host "`n=== Installing system deps ===" -ForegroundColor Cyan
Invoke-Expression "$SSH `"sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv build-essential curl git`""

# --- Part C: Setup Python venv on the VM ---
Write-Host "`n=== Setting up Python venv ===" -ForegroundColor Cyan
Invoke-Expression "$SSH `"cd ~/jainLLM/svk-corpus && python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && echo 'Venv ready'`""

# --- Part D: Install OpenCode on the VM ---
Write-Host "`n=== Installing OpenCode ===" -ForegroundColor Cyan
Invoke-Expression "$SSH `"curl -fsSL https://opencode.ai/install | bash && echo 'OpenCode installed'`""
