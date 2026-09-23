"""Import the organizer archive locally. Never extract arbitrary ZIP paths."""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'employees.json', 'events.json', 'skills.json', 'activity_history.csv'}


def extract(archive, root=ROOT):
    data = Path(root) / 'data'
    data.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        found = {}
        for info in source.infolist():
            name = Path(info.filename).name
            if name not in NAMES or '__MACOSX' in info.filename:
                continue
            if name in found or info.file_size > 20_000_000:
                raise ValueError('Duplicate filename or file larger than 20 MB.')
            found[name] = source.read(info)
        if set(found) != NAMES:
            raise ValueError('Archive must contain employees.json, events.json, skills.json and activity_history.csv.')
        if (Path(root) / 'runtime' / 'career.sqlite3').exists():
            raise ValueError('Existing runtime database detected. Back up and move runtime/career.sqlite3 before replacing the starter dataset.')
        for name, content in found.items():
            (data / name).write_bytes(content)
    print('Dataset imported locally. Run: python server.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        extract(args.archive)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        sys.exit(str(exc))
