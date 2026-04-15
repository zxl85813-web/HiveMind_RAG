
import math
from typing import List, Any
import numpy as np

def calculate_mrr(relevant_indices: List[int]) -> float:
    """
    Mean Reciprocal Rank: inverse of the rank of the first relevant document.
    """
    if not relevant_indices:
        return 0.0
    return 1.0 / (relevant_indices[0] + 1)

def calculate_precision_at_k(relevant_indices: List[int], k: int) -> float:
    """
    Precision@K: proportion of relevant chunks in the top K results.
    """
    if k <= 0:
        return 0.0
    hits = [i for i in relevant_indices if i < k]
    return len(hits) / k

def calculate_recall_at_k(relevant_indices: List[int], total_relevant: int, k: int) -> float:
    """
    Recall@K: proportion of total relevant chunks found in the top K results.
    """
    if total_relevant <= 0:
        return 0.0
    hits = [i for i in relevant_indices if i < k]
    return len(hits) / total_relevant

def calculate_hit_rate(relevant_indices: List[int], k: int) -> float:
    """
    Hit Rate@K: 1 if any relevant chunk is in top K, else 0.
    """
    hits = [i for i in relevant_indices if i < k]
    return 1.0 if hits else 0.0

def calculate_dcg(relevances: List[int], k: int) -> float:
    """
    Discounted Cumulative Gain (standard formula).
    """
    dcg = 0.0
    for i in range(min(len(relevances), k)):
        rel = relevances[i]
        dcg += (2**rel - 1) / math.log2(i + 2)
    return dcg

def calculate_ndcg(actual_relevances: List[int], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain.
    actual_relevances: list of relevance scores (e.g., [1, 0, 1] for binary)
    """
    dcg = calculate_dcg(actual_relevances, k)
    # Ideal DCG: sorted relevances descending
    ideal_relevances = sorted(actual_relevances, reverse=True)
    idcg = calculate_dcg(ideal_relevances, k)
    
    if idcg == 0:
        return 0.0
    return dcg / idcg

def calculate_noise_ratio(chunk_relevancy_mask: List[bool]) -> float:
    """
    Calculates the ratio of non-relevant (noise) chunks to total chunks.
    """
    if not chunk_relevancy_mask:
        return 0.0
    noise_count = sum(1 for is_rel in chunk_relevancy_mask if not is_rel)
    return noise_count / len(chunk_relevancy_mask)

# For Generator Metrics (Aggregations)
def calculate_faithfulness_nli(supported_claims: int, total_claims: int) -> float:
    if total_claims == 0:
        return 1.0 # Vacuously true if no claims
    return supported_claims / total_claims
