"""
Desensitization Engine — Orchestrates detection and redaction based on policy.
"""
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import json
from loguru import logger

from .detectors import DetectorRegistry, DetectedItem, RegexDetector
from .redactors import Redactor


class DesensitizationEngine:
    """Core engine for detecting and redacting sensitive data based on policy rules."""
    
    @staticmethod
    def process_text(text: str, policy_rules: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Processes text using the provided rules.
        
        Args:
            text: The original text to process.
            policy_rules: Dictionary mapping detector_type to options (e.g., {"phone": {"action": "mask", "whitelist": []}})
                         Or a legacy flat dict mapping to actions.
            
        Returns:
            Tuple of (redacted_text, list of applied_item_records)
        """
        if not text or not policy_rules:
            return text, []
            
        # Standardize policy_rules format
        structured_rules = {}
        for k, v in policy_rules.items():
            if isinstance(v, str):
                structured_rules[k] = {"action": v, "whitelist": [], "severity": "medium"}
            else:
                structured_rules[k] = v

        # 1. Detect all items based on policy rules
        all_detected_items: List[DetectedItem] = []
        for detector_type, options in structured_rules.items():
            # Handle custom regex patterns if provided
            if detector_type == "custom_regex" and isinstance(options, list):
                for custom_rule in options:
                    pattern = custom_rule.get("pattern")
                    if not pattern:
                        continue
                    name = custom_rule.get("name", "custom")
                    try:
                        regex_det = RegexDetector(pattern, name)
                        items = regex_det.detect(text)
                        
                        # Apply Whitelist for custom
                        whitelist = custom_rule.get("whitelist", [])
                        if whitelist:
                            items = [it for it in items if it.original_text not in whitelist]
                        
                        # We need to map the action/severity for these custom items
                        # Since we want to reuse the same loop logic later, 
                        # we'll store the rule info in a way the loop can find it
                        # but custom rules are unique. 
                        # Actually, better to just detect and tag them.
                        for it in items:
                            # We'll hijack detector_type temporarily to point back to the rule
                            # Or just add attributes to DetectedItem? DetectedItem is a dataclass.
                            # Let's just use a special prefix for custom ones in structured_rules
                            custom_key = f"__custom_{name}"
                            it.detector_type = custom_key
                            structured_rules[custom_key] = custom_rule
                            all_detected_items.append(it)
                    except Exception as e:
                        logger.error(f"Invalid custom regex '{pattern}': {e}")
                continue

            detector = DetectorRegistry.get_detector(detector_type)
            if detector:
                items = detector.detect(text)
                
                # Apply Whitelist Filter
                whitelist = options.get("whitelist", [])
                if whitelist:
                    items = [it for it in items if it.original_text not in whitelist]
                    
                all_detected_items.extend(items)
                
        if not all_detected_items:
            return text, []

        # 2. Sort items by start_index, handle overlaps
        all_detected_items.sort(key=lambda x: (x.start_index, -(x.end_index - x.start_index)))
        
        filtered_items = []
        last_end = -1
        for item in all_detected_items:
            if item.start_index >= last_end:
                filtered_items.append(item)
                last_end = item.end_index

        # 3. Apply redactions from end to start
        filtered_items.sort(key=lambda x: x.start_index, reverse=True)
        
        redacted_text = text
        applied_records = []
        
        for item in filtered_items:
            options = structured_rules.get(item.detector_type, {"action": "mask"})
            action = options.get("action", "mask")
            redacted_value = Redactor.apply(action, item.original_text, item.detector_type)
            
            # Record what we did
            preview_len = min(6, len(item.original_text))
            record = {
                "detector_type": item.detector_type,
                "original_text_preview": item.original_text[:preview_len] + "..." if len(item.original_text) > preview_len else item.original_text,
                "redacted_text": redacted_value,
                "start_index": item.start_index,
                "end_index": item.end_index,
                "action_taken": action,
                "severity": options.get("severity", "medium")
            }
            applied_records.append(record)
            
            # Substitute in text
            redacted_text = redacted_text[:item.start_index] + redacted_value + redacted_text[item.end_index:]
            
        applied_records.reverse()
        return redacted_text, applied_records

