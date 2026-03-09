"""
Redactors — Implementing various text masking strategies.
"""

import hashlib
from enum import Enum


class RedactionAction(str, Enum):
    MASK = "mask"  # e.g., 138****1234
    STAR = "star"  # e.g., ***********
    PLACEHOLDER = "placeholder"  # e.g., [PHONE]
    HASH = "hash"  # sha256
    DELETE = "delete"  # remove from text completely
    REPLACE = "replace"  # custom replacement


class Redactor:
    """Strategy to redact detected sensitive items."""

    @staticmethod
    def apply(action: str, original_text: str, detector_type: str = "") -> str:
        """Applies the specified redaction action to the original text."""

        if action == RedactionAction.STAR:
            return "*" * len(original_text)

        elif action == RedactionAction.PLACEHOLDER:
            upper_type = detector_type.upper() if detector_type else "REDACTED"
            return f"[{upper_type}]"

        elif action == RedactionAction.DELETE:
            return ""

        elif action == RedactionAction.HASH:
            return hashlib.sha256(original_text.encode("utf-8")).hexdigest()[:16]  # Short-hash

        elif action == RedactionAction.MASK:
            # Smart masking
            l = len(original_text)
            if l <= 4:
                return "*" * l
            elif 4 < l <= 8:  # Like API keys 'abcd123' -> ab***23
                return original_text[:2] + "*" * (l - 4) + original_text[-2:]
            elif l == 11:  # Like phone '13812345678' -> 138****5678
                return original_text[:3] + "****" + original_text[-4:]
            elif l == 18:  # Like ID Card -> 110105********1234
                return original_text[:6] + "********" + original_text[-4:]
            else:
                # Default for long strings (like bank cards)
                suffix_len = 4
                prefix_len = min(6, l // 3)
                mask_len = l - suffix_len - prefix_len
                return original_text[:prefix_len] + "*" * mask_len + original_text[-suffix_len:]

        # Default replace
        return "[REDACTED]"
