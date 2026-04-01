from loguru import logger


class VirtualSegmenter:
    """
    Utility to inject structural landmarks into a massive single-block context.
    Helps LLMs navigate long text in RAG scenarios.
    """

    @staticmethod
    def inject_markers(text: str, chunk_chars: int = 2500) -> str:
        """
        Inject segment markers [SEGMENT N] into the text every chunk_chars to 
        provide the attention mechanism with structural anchors.
        """
        if len(text) < chunk_chars * 1.5:
            return text

        logger.info(f"🧬 [VirtualSegmenter] Injecting markers into {len(text)} characters of context.")

        # Split into roughly equal parts at newline boundaries if possible
        parts = []
        current_pos = 0
        seg_num = 1

        while current_pos < len(text):
            # Try to find a good split point (newline) near chunk_chars
            next_pos = current_pos + chunk_chars
            if next_pos < len(text):
                # Look for the nearest double newline to keep paragraphs intact
                split_point = text.rfind("\n\n", current_pos, next_pos + 500)
                if split_point == -1 or split_point < current_pos + chunk_chars // 2:
                    # Fallback to single newline
                    split_point = text.find("\n", next_pos)
                    if split_point == -1 or split_point > next_pos + 1000:
                        split_point = next_pos

                segment = text[current_pos:split_point]
                parts.append(f"--- [LANDMARK SEGMENT {seg_num}] ---\n{segment}\n--- [END SEGMENT {seg_num}] ---")
                current_pos = split_point
                seg_num += 1
            else:
                segment = text[current_pos:]
                parts.append(f"--- [LANDMARK SEGMENT {seg_num}] ---\n{segment}\n--- [END SEGMENT {seg_num}] ---")
                break

        return "\n\n".join(parts)

    @staticmethod
    def detect_failure_cause(query: str, response: str, context: str) -> str | None:
        """
        Heuristically check if a failure was caused by 'Lost in the Middle' 
        rather than total total missing information.
        """
        resp_lower = response.lower()

        # Signals that the model couldn't find the info
        negative_signals = ["i found no information", "not in the context", "is not mentioned", "没找到", "没有提及"]

        if any(sig in resp_lower for sig in negative_signals):
            # If the context is very large but the response is negative, it's likely a context failure
            if len(context) > 8000:
                return "lost_in_middle_likely"

        return None
