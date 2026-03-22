# scripts/check_gpu.py
import subprocess
import sys

print("=== 1. NVIDIA Driver ===")
result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
if result.returncode == 0:
    print(result.stdout[:500])
else:
    print("nvidia-smi 未找到，請先安裝 NVIDIA 驅動")
    sys.exit(1)

print("\n=== 2. PyTorch CUDA Info ===")
import torch
print(f"torch version: {torch.__version__}")
print(f"torch.version.cuda: {torch.version.cuda}")
print(f"torch.cuda.is_available(): {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("GPU 不可用，需要重新安裝 CUDA 版本的 PyTorch")