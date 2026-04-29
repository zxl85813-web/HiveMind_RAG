"""Make the repo-root ``scripts._export`` package importable from this test
package.

The ``backend/scripts/`` directory shadows the repo-root ``scripts/`` on
``sys.path`` when pytest is invoked from ``backend/``. We insert the repo root
at index 0 so ``scripts._export`` (which only exists under the repo root) wins
during attribute resolution while ``backend/scripts/export_openapi.py`` keeps
working for the rest of the suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
