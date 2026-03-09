import hashlib
import re
from typing import Any

from app.audit.security.detectors import DetectorRegistry


class AuditEngine:
    """Engine for performing automatic data quality audits (M2.3)."""

    @staticmethod
    def calculate_hash(text: str) -> str:
        """Calculates SHA-256 hash of text for deduplication."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def audit_text(resource_data: dict[str, Any]) -> dict[str, Any]:
        """
        Analyzes a StandardizedResource for quality metrics.
        Returns a dictionary of scores and status.
        """
        text = resource_data.get("raw_text", "")
        filename = resource_data.get("meta", {}).get("filename", "")

        if not text or not text.strip():
            return {
                "quality_score": 0.0,
                "content_length_ok": False,
                "duplicate_ratio": 0.0,
                "garble_ratio": 0.0,
                "blank_ratio": 1.0,
                "format_integrity_ok": False,
                "pii_count": 0,
                "status": "rejected",
                "message": "Empty content",
            }

        text_len = len(text)

        # 1. Content Length (Requirement: >= 100 chars)
        content_length_ok = text_len >= 100

        # 2. Blank Ratio (White space / Total)
        whitespace_count = len(re.findall(r"\s", text))
        blank_ratio = whitespace_count / text_len if text_len > 0 else 1.0

        # 3. Garble Ratio (Non-printable characters or unusual encoding artifacts)
        # We look for a high density of non-printable chars or sequences typical of failed OCR/Parsing
        garbled_chars = len([c for c in text if not c.isprintable() and not c.isspace()])
        garble_ratio = garbled_chars / text_len if text_len > 0 else 0.0

        # 4. Duplicate Ratio (Strict block-based duplication check)
        block_size = 50
        blocks = [text[i : i + block_size] for i in range(0, text_len, block_size)]
        if blocks:
            unique_blocks = len(set(blocks))
            duplicate_ratio = (len(blocks) - unique_blocks) / len(blocks)
        else:
            duplicate_ratio = 0.0

        # 5. Format Integrity Check (M2.1D)
        # Check if the parser produced structured artifacts suitable for its type
        sections = resource_data.get("sections", [])
        tables = resource_data.get("tables", [])
        format_integrity_ok = True
        integrity_issues = []

        lower_filename = filename.lower()
        if lower_filename.endswith((".pdf", ".docx")):
            if not sections:
                format_integrity_ok = False
                integrity_issues.append("No layout sections extracted (PDF/Word)")
        elif lower_filename.endswith((".xlsx", ".xls", ".csv")) and not tables:
            format_integrity_ok = False
            integrity_issues.append("No tables extracted (Excel/CSV)")

        # 6. PII Sensitivity Detection
        pii_items = []
        for detector_type in DetectorRegistry.get_all():
            detector = DetectorRegistry.get_detector(detector_type)
            if detector:
                found = detector.detect(text)
                pii_items.extend(found)

        pii_count = len(pii_items)
        pii_density = (pii_count / text_len) * 1000 if text_len > 0 else 0

        # 7. Composite Quality Score
        score = 1.0
        issues = []

        if not content_length_ok:
            score -= 0.4
            issues.append(f"Content too short ({text_len} chars)")

        if duplicate_ratio > 0.3:
            penalty = (duplicate_ratio - 0.3) * 1.5
            score -= penalty
            issues.append(f"High duplication ({duplicate_ratio:.1%})")

        if garble_ratio > 0.05:
            penalty = garble_ratio * 10
            score -= penalty
            issues.append(f"High garble ratio ({garble_ratio:.1%})")

        if blank_ratio > 0.4:
            penalty = blank_ratio - 0.4
            score -= penalty
            issues.append(f"Too much whitespace ({blank_ratio:.1%})")

        if not format_integrity_ok:
            score -= 0.3
            issues.extend(integrity_issues)

        # PII Threshold
        is_sensitive = pii_density > 5.0
        if is_sensitive:
            issues.append(f"High PII density ({pii_density:.1f}/1k chars)")

        quality_score = max(0.0, min(1.0, score))

        # 8. Status Routing (3-tier)
        if quality_score < 0.4:
            status = "rejected"
            message = "Rejected: " + "; ".join(issues)
        elif quality_score < 0.85 or is_sensitive or not format_integrity_ok:
            status = "pending"  # Needs human review
            message = "Pending Review: " + "; ".join(issues)
        else:
            status = "approved"
            message = "Auto-approved"

        return {
            "quality_score": quality_score,
            "content_length_ok": content_length_ok,
            "duplicate_ratio": duplicate_ratio,
            "garble_ratio": garble_ratio,
            "blank_ratio": blank_ratio,
            "format_integrity_ok": format_integrity_ok,
            "pii_count": pii_count,
            "status": status,
            "message": message,
            "content_hash": AuditEngine.calculate_hash(text),
        }
