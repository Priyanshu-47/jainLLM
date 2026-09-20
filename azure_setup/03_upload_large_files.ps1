REM ============================================
REM STEP 3: Upload large files NOT in git repo
REM These files were excluded from GitHub (>100MB)
REM Run from PowerShell on your Windows machine
REM ============================================

$SSH_KEY = "D:\DL\JainVM_key.pem"
$VM = "azureuser@20.98.93.123"
$REMOTE_BASE = "~/jainLLM/svk-corpus"

# Files to upload (local path -> remote path)
$files = @(
    @{ Local = "E:\JainLLM\svk-corpus\data\quality\units_quality.jsonl";          Remote = "$REMOTE_BASE/data/quality/units_quality.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\release\low_quality_units.jsonl";       Remote = "$REMOTE_BASE/data/release/low_quality_units.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\release\rag_corpus.jsonl";              Remote = "$REMOTE_BASE/data/release/rag_corpus.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\release\training_corpus.jsonl";         Remote = "$REMOTE_BASE/data/release/training_corpus.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\segmented\SVK-2006\units.jsonl";        Remote = "$REMOTE_BASE/data/segmented/SVK-2006/units.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\segmented\SVK-2007\units.jsonl";        Remote = "$REMOTE_BASE/data/segmented/SVK-2007/units.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\training\sft_candidate_passages_v1.jsonl"; Remote = "$REMOTE_BASE/data/training/sft_candidate_passages_v1.jsonl" },
    @{ Local = "E:\JainLLM\svk-corpus\data\training\sft_candidate_passages_v2.jsonl"; Remote = "$REMOTE_BASE/data/training/sft_candidate_passages_v2.jsonl" }
)

foreach ($f in $files) {
    if (Test-Path $f.Local) {
        $size = [math]::Round((Get-Item $f.Local).Length / 1MB, 1)
        Write-Host "Uploading $size MB : $($f.Local)" -ForegroundColor Yellow
        
        # Ensure remote directory exists
        $remoteDir = Split-Path $f.Remote -Parent
        ssh -i $SSH_KEY $VM "mkdir -p $remoteDir"
        
        # Upload with scp (preserves speed better than individual ssh commands)
        scp -i $SSH_KEY -o Compression=yes $f.Local "${VM}:$($f.Remote)"
        
        Write-Host "  Done." -ForegroundColor Green
    } else {
        Write-Host "  SKIP (not found): $($f.Local)" -ForegroundColor DarkGray
    }
}

Write-Host "`n=== All large files uploaded ===" -ForegroundColor Cyan
