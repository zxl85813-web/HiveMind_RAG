"""
Detectors Framework — For finding sensitive information in text.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type
import re
from dataclasses import dataclass


@dataclass
class DetectedItem:
    detector_type: str
    original_text: str
    start_index: int
    end_index: int


class BaseDetector(ABC):
    """Base class for all sensitive data detectors."""
    
    detector_type: str = "base"
    
    @abstractmethod
    def detect(self, text: str) -> List[DetectedItem]:
        """Detect sensitive items in the given text."""
        return []


class RegexDetector(BaseDetector):
    """Detector based on a specific regex pattern."""
    
    def __init__(self, pattern: str, detector_type: str):
        self.pattern = re.compile(pattern)
        self.detector_type = detector_type
        
    def detect(self, text: str) -> List[DetectedItem]:
        items = []
        for match in self.pattern.finditer(text):
            items.append(
                DetectedItem(
                    detector_type=self.detector_type,
                    original_text=match.group(),
                    start_index=match.start(),
                    end_index=match.end()
                )
            )
        return items


class PhoneDetector(RegexDetector):
    """Detects Chinese mobile phone numbers."""
    def __init__(self):
        # Starts with 13-19, total 11 digits
        super().__init__(r'(?<!\d)1[3-9]\d{9}(?!\d)', "phone")


class IDCardDetector(RegexDetector):
    """Detects Chinese ID Card numbers (18 digits, last can be X)."""
    def __init__(self):
        super().__init__(r'(?<!\d)[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])([0-2][1-9]|10|20|30|31)\d{3}[0-9Xx](?!\d)', "id_card")


class EmailDetector(RegexDetector):
    """Detects email addresses."""
    def __init__(self):
        super().__init__(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "email")


class APIKeyDetector(RegexDetector):
    """Detects common API keys or tokens (Heuristic: high entropy 20-40 chars like sk-xxx)."""
    def __init__(self):
        # Currently a simple regex for typical keys like OpenAI (sk-xxxx), GitHub (ghp_xxxx)
        super().__init__(r'(sk-[a-zA-Z0-9]{20,60}|ghp_[a-zA-Z0-9]{36}|Bearer\s+[a-zA-Z0-9\-\._~+\/]+=*)', "api_key")


class BankCardDetector(RegexDetector):
    """Detects Bank Card Numbers (usually 16 or 19 digits)."""
    def __init__(self):
        super().__init__(r'(?<!\d)[456]\d{15,18}(?!\d)', "bank_card")


class IPDetector(RegexDetector):
    """Detects IPv4 addresses."""
    def __init__(self):
        super().__init__(r'(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)', "ip_address")


class MACDetector(RegexDetector):
    """Detects MAC addresses (standard colon or hyphen separated)."""
    def __init__(self):
        super().__init__(r'(?i)(?<![0-9A-F])(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}(?![0-9A-F])', "mac_address")


class PassportDetector(RegexDetector):
    """Detects Chinese Passport numbers (starts with D, E, G, P, etc. followed by digits)."""
    def __init__(self):
        super().__init__(r'(?<![A-Z0-9])[DEGKP]\d{7,8}(?![A-Z0-9])', "passport")


class DetectorRegistry:
    """Registry to hold and retrieve available detectors."""
    
    _detectors: Dict[str, BaseDetector] = {}
    
    @classmethod
    def register(cls, detector: BaseDetector):
        cls._detectors[detector.detector_type] = detector
        
    @classmethod
    def get_detector(cls, detector_type: str) -> BaseDetector | None:
        return cls._detectors.get(detector_type)
        
    @classmethod
    def get_all(cls) -> Dict[str, BaseDetector]:
        return cls._detectors


# Auto-register built-in detectors
DetectorRegistry.register(PhoneDetector())
DetectorRegistry.register(IDCardDetector())
DetectorRegistry.register(EmailDetector())
DetectorRegistry.register(APIKeyDetector())
DetectorRegistry.register(BankCardDetector())
DetectorRegistry.register(IPDetector())
DetectorRegistry.register(MACDetector())
DetectorRegistry.register(PassportDetector())
