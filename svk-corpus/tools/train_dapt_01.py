#!/usr/bin/env python3
"""DAPT-01: Domain Adaptation Training Script for Qwen3-8B."""
import os
import json
import yaml
from pathlib import Path
from datetime import datetime

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_training_script(config):
    """Create the training script content."""
    script = f'''#!/bin/bash
# DAPT-01: Domain Adaptation Training
# Base Model: {config["model"]["name"]}
# Date: {datetime.now().isoformat()}

set -e

echo "=== DAPT-01: Domain Adaptation Training ==="
echo "Base Model: {config["model"]["name"]}"
echo "Start Time: $(date)"

# Create output directory
mkdir -p {config["training"]["output_dir"]}

# Run training
python -m torch.distributed.launch \\
    --nproc_per_node=1 \\
    --master_port=29500 \\
    -m svk_corpus.training.dapt_trainer \\
    --model_name {config["model"]["name"]} \\
    --train_file {config["dataset"]["train_file"]} \\
    --validation_file {config["dataset"]["validation_file"]} \\
    --output_dir {config["training"]["output_dir"]} \\
    --num_train_epochs {config["training"]["num_train_epochs"]} \\
    --per_device_train_batch_size {config["training"]["per_device_train_batch_size"]} \\
    --gradient_accumulation_steps {config["training"]["gradient_accumulation_steps"]} \\
    --learning_rate {config["training"]["learning_rate"]} \\
    --lora_r {config["lora"]["r"]} \\
    --lora_alpha {config["lora"]["lora_alpha"]} \\
    --max_seq_length {config["training"]["max_seq_length"]} \\
    --logging_steps {config["training"]["logging_steps"]} \\
    --save_steps {config["training"]["save_steps"]} \\
    --eval_steps {config["training"]["eval_steps"]} \\
    --seed {config["training"]["seed"]} \\
    --bf16 \\
    --report_to tensorboard

echo "=== DAPT-01 Complete ==="
echo "End Time: $(date)"
echo "Output: {config["training"]["output_dir"]}"
'''
    return script

def main():
    config_path = "configs/dapt_qwen3_8b.yaml"
    config = load_config(config_path)
    
    # Create training script
    script_content = create_training_script(config)
    script_path = "scripts/run_dapt_01.sh"
    
    os.makedirs("scripts", exist_ok=True)
    with open(script_path, 'w') as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)
    
    print(f"Created training script: {script_path}")
    print(f"Config: {config_path}")
    print(f"Output dir: {config['training']['output_dir']}")
    
    # Print summary
    print("\n=== DAPT-01 Configuration ===")
    print(f"Base Model: {config['model']['name']}")
    print(f"LoRA rank: {config['lora']['r']}")
    print(f"Learning rate: {config['training']['learning_rate']}")
    print(f"Epochs: {config['training']['num_train_epochs']}")
    print(f"Batch size: {config['training']['per_device_train_batch_size']}")
    print(f"Gradient accumulation: {config['training']['gradient_accumulation_steps']}")
    print(f"Max seq length: {config['training']['max_seq_length']}")
    print(f"Seed: {config['training']['seed']}")

if __name__ == '__main__':
    main()
