
from typing import Dict, Any

class ModelDialect:
    """
    L5 Adaptation: Translates generic prompt requirements into model-specific 'dialects' 
    to maximize attention and instruction following.
    """
    
    @staticmethod
    def wrap_instruction(model_name: str, instruction: str) -> str:
        model_name = model_name.lower()
        
        if "claude" in model_name:
            # Claude 3.x loves XML structure for clear grounding
            return f"<instruction>\n{instruction}\n</instruction>\n<thinking_process>\nThink step-by-step before answering.\n</thinking_process>"
        
        if "deepseek" in model_name:
            # DeepSeek V3/Reasoner prefers explicit structural markers and CoT
            return f"### INSTRUCTION\n{instruction}\n### REASONING\nProvide a detailed logical trace before the final answer."
            
        if "gemini" in model_name:
            # Gemini focuses on long context, benefits from repeated anchoring
            return f"OBJECTIVE: {instruction}\n\n[REITERATION]: Your task is to fulfill the OBJECTIVE above by analyzing the context provided."
            
        # Default: Markdown standard
        return f"**Instruction**: {instruction}"

    @staticmethod
    def get_output_format_hook(model_name: str) -> str:
        model_name = model_name.lower()
        if "claude" in model_name:
            return "Respond only with a valid JSON object wrapped in <json></json> tags."
        return "Respond only with a valid JSON object."

model_dialect = ModelDialect()
