import argparse
from pathlib import Path
from ez_fai_builder import run_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    outputs = run_batch(Path(args.pdf), Path(args.template), Path(args.output_dir))
    for name, path in outputs.items():
        print(f'{name}: {path}')


if __name__ == '__main__':
    main()
