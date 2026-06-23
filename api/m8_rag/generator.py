"""Vendored from Module 8. DO NOT MODIFY.

flan-t5-base loader. Returns a callable matching the HuggingFace
`pipeline("text2text-generation", ...)` interface — call it with the
prompt string and keyword arguments (`max_new_tokens`, `do_sample`).
"""
from typing import Optional

_cached = None


def load_generator():
    """Return the flan-t5-base text-generation callable (cached).

    Uses the model directly since ``text2text-generation`` was removed
    from ``transformers`` v5.
    """
    global _cached
    if _cached is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
        model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")

        def _generate(prompt: str, **kwargs) -> list[dict[str, str]]:
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model.generate(**inputs, **kwargs)
            text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return [{"generated_text": text}]

        _cached = _generate
    return _cached
