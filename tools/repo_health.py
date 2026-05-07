from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    'ez_fai_builder.py',
    'local_test_runner.py',
    'requirements.txt',
    'run_local_test.ps1',
    '.github/workflows/test.yml',
]


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f'Missing required files: {missing}')

    for module_name in ['ez_fai_builder', 'local_test_runner']:
        importlib.import_module(module_name)

    print('EZ-FAIR repo health check passed')


if __name__ == '__main__':
    main()
