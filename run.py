"""One-command entrypoint; a fresh clone uses independent demonstration fixtures."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if '--dataset' in sys.argv:
    index = sys.argv.index('--dataset')
    if len(sys.argv) <= index + 1:
        raise SystemExit('Usage: python run.py --dataset path/to/career_quest_dataset.zip')
    from scripts.import_dataset import extract
    extract(sys.argv[index + 1])
    del sys.argv[index:index + 2]

if not (ROOT / 'data' / 'employees.json').exists():
    from examples.demo import write
    write(ROOT)
    print('Using independent demo fixtures. For organizer data, see README.md.')

from server import main
main()
