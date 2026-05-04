from typing import Any
from ..state import BuilderState
from .template import template_search_node
from .interview import interview_node

async def context_injection_node(state: BuilderState) -> dict[str, Any]:
    """Inject existing KBs, graphs, and system context."""
    return {}

from .guardian import scope_guardian_node

from .testset import testset_creation_node
from .eval_preview import eval_preview_node
from .confirm import confirm_node

from .generator import generate_config_node
