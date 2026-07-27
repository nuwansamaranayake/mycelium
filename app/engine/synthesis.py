"""Grounded answer synthesis: the LLM writes sentences, deterministic code audits citations.

The model receives only ACL-filtered, already-retrieved passages and must return every
sentence with the passage ids that support it (strict JSON schema through the groundwork
gateway). Deterministic post-checks — never the model — decide groundedness: a sentence
citing nothing, or citing an id outside the retrieved set, is marked ungrounded and counted,
never silently dropped. Key-gating (503 without OPENROUTER_API_KEY) lives in the route;
retrieval itself is the keyless product.
"""
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

SYNTHESIS_SCHEMA = {
    "name": "grounded_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "sentences": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "passage_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["text", "passage_ids"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["sentences"],
        "additionalProperties": False,
    },
}


class CompletesJson(Protocol):
    def complete(self, *, model: str, messages: list[dict],
                 json_schema: dict | None = None, temperature: float = 0.0): ...


class EmptySynthesisError(RuntimeError):
    """The model returned zero sentences: a total synthesis failure. Recording it would
    produce an empty answer with ungrounded_count=0 — the same machine-readable
    'perfectly grounded' signal as a fully cited answer. Fail loud instead."""


class AnswerSentence(BaseModel):
    text: str
    passage_ids: list[str]
    grounded: bool


class GroundedAnswer(BaseModel):
    sentences: list[AnswerSentence]
    ungrounded_count: int

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.sentences)


def synthesize(
    gateway: CompletesJson,
    model: str,
    question: str,
    passages: list[dict],
) -> GroundedAnswer:
    """passages: [{passage_id, text, freshness_label}] — the retrieved, ACL-filtered set."""
    if not model:
        raise RuntimeError("LLM_MODEL_REASONING is not set. Refusing to guess a model.")
    if not passages:
        raise ValueError("no retrieved passages to synthesize from")
    context = "\n\n".join(
        f"[{p['passage_id']}] (freshness: {p['freshness_label']})\n{p['text']}"
        for p in passages)
    result = gateway.complete(
        model=model,
        messages=[
            {"role": "system",
             "content": ("Answer the question using ONLY the passages provided. Return one "
                         "entry per sentence of your answer, each with passage_ids listing "
                         "the bracketed passage ids that support that exact sentence. Every "
                         "sentence must cite at least one passage id. If the passages do not "
                         "contain the answer, say so in one sentence citing the closest "
                         "passage. Never use knowledge outside the passages. Return JSON.")},
            {"role": "user", "content": f"Question: {question}\n\nPassages:\n{context}"},
        ],
        json_schema=SYNTHESIS_SCHEMA,
    )
    if isinstance(result, list):  # envelope quirk seen live on some providers (see FAILURES)
        result = {"sentences": result}
    valid_ids = {p["passage_id"] for p in passages}
    items = result.get("sentences", [])
    if not items:
        raise EmptySynthesisError(
            "synthesis returned no sentences; refusing to record an empty answer "
            "as perfectly grounded")
    sentences: list[AnswerSentence] = []
    ungrounded = 0
    for item in items:
        cited = [str(pid) for pid in item["passage_ids"]]
        grounded = bool(cited) and all(pid in valid_ids for pid in cited)
        if not grounded:
            ungrounded += 1
        sentences.append(AnswerSentence(text=item["text"], passage_ids=cited,
                                        grounded=grounded))
    return GroundedAnswer(sentences=sentences, ungrounded_count=ungrounded)
