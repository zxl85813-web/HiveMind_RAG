"""Quote-intelligence service package.

Pipeline: fetch -> mask (reversible) -> top-N -> LLM analysis -> unmask.

Public surface:
    - TokenVault             : reversible PII masking
    - QuoteIntelligenceService : end-to-end orchestrator
"""
from .vault import TokenVault
from .service import QuoteIntelligenceService

__all__ = ["TokenVault", "QuoteIntelligenceService"]
