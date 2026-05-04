"""
Testset Co-Creation & Eval Critic Node.
Guides the user to create a high-quality Golden Dataset (EDD).
"""
from typing import Any, List
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.core.llm_factory import get_chat_model

from ..state import BuilderState

class TestCase(BaseModel):
    question: str = Field(description="The input question or task for the agent.")
    expected_outcome: str = Field(description="The ideal ground truth response or tool usage.")
    complexity: str = Field(description="Low, Medium, or High")

class TestsetEvaluation(BaseModel):
    is_sufficient: bool = Field(description="True if we have enough high-quality test cases (min 3).")
    feedback: str = Field(description="Polite critique or instructions for the user to improve the testset.")
    new_cases_extracted: List[TestCase] = Field(default_factory=list, description="Any new test cases identified in the user message.")

TESTSET_CRITIC_PROMPT = """You are the Eval Critic for the Agent Builder Assistant. 
Your goal is to ensure the user provides a robust 'Golden Dataset' for testing their new Agent.

CURRENT GOLDEN DATASET:
{current_dataset}

LATEST USER MESSAGE:
{latest_message}

CORE AGENT GOAL:
{confirmed_fields}

### YOUR TASKS:
1. **Extract**: If the user provided a new example (question/answer pair), extract it.
2. **Evaluate**: 
   - Is the test case ambiguous? 
   - Does it directly test the core functionality of the proposed agent?
   - Is the 'expected outcome' specific enough for automated grading?
3. **Feedback**: 
   - If the cases are good, encourage the user.
   - If they are poor or missing, explain WHY and give a clear example of a good test case.
   - We need at least 3 high-quality, diverse test cases before moving to the next stage.

=== CRITICAL: QUALITY OVER QUANTITY ===
Do NOT accept 'Hello' or 'What is your name' as valid test cases. They must be task-oriented.
"""

async def testset_creation_node(state: BuilderState) -> dict[str, Any]:
    """Co-create the golden dataset (eval harness) with the user."""
    messages = state.get("messages", [])
    latest_message = messages[-1].content if messages else ""
    current_dataset = state.get("golden_dataset", [])
    confirmed_fields = state.get("confirmed_fields", {})

    llm = get_chat_model(temperature=0)
    evaluator = llm.with_structured_output(TestsetEvaluation, method="function_calling")
    
    prompt = ChatPromptTemplate.from_template(TESTSET_CRITIC_PROMPT)
    chain = prompt | evaluator
    
    result: TestsetEvaluation = await chain.ainvoke({
        "current_dataset": str(current_dataset),
        "latest_message": latest_message,
        "confirmed_fields": str(confirmed_fields)
    })
    
    # Merge new cases
    updated_dataset = list(current_dataset)
    for case in result.new_cases_extracted:
        updated_dataset.append(case.dict())
    
    # Prepare response message
    response_msg = AIMessage(content=result.feedback)
    
    # Logic for next step
    next_step = "testset_creation" # Default to staying here
    if len(updated_dataset) >= 3 and result.is_sufficient:
        next_step = "test_cases_passed"
        response_msg.content += "\n\n✅ Golden Dataset finalized. Ready for sandbox preview."
        
    return {
        "golden_dataset": updated_dataset,
        "messages": [response_msg],
        "next_step": next_step
    }
