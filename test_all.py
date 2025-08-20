#!/usr/bin/env python3
"""
Test runner for all packages in the workspace.
This avoids pytest collection conflicts between packages.
"""
import subprocess
import sys
from pathlib import Path

def run_package_tests(package_path: Path) -> int:
    """Run tests for a specific package."""
    print(f"\n{'='*60}")
    print(f"Running tests for: {package_path.name}")
    print(f"{'='*60}")
    
    if not (package_path / "tests").exists():
        print(f"No tests directory found in {package_path}")
        return 0
    
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(package_path),
                "pytest",
                str(package_path / "tests"),
                "-v",
            ],
            cwd=package_path.parent.parent,  # Run from workspace root
            check=False,
        )
        return result.returncode
    except Exception as e:
        print(f"Error running tests for {package_path}: {e}")
        return 1

def main():
    """Run all package tests."""
    workspace_root = Path(__file__).parent
    packages_dir = workspace_root / "packages"
    
    if not packages_dir.exists():
        print("No packages directory found")
        return 1
    
    failed_packages = []
    total_packages = 0
    
    for package_path in packages_dir.iterdir():
        if package_path.is_dir() and (package_path / "pyproject.toml").exists():
            total_packages += 1
            exit_code = run_package_tests(package_path)
            if exit_code != 0:
                failed_packages.append(package_path.name)
    
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total packages: {total_packages}")
    
    if failed_packages:
        print(f"Failed packages: {', '.join(failed_packages)}")
        return 1
    else:
        print("All package tests passed! ✅")
        return 0

if __name__ == "__main__":
    sys.exit(main())
