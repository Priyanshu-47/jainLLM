#!/usr/bin/env python3
"""DAPT-01: Domain Adaptation Trainer for Qwen3-8B."""
import os
import json
import torch
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class DAPTTrainer:
    """Domain Adaptation Trainer using QLoRA."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.trainer = None
        
    def load_model(self):
        """Load base model and tokenizer."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        
        print(f"Loading model: {self.config['model']['name']}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config['model']['name'],
            trust_remote_code=True
        )
        
        # Load model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config['model']['name'],
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Prepare for training
        self.model = prepare_model_for_kbit_training(self.model)
        
        # Apply LoRA
        lora_config = LoraConfig(
            r=self.config['lora']['r'],
            lora_alpha=self.config['lora']['lora_alpha'],
            lora_dropout=self.config['lora']['lora_dropout'],
            target_modules=self.config['lora']['target_modules'],
            bias=self.config['lora']['bias'],
            task_type=self.config['lora']['task_type']
        )
        
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        
        print("Model loaded successfully")
        
    def load_dataset(self):
        """Load and tokenize dataset."""
        from datasets import load_dataset
        
        print(f"Loading dataset: {self.config['dataset']['train_file']}")
        
        dataset = load_dataset(
            'json',
            data_files={
                'train': self.config['dataset']['train_file'],
                'validation': self.config['dataset']['validation_file']
            }
        )
        
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                truncation=True,
                padding='max_length',
                max_length=self.config['training']['max_seq_length']
            )
        
        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            num_proc=self.config['dataset']['preprocessing_num_workers'],
            remove_columns=dataset['train'].column_names
        )
        
        print(f"Dataset loaded: {len(tokenized_dataset['train'])} train, {len(tokenized_dataset['validation'])} val")
        return tokenized_dataset
        
    def train(self):
        """Run training."""
        from transformers import TrainingArguments, Trainer
        
        print("Starting training...")
        
        training_args = TrainingArguments(
            output_dir=self.config['training']['output_dir'],
            num_train_epochs=self.config['training']['num_train_epochs'],
            per_device_train_batch_size=self.config['training']['per_device_train_batch_size'],
            per_device_eval_batch_size=self.config['training']['per_device_eval_batch_size'],
            gradient_accumulation_steps=self.config['training']['gradient_accumulation_steps'],
            learning_rate=self.config['training']['learning_rate'],
            weight_decay=self.config['training']['weight_decay'],
            warmup_ratio=self.config['training']['warmup_ratio'],
            lr_scheduler_type=self.config['training']['lr_scheduler_type'],
            max_grad_norm=self.config['training']['max_grad_norm'],
            logging_steps=self.config['training']['logging_steps'],
            save_steps=self.config['training']['save_steps'],
            eval_steps=self.config['training']['eval_steps'],
            save_total_limit=self.config['training']['save_total_limit'],
            fp16=self.config['training']['fp16'],
            bf16=self.config['training']['bf16'],
            dataloader_num_workers=self.config['training']['dataloader_num_workers'],
            seed=self.config['training']['seed'],
            report_to=self.config['training']['report_to'],
            run_name=self.config['training']['run_name'],
            evaluation_strategy=self.config['evaluation']['eval_strategy'],
            load_best_model_at_end=self.config['evaluation']['load_best_model_at_end'],
            metric_for_best_model=self.config['evaluation']['metric_for_best_model'],
            greater_is_better=self.config['evaluation']['greater_is_better']
        )
        
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.tokenized_dataset['train'],
            eval_dataset=self.tokenized_dataset['validation']
        )
        
        # Train
        self.trainer.train()
        
        # Save
        self.trainer.save_model()
        self.tokenizer.save_pretrained(self.config['training']['output_dir'])
        
        print(f"Training complete. Model saved to {self.config['training']['output_dir']}")
        
    def run(self):
        """Run full training pipeline."""
        self.load_model()
        self.tokenized_dataset = self.load_dataset()
        self.train()

def main():
    """Main entry point."""
    import yaml
    
    # Load config
    config_path = "configs/dapt_qwen3_8b.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Create trainer
    trainer = DAPTTrainer(config)
    
    # Run training
    trainer.run()

if __name__ == '__main__':
    main()
