"""Collect auditable evidence that MindSpore is using the requested Ascend device."""

import json
import subprocess


def main() -> None:
    import mindspore as ms

    ms.set_context(device_target="Ascend")
    device_target = ms.get_context("device_target")
    npu = subprocess.run(
        ["npu-smi", "info"], check=False, capture_output=True, text=True, timeout=15
    )
    evidence = {
        "mindspore_version": ms.__version__,
        "device_target": device_target,
        "npu_smi_exit_code": npu.returncode,
        "npu_smi_excerpt": npu.stdout[:4000],
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if device_target != "Ascend" or npu.returncode != 0:
        raise SystemExit("Ascend verification failed; refusing acceptance run")


if __name__ == "__main__":
    main()
