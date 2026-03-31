from __future__ import annotations

import subprocess
import sys


def run_step(label: str, command: list[str]) -> int:
    print(f"[quality] {label}: {' '.join(command)}")
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print(f"[quality] FAILED: {label} (exit {completed.returncode})")
        return completed.returncode
    print(f"[quality] PASSED: {label}")
    return 0


def main() -> int:
    compile_exit = run_step("compile sanity", [sys.executable, "-m", "compileall", "src", "tests", "scripts"])
    if compile_exit != 0:
        return compile_exit

    test_exit = run_step("pytest", [sys.executable, "-m", "pytest", "tests"])
    if test_exit != 0:
        return test_exit

    print("[quality] All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
