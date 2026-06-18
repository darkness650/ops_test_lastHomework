"""
Check what's in the checkpoint
"""
import torch
import numpy as np

checkpoint_path = r"d:\code\python\paper\LightLog\LogRobust\checkpoints\best_model.pth"

print(f"Loading checkpoint from {checkpoint_path}")
checkpoint = torch.load(checkpoint_path, weights_only=False)

print(f"\nCheckpoint keys: {list(checkpoint.keys())}")
print(f"\nEpoch: {checkpoint.get('epoch', 'N/A')}")
print(f"Best val F1: {checkpoint.get('best_val_f1', 'N/A')}")
print(f"Best threshold: {checkpoint.get('best_threshold', 'N/A')}")

# Check model state
model_state = checkpoint['model_state_dict']
print(f"\nModel state dict keys:")
for key in model_state.keys():
    print(f"  {key}: {model_state[key].shape}")

# Check vocab sizes
word_vocab = checkpoint['word_vocab']
template_vocab = checkpoint['template_vocab']
idf_dict = checkpoint['idf_dict']

print(f"\nWord vocab size: {len(word_vocab)}")
print(f"Template vocab size: {len(template_vocab)}")
print(f"IDF dict size: {len(idf_dict)}")

# Sample some IDF values
print(f"\nSample IDF values:")
for i, (word, idf) in enumerate(list(idf_dict.items())[:10]):
    print(f"  {word}: {idf:.4f}")
