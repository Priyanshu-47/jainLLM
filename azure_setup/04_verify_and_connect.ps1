REM ============================================
REM STEP 4: Quick SSH connect + verify everything
REM Run from PowerShell on your Windows machine
REM ============================================

$SSH_KEY = "D:\DL\JainVM_key.pem"
$VM = "azureuser@20.98.93.123"

# Quick connect (interactive)
Write-Host "=== Connecting to VM ===" -ForegroundColor Cyan
Write-Host "Run these commands once connected:" -ForegroundColor Yellow
Write-Host "  cd ~/jainLLM/svk-corpus"
Write-Host "  source .venv/bin/activate"
Write-Host "  export PYTHONPATH=\`$(pwd)/src"
Write-Host "  python -m unittest discover -s tests -v"
Write-Host "  opencode"
Write-Host ""

# Or run verification remotely
Write-Host "=== Running remote verification ===" -ForegroundColor Cyan
$cmds = @"
cd ~/jainLLM/svk-corpus
echo '--- Repo structure ---'
ls -la
echo ''
echo '--- Data dirs ---'
ls data/segmented/ | head -20
echo ''
echo '--- Large files ---'
du -sh data/release/*.jsonl data/quality/units_quality.jsonl data/training/sft_candidate_passages_*.jsonl data/segmented/SVK-2006/units.jsonl data/segmented/SVK-2007/units.jsonl 2>/dev/null
echo ''
echo '--- Tests ---'
source .venv/bin/activate
export PYTHONPATH=`$(pwd)/src
python -m unittest discover -s tests 2>&1 | tail -5
echo ''
echo '--- OpenCode ---'
which opencode 2>/dev/null || echo 'OpenCode not installed yet'
"@

ssh -i $SSH_KEY $VM $cmds
