"""支持 ``python -m cloudhub`` 直接调用。"""

from __future__ import annotations

import sys

from cloudhub.cli import main

if __name__ == "__main__":
    sys.exit(main())
