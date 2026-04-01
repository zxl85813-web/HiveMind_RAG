"""
Security Sanitizer for LLM Inputs/Outputs
"""

import re
from typing import ClassVar

from loguru import logger


class SecuritySanitizer:
    """
    Cleans sensitive info from prompts or tool outputs to prevent data leakage.
    """

    # Simple regex patterns for common sensitive data
    PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_MASKED]"),  # Email
        (r"(?i)(api[-_]?key|secret|token)[:\s=]+[a-z0-9]{20,}", "[KEY_MASKED]"),  # Generic Key
        (r"\b(sk|AIza)[-a-zA-Z0-9]{20,}\b", "[KEY_MASKED]"),  # OpenAI/Google Key
        (r"Bearer\s+[a-zA-Z0-9\-\._~+/]+=*", "Bearer [TOKEN_MASKED]"),  # Auth Token
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[CARD_MASKED]"),  # Credit Card
    ]

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Check if any sensitive data patterns match in the text."""
        if not text:
            return False

        for pattern, _ in cls.PATTERNS:
            if re.search(pattern, text):
                return True

        return False

    @classmethod
    def mask_text(cls, text: str) -> str:
        """Apply masking patterns to the text."""
        if not text:
            return text

        original = text
        for pattern, replacement in cls.PATTERNS:
            text = re.sub(pattern, replacement, text)

        if text != original:
            logger.warning("🛡️ [Security] Sensitive information masked in text.")

        return text


from typing import Any

from pydantic import BaseModel


class AuditResult(BaseModel):
    is_safe: bool = True
    requires_approval: bool = False
    message: str = ""
    error_code: str | None = None

class ToolAuditor:
    """
    CC-inspired 4-layer Security Chain.
    LAYER 1: DENY (Hard blocks by policy)
    LAYER 2: VALIDATE (Schema & Injection checks)
    LAYER 3: CHECK (Metadata-driven role check)
    LAYER 4: CAN_USE (Final dynamic approval / Consent)
    """

    DENY_PATTERNS: ClassVar[list[str]] = [
        r"rm\s+-rf\s+/",         # Root deletion
        r"format\s+c:",          # Windows disk format
        r"drop\s+database",      # DB destruction
        r"shutdown\s+-h",        # System shutdown
        r"\/etc\/shadow",        # Sensitive OS files
        r"\.env",                # Secrets
    ]

    @classmethod
    def audit_chain(
        cls,
        tool_name: str,
        args: dict,
        meta: Any = None,
        auth: Any = None
    ) -> AuditResult:
        """
        Processes the 4-layer security chain.
        """
        args_str = str(args).lower()

        # --- LAYER 1: DENY ---
        for pattern in cls.DENY_PATTERNS:
            if re.search(pattern, args_str):
                logger.critical(f"🛑 [LAYER 1] Blocked dangerous pattern in tool {tool_name}")
                return AuditResult(is_safe=False, message=f"Dangerous input pattern detected: {pattern}", error_code="SECURITY_L1_DENY")

        # --- LAYER 2: VALIDATE ---
        # Placeholder for complex AST-based injection detection (Phase 3 upgrade)
        if "script" in args and ("import os" in args["script"] or "subprocess" in args["script"]):
             # Note: python_interpreter might allow this, but we check if sandbox supports it
             pass

        # --- LAYER 3: CHECK (Metadata-driven) ---
        if meta:
            # Rule: only Admin can use non-read-only tools if enforced
            user_role = getattr(auth, "role", "guest") if auth else "guest"

            if not meta.is_read_only and user_role == "guest":
                logger.warning(f"🚫 [LAYER 3] Guest user blocked from non-read-only tool: {tool_name}")
                return AuditResult(is_safe=False, message="Permission denied: Write operations not allowed for Guest.", error_code="SECURITY_L3_ROLE")

        # --- LAYER 4: CAN_USE (Manual Consent) ---
        if meta and meta.is_destructive:
            logger.info(f"🛡️ [LAYER 4] Destructive operation {tool_name} requires user consent.")
            return AuditResult(is_safe=True, requires_approval=True, message=f"Confirm destructive action: {tool_name}")

        return AuditResult(is_safe=True)

    @classmethod
    def audit_tool_call(cls, tool_name: str, args: dict) -> bool:
        """Deprecated: use audit_chain for full protection."""
        return cls.audit_chain(tool_name, args).is_safe
