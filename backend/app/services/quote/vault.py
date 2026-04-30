"""TokenVault — reversible PII masking with stable per-value tokens.

Why: the QuoteIntelligence agent must never ship raw customer names /
phones / emails to a third-party LLM, but the **final** report must read
naturally for the human owner. So we replace each PII value with a
deterministic placeholder like ``[CUST_001]`` before the LLM call, then
substitute the original values back into the LLM's markdown response.

Design notes:
    - Tokens are stable per *value* within a vault — repeated occurrences
      of "Alice Chen" all map to the same ``[CUST_001]`` so the LLM sees
      coherent entities.
    - Vault is a per-run object; never persisted.
    - ``unmask`` is a single-pass replace; collision-free because tokens
      use fixed prefix + zero-padded counter and never appear in source
      text.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


_TOKEN_RE = re.compile(r"\[(?:CUST|PHONE|EMAIL|COMPANY)_\d{3,}\]")


class TokenVault:
    """Reversible mask: value <-> [KIND_NNN] token."""

    __slots__ = ("_token_to_value", "_value_to_token", "_counter")

    def __init__(self) -> None:
        self._token_to_value: dict[str, str] = {}
        self._value_to_token: dict[tuple[str, str], str] = {}
        self._counter: dict[str, int] = defaultdict(int)

    # ---- mask ---------------------------------------------------------
    def mask(self, value: str | None, kind: str = "DATA") -> str:
        """Return a stable token for ``value``. Empty/None -> empty string."""
        if value is None or value == "":
            return ""
        key = (kind, value)
        existing = self._value_to_token.get(key)
        if existing:
            return existing
        self._counter[kind] += 1
        token = f"[{kind}_{self._counter[kind]:03d}]"
        self._token_to_value[token] = value
        self._value_to_token[key] = token
        return token

    def mask_quote_dict(self, quote: dict[str, Any]) -> dict[str, Any]:
        """Return a *copy* of ``quote`` with PII fields replaced by tokens.

        Operates only on the canonical PII fields used by the demo schema.
        """
        masked = dict(quote)
        if "customer_name" in masked:
            masked["customer_name"] = self.mask(masked["customer_name"], "CUST")
        if "customer_phone" in masked:
            masked["customer_phone"] = self.mask(masked["customer_phone"], "PHONE")
        if "customer_email" in masked:
            masked["customer_email"] = self.mask(masked["customer_email"], "EMAIL")
        if masked.get("customer_company"):
            masked["customer_company"] = self.mask(masked["customer_company"], "COMPANY")
        return masked

    # ---- unmask -------------------------------------------------------
    def unmask(self, text: str) -> str:
        """Substitute every recognised token back to its original value."""
        if not text:
            return text

        def _sub(m: re.Match[str]) -> str:
            tok = m.group(0)
            return self._token_to_value.get(tok, tok)

        return _TOKEN_RE.sub(_sub, text)

    # ---- introspection ------------------------------------------------
    def mapping(self) -> dict[str, str]:
        """Return a copy of the token -> value mapping (for audit/debug)."""
        return dict(self._token_to_value)

    def __len__(self) -> int:
        return len(self._token_to_value)
