from app.sdk.core.token_service import TokenService

text = "First line.\nSecond line.\nThird line."
count = TokenService.count_tokens(text)
print(f"Tokens for '{text}': {count}")

suffix = "... [Truncated due to context budget] ..."
suffix_count = TokenService.count_tokens(suffix)
print(f"Tokens for suffix: {suffix_count}")

budget = 25
result = TokenService.truncate_to_budget(text, budget)
print(f"Result for budget {budget}: '{result}'")
