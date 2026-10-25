#!/usr/bin/env python3
"""Entry point behind a sandbox's ``mac``, ``user`` and ``bin/*`` launchers.

    simrun.py mac  SANDBOX [COMMAND...]
    simrun.py user SANDBOX [MESSAGE...]
    simrun.py shim SANDBOX NAME [ARGS...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv):
    if not argv or argv[0] not in ("mac", "user", "shim"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    if argv[0] == "mac":
        from sim.mac import main as run
    elif argv[0] == "user":
        from sim.user import main as run
    else:
        from sim.shim import main as run
    return run(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
