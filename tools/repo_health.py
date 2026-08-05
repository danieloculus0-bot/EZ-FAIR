from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_FILES = [
    'ez_fai_builder.py',
    'ez_fair.py',
    'ez_fair_enhancements.py',
    'fai_template_writer.py',
    'form_profiles.py',
    'gdt_control_candidates.py',
    'local_test_runner.py',
    'requirements.txt',
    'run_local_test.ps1',
    '.github/workflows/test.yml',
]


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f'Missing required files: {missing}')

    for module_name in [
        'ez_fai_builder',
        'ez_fair_enhancements',
        'fai_template_writer',
        'form_profiles',
        'gdt_control_candidates',
        'local_test_runner',
    ]:
        importlib.import_module(module_name)

    print('EZ-FAIR repo health check passed')


if __name__ == '__main__':
    main()
