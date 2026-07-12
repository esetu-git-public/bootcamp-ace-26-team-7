import os, sys, platform, subprocess, json, shutil

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ModuleNotFoundError:
    _PSUTIL_AVAILABLE = False
    psutil = None

try:
    import torch
    _TORCH_AVAILABLE = True
except ModuleNotFoundError:
    _TORCH_AVAILABLE = False
    torch = None


def _nvidia_smi_query():
    vals = {"gpu_util_percent": None, "gpu_temp": None, "gpu_power_w": None}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            vals["gpu_util_percent"] = float(parts[0]) if parts[0] != "[Not Supported]" else None
            vals["gpu_temp"] = float(parts[1]) if len(parts) > 1 and parts[1] != "[Not Supported]" else None
            vals["gpu_power_w"] = float(parts[2]) if len(parts) > 2 and parts[2] != "[Not Supported]" else None
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    return vals


def detect_hardware(verbose=True):
    info = {}

    if _PSUTIL_AVAILABLE:
        vm = psutil.virtual_memory()
        info["ram"] = {
            "total_gb": round(vm.total / 1e9, 1),
            "available_gb": round(vm.available / 1e9, 1),
        }
        info["cpu"] = {
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "freq_mhz": round(psutil.cpu_freq().max, 1) if psutil.cpu_freq() else None,
        }
    else:
        info["ram"] = {"total_gb": "?", "available_gb": "?"}
        info["cpu"] = {"cores_physical": "?", "cores_logical": "?"}

    if _TORCH_AVAILABLE:
        info["torch_version"] = torch.__version__
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            info["gpu"] = {
                "name": torch.cuda.get_device_name(0),
                "vram_total_gb": round(props.total_memory / 1e9, 1),
                "compute_capability": f"{props.major}.{props.minor}",
            }
        else:
            info["gpu"] = None
    else:
        info["torch_version"] = None
        info["gpu"] = None

    info["cpu"]["name"] = platform.processor() or platform.machine()
    info["cpu"]["architecture"] = platform.machine()
    info["python_version"] = platform.python_version()
    info["os"] = platform.platform()

    for label, path in [("models", "models"), ("data", "data")]:
        disk = _disk_free(path)
        if disk is not None:
            info[f"disk_{label}_free_gb"] = round(disk / 1e9, 1)
        else:
            info[f"disk_{label}_free_gb"] = None

    if verbose:
        _print_hardware(info)

    return info


def _disk_free(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return shutil.disk_usage(path).free
    except OSError:
        return None


def _print_hardware(info):
    sep = "─" * 50
    print(sep)
    print(f"  CPU:         {info['cpu']['name']}")
    print(f"  Cores:       {info['cpu']['cores_physical']} physical / {info['cpu']['cores_logical']} logical")
    if info["cpu"].get("freq_mhz"):
        print(f"  CPU Freq:    {info['cpu']['freq_mhz']} MHz")
    print(f"  Arch:        {info['cpu']['architecture']}")
    print(f"  RAM:         {info['ram']['available_gb']} / {info['ram']['total_gb']} GB available")
    if info["gpu"]:
        print(f"  GPU:         {info['gpu']['name']}")
        print(f"  VRAM:        {info['gpu']['vram_total_gb']} GB")
        print(f"  CUDA Cap:    {info['gpu']['compute_capability']}")
    else:
        print(f"  GPU:         (none / CPU only)")
    print(f"  Python:      {info['python_version']}")
    if info.get("torch_version"):
        print(f"  PyTorch:     {info['torch_version']}")
    if info.get("disk_models_free_gb"):
        print(f"  Disk (models): {info['disk_models_free_gb']} GB free")
    if info.get("disk_data_free_gb"):
        print(f"  Disk (data):   {info['disk_data_free_gb']} GB free")
    print(sep)


def get_resource_usage():
    usage = {}

    if _PSUTIL_AVAILABLE:
        usage["cpu_percent"] = psutil.cpu_percent(interval=0.3)
        usage["cpu_per_core"] = psutil.cpu_percent(interval=0.0, percpu=True)
        vm = psutil.virtual_memory()
        usage["ram_used_gb"] = round((vm.total - vm.available) / 1e9, 1)
        usage["ram_total_gb"] = round(vm.total / 1e9, 1)
        usage["ram_percent"] = vm.percent
    else:
        usage["cpu_percent"] = None
        usage["ram_used_gb"] = None
        usage["ram_total_gb"] = None
        usage["ram_percent"] = None

    usage["gpu_mem_used_gb"] = None
    usage["gpu_mem_total_gb"] = None
    usage["gpu_mem_percent"] = None
    usage["gpu_util_percent"] = None
    usage["gpu_temp"] = None

    if _TORCH_AVAILABLE and torch.cuda.is_available():
        usage["gpu_mem_allocated_gb"] = round(torch.cuda.memory_allocated(0) / 1e9, 1)
        usage["gpu_mem_reserved_gb"] = round(torch.cuda.memory_reserved(0) / 1e9, 1)
        total = torch.cuda.get_device_properties(0).total_memory
        usage["gpu_mem_total_gb"] = round(total / 1e9, 1)
        if total > 0:
            usage["gpu_mem_percent"] = round(torch.cuda.memory_allocated(0) / total * 100, 1)
        ns = _nvidia_smi_query()
        usage["gpu_util_percent"] = ns["gpu_util_percent"]
        usage["gpu_temp"] = ns["gpu_temp"]
        usage["gpu_power_w"] = ns["gpu_power_w"]

    return usage


def format_resource_usage(usage, compact=True):
    parts = []
    if usage["cpu_percent"] is not None:
        parts.append(f"CPU {usage['cpu_percent']:.1f}%")
    if usage["ram_used_gb"] is not None and usage["ram_total_gb"] is not None:
        parts.append(f"RAM {usage['ram_used_gb']}/{usage['ram_total_gb']} GB ({usage['ram_percent']}%)")
    if usage["gpu_mem_total_gb"] is not None and usage["gpu_mem_allocated_gb"] is not None:
        gpu_line = f"GPU {usage['gpu_mem_allocated_gb']}/{usage['gpu_mem_total_gb']} GB"
        if usage["gpu_mem_percent"] is not None:
            gpu_line += f" ({usage['gpu_mem_percent']}%)"
        if usage["gpu_util_percent"] is not None:
            gpu_line += f" util {usage['gpu_util_percent']}%"
        if usage["gpu_temp"] is not None:
            gpu_line += f" {usage['gpu_temp']}°C"
        parts.append(gpu_line)
    return " | ".join(parts) if parts else "(resource data unavailable)"


def print_resource_usage():
    usage = get_resource_usage()
    line = format_resource_usage(usage)
    print(f"[System] {line}")


def auto_monitor():
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if ip is not None:
            def _hook(info):
                print_resource_usage()
            ip.events.register("post_run_cell", _hook)
            print("Resource monitor active — hardware stats shown after every cell.")
    except (ImportError, Exception):
        print("Resource monitor requires IPython / Jupyter. Skipping auto hook.")
