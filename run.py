"""One-command entrypoint; a fresh clone uses independent demonstration fixtures."""
from server import main

if __name__ == '__main__':
    main(bootstrap=True)
