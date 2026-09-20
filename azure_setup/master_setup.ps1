#!/usr/bin/env pwsh
<# ============================================
   MASTER SCRIPT: Full Azure VM Setup for JainLLM
   Run from PowerShell on your Windows machine
   ============================================ #>

$SSH_KEY = "D:\DL\JainVM_key.pem"
$VM = "azureuser@20.98.93.123"
$REMOTE_BASE = "~/jainLLM/svk-corpus"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " JainLLM Azure VM Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --------------------------------------------------
# STEP 1: Clean up any previously uploaded files
# --------------------------------------------------
Write-Host "`n[1/5] Cleaning up previously uploaded files..." -ForegroundColor Yellow
ssh -i $SSH_KEY $VM @"
cd ~
# Remove files that were slowly uploaded before
rm -rf svk-corpus jainLLM .freebuff Analysis.txt Research.txt README.md
rm -f jain_svk_*.md jain_svk_*.csv
echo 'Cleanup done'
"@

# --------------------------------------------------
# STEP 2: Clone the repo
# --------------------------------------------------
Write-Host "`n[2/5] Cloning repo from GitHub..." -ForegroundColor Yellow
ssh -i $SSH_KEY $VM @"
cd ~
git clone https://github.com/Priyanshu-47/jainLLM.git
echo 'Clone complete'
ls -la jainLLM/
"@

# --------------------------------------------------
# STEP 3: Install system deps + Python venv
# --------------------------------------------------
Write-Host "`n[3/5] Installing system dependencies..." -ForegroundColor Yellow
ssh -i $SSH_KEY $VM @"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv build-essential curl git
python3 --version
echo 'System deps installed'
"@

Write-Host "`n[3b] Setting up Python venv..." -ForegroundColor Yellow
ssh -i $SSH_KEY $VM @"
cd ~/jainLLM/svk-corpus
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
echo 'Venv ready'
"@

# --------------------------------------------------
# STEP 4: Upload large files not in git
# --------------------------------------------------
Write-Host "`n[4/5] Uploading large files (not in git)..." -ForegroundColor Yellow

$largeFiles = @(
    @{ Local = "E:\JainLLM\svk-corpus\data\quality\units_quality.jsonl";          Remote = "$REMOTE_BASE/data/quality/units_quality.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\release\low_quality_units.jsonl";       Remote = "$REMOTE_BASE/data/release/low_quality_units.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\release\rag_corpus.jsonl";              Remote = "$REMOTE_BASE/data/release/rag_corpus.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\release\training_corpus.jsonl";         Remote = "$REMOTE_BASE/data/release/training_corpus.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\segmented\SVK-2006\units.jsonl";        Remote = "$REMOTE_BASE/data/segmented/SVK-2006/units.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\segmented\SVK-2007\units.jsonl";        Remote = "$REMOTE_BASE/data/segmented/SVK-2007/units.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\training\sft_candidate_passages_v1.jsonl"; Remote = "$REMOTE_BASE/data/training/sft_candidate_passages_v1.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\training\sft_candidate_passages_v2.jsonl"; Remote = "$REMOTE_BASE/data/training/sft_candidate_passages_v2.jsonl" }
)

foreach ($f in $largeFiles) {
    if (Test-Path $f.Local) {
        $size = [math]::Round((Get-Item $f.Local).Length / 1MB, 1)
        Write-Host "  Uploading $size MB : $(Split-Path $f.Local -Leaf)" -ForegroundColor DarkYellow
        
        # Ensure remote dir exists
        $remoteDir = Split-Path $f.Remote -Parent
        ssh -i $SSH_KEY $VM "mkdir -p $remoteDir"
        
        # Upload with compression
        scp -i $SSH_KEY -o Compression=yes $f.Local "${VM}:$($f.Remote)"
        
        Write-Host "    Done" -ForegroundColor Green
    }
}

# --------------------------------------------------
# STEP 5: Install OpenCode
# --------------------------------------------------
Write-Host "`n[5/5] Installing OpenCode..." -ForegroundColor Yellow
ssh -i $SSH_KEY $VM @"
curl -fsSL https://opencode.ai/install | bash
echo 'OpenCode installed'
opencode --version 2>/dev/null || echo 'OpenCode installed (restart shell to use)'
"@

# --------------------------------------------------
# VERIFY
# --------------------------------------------------
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
ssh -i $SSH_KEY $VM @"
cd ~/jainLLM/svk-corpus
echo '--- Repo ---'
ls -la
echo ''
echo '--- Large files ---'
du -sh data/release/*.jsonl data/quality/units_quality.jsonl data/training/sft_candidate_passages_*.jsonl data/segmented/SVK-2006/units.jsonl data/segmented/SVK-2007/units.jsonl 2>/dev/null
echo ''
echo '--- Python ---'
source .venv/bin/activate
python3 --version
echo ''
echo '--- OpenCode ---'
which opencode 2>/dev/null || echo '(restart shell to use opencode)'
"@

Write-Host "`n============================================" -ForegroundColor Green
Write-Host " SETUP COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "To connect to your VM:" -ForegroundColor White
Write-Host "  ssh -i `"D:\DL\JainVM_key.pem`" azureuser@20.98.93.123" -ForegroundColor Yellow
Write-Host ""
Write-Host "Once connected:" -ForegroundColor White
Write-Host "  cd ~/jainLLM/svk-corpus" -ForegroundColor Yellow
Write-Host "  source .venv/bin/activate" -ForegroundColor Yellow
Write-Host "  export PYTHONPATH=`$(pwd)/src" -ForegroundColor Yellow
Write-Host "  opencode" -ForegroundColor Yellow
