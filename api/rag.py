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
    source_lines = []
    numbered = {}
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get("text", "")
        source_lines.append(f"[{i}] {text}")
        numbered[i] = chunk
    sources_str = "\n".join(source_lines)
    prompt_str = PROMPT_TEMPLATE.format(sources=sources_str, question=question)
    return prompt_str, numbered


def extract_citations(answer: str, numbered: dict[int, dict]) -> list[dict]:
    """Pull [N]-style markers from `answer` and resolve to retrieved chunks.

    Each return value is shaped {"chunk_id": int, "score": float}. Only
    indices that are present in `numbered` are returned; duplicates are
    de-duplicated.
    """
    markers = CITATION_PATTERN.findall(answer)
    citations = []
    seen_chunks = set()
    for marker in markers:
        idx = int(marker)
        if idx in numbered:
            chunk = numbered[idx]
            chunk_id = chunk.get("chunk_id")
            if chunk_id is not None and chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                additional = chunk.get("_additional") or {}
                distance = additional.get("distance", 0.0)
                score = max(0.0, min(1.0, 1.0 - distance))
                citations.append({
                    "chunk_id": chunk_id,
                    "score": score
                })
    return citations


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
    vector = embedder.encode(question).tolist()

    result = (
        weaviate_client.query
        .get("Chunk", ["text", "chunk_id"])
        .with_near_vector({"vector": vector})
        .with_additional(["distance"])
        .with_limit(k)
        .do()
    )

    chunks = result.get("data", {}).get("Get", {}).get("Chunk", [])
    if not chunks:
        return {
            "answer": SENTINEL,
            "citations": [],
            "confidence": 0.0
        }

    prompt, numbered = assemble_prompt(question, chunks)

    gen_outputs = generator(prompt, max_new_tokens=256, do_sample=False)
    raw_answer = gen_outputs[0]["generated_text"]

    citations = extract_citations(raw_answer, numbered)
    if not citations:
        return {
            "answer": SENTINEL,
            "citations": [],
            "confidence": 0.0
        }

    scores = [c["score"] for c in citations]
    confidence = sum(scores) / len(scores) if scores else 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "answer": raw_answer,
        "citations": citations,
        "confidence": confidence
    }
