"""
Security Sanitizer for LLM Inputs/Outputs
"""

import re
from typing import List, Tuple
from loguru import logger

class SecuritySanitizer:
    """
    Cleans sensitive info from prompts or tool outputs to prevent data leakage.
    """
    
    # Simple regex patterns for common sensitive data
    PATTERNS = [
        (r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_MASKED]'), # Email
        (r'(?i)(api[-_]?key|secret|token)[:\s=]+[a-z0-9]{20,}', '[KEY_MASKED]'), # Generic Key
        (r'\b(sk|AIza)[-a-zA-Z0-9]{20,}\b', '[KEY_MASKED]'), # OpenAI/Google Key
        (r'Bearer\s+[a-zA-Z0-9\-\._~+/]+=*', 'Bearer [TOKEN_MASKED]'), # Auth Token
        (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD_MASKED]'), # Credit Card
    ]

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

class ToolAuditor:
    """
    Logs and audits tool calls for behavioral policy compliance.
    """
    
    FORBIDDEN_COMMANDS = ['rm -rf', 'format c:', 'drop table', 'shutdown']

    @classmethod
    def audit_tool_call(cls, tool_name: str, args: dict) -> bool:
        """
        Check if tool arguments violate safety policies.
        Returns True if SAFE, False if BLOCKED.
        """
        args_str = str(args).lower()
        
        for cmd in cls.FORBIDDEN_COMMANDS:
            if cmd in args_str:
                logger.critical(f"🛑 [Security] BLOCKED potentially dangerous tool call: {tool_name} with args {args}")
                return False
                
        return True
