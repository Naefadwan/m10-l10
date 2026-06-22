"""RAG composer — retrieve → assemble → generate → cite → grounding check.

Per the Evaluation Methodology Rule, the grounding criterion is:
`len(citations) > 0` is required when `answer` is not the empty-
retrieval sentinel. Every cited `chunk_id` must correspond to a
chunk in the top-`k` retrieved from Weaviate.

The generator call uses `do_sample=False` so retrieval and metric
reproducibility hold across runs.
"""
import re
from typing import Tuple

PROMPT_TEMPLATE = """\
You are answering a recipe question. Use ONLY the numbered sources below.
Cite each claim with the source number in square brackets, e.g. [1].
If the sources do not contain the answer, say: I cannot answer this from the available sources.

Sources:
{sources}

Question: {question}
Answer:"""

SENTINEL = "I cannot answer this from the available sources"
CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def assemble_prompt(question: str, chunks: list[dict]) -> Tuple[str, dict[int, dict]]:
    """Number the retrieved chunks 1..k and substitute into the prompt template.

    Returns (prompt_str, {citation_index: chunk_dict}).
    """
    # TODO: walk the chunks list, build numbered source lines, and call
    #       PROMPT_TEMPLATE.format(...). Return the prompt string and the
    #       index→chunk mapping. Index starts at 1, not 0.
    raise NotImplementedError


def extract_citations(answer: str, numbered: dict[int, dict]) -> list[dict]:
    """Pull [N]-style markers from `answer` and resolve to retrieved chunks.

    Each return value is shaped {"chunk_id": int, "score": float}. Only
    indices that are present in `numbered` are returned; duplicates are
    de-duplicated.
    """
    # TODO: iterate CITATION_PATTERN.finditer(answer), look up each index
    #       in `numbered`, and emit one {"chunk_id", "score"} dict per
    #       unique index that maps to a real retrieved chunk.
    raise NotImplementedError


def compose_rag(question: str, embedder, weaviate_client, generator, k: int = 4) -> dict:
    """Run the four-stage RAG pipeline.

    Returns a dict {"answer": str, "citations": list[dict], "confidence": float}.

    Grounding contract:
    - If Weaviate returns zero chunks → return SENTINEL with citations=[]
      and confidence=0.0.
    - If the generator returns text with no resolvable citation
      markers → also return SENTINEL with citations=[] and
      confidence=0.0. (This is the "refuse rather than hallucinate"
      rule the autograder enforces.)
    """
    # TODO:
    # 1. Encode `question` with `embedder` and query Weaviate via
    #    `with_near_vector` for top-k chunks (the Weaviate class is
    #    `vectorizer=none`, so `with_near_text` would fail at runtime).
    # 2. If retrieved == [], return the sentinel-shaped dict.
    # 3. assemble_prompt(question, retrieved) → (prompt, numbered).
    # 4. Run the generator with do_sample=False and max_new_tokens=256.
    # 5. extract_citations(raw, numbered).
    # 6. If no citations resolved → return the sentinel-shaped dict.
    # 7. confidence = mean(citation scores), clipped to [0, 1].
    # 8. Return {"answer": raw, "citations": citations, "confidence": confidence}.
    raise NotImplementedError
