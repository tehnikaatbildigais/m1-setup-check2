"""MI-1 · mijiedarbības kopsavilkums un nākamā soļa ieteikums.

Funkcijas līgums: `kopsavilkums(teksts) -> Suggestion(kopsavilkums, solis, avots, piezīme)`.
Bez `ANTHROPIC_API_KEY` darbojas atslēgvārdu imitācija. Ar atslēgu izmanto Claude;
kļūdas, noildzes vai atteikuma gadījumā atgriežas pie imitācijas.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger("app.crm.ai")

MODEL = "claude-opus-5-5"
MAX_SENTENCES = 3
MAX_INPUT_CHARS = 8000

SYSTEM_PROMPT = (
    "Tu palīdzi iestādes darbiniekam CRM sistēmā. No darbinieka piezīmēm par sarunu ar "
    "organizāciju uzraksti kopsavilkumu latviešu valodā, ne vairāk kā trīs teikumos, un "
    "vienu konkrētu nākamo soli darbiniekam. Raksti tikai faktus no piezīmēm; neizdomā "
    "vārdus, datumus vai solījumus. Neiekļauj personas kodus, tālruņus vai adreses."
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "next_step": {"type": "string"},
    },
    "required": ["summary", "next_step"],
    "additionalProperties": False,
}

KEYWORD_STEPS = [
    ("piedāvājum", "Sagatavot un nosūtīt piedāvājumu."),
    ("seminār", "Nosūtīt semināra programmu un reģistrācijas informāciju."),
    ("līgum", "Sagatavot līguma projektu un nosūtīt saskaņošanai."),
    ("konsultācij", "Vienoties par konsultācijas laiku."),
    ("sanāksm", "Vienoties par nākamās sanāksmes laiku."),
    ("tikšanās", "Vienoties par nākamās tikšanās laiku."),
    ("materiāl", "Nosūtīt pieprasītos materiālus."),
    ("zvan", "Piezvanīt kontaktpersonai un precizēt atvērtos jautājumus."),
]
DEFAULT_STEP = "Sazināties ar kontaktpersonu un vienoties par nākamo soli."

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Suggestion:
    summary: str
    next_step: str
    source: str  # "imitācija" vai "Claude"
    notice: str = ""


def _limit_sentences(text: str) -> str:
    sentences = [s.strip() for s in SENTENCE_END.split(text.strip()) if s.strip()]
    return " ".join(sentences[:MAX_SENTENCES])


def imitation(text: str) -> Suggestion:
    summary = _limit_sentences(" ".join(text.split()))
    lowered = text.casefold()
    step = next((s for word, s in KEYWORD_STEPS if word in lowered), DEFAULT_STEP)
    return Suggestion(summary, step, "imitācija")


def _claude(text: str) -> Suggestion:
    import anthropic  # Importē tikai tad, ja ir atslēga.

    client = anthropic.Anthropic(timeout=30.0, max_retries=1)
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text[:MAX_INPUT_CHARS]}],
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("refusal")
    payload = json.loads(next(b.text for b in response.content if b.type == "text"))
    return Suggestion(
        _limit_sentences(payload["summary"]), payload["next_step"].strip(), "Claude"
    )


def kopsavilkums(text: str) -> Suggestion:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return imitation(text)
    try:
        return _claude(text)
    except Exception as exc:  # tīkls, noildze, API kļūda, atteikums vai nederīgs JSON
        # Piezīmēs var būt personas dati, tāpēc žurnālā tikai kļūdas tips.
        logger.warning("Claude nav pieejams (%s); izmantota imitācija", type(exc).__name__)
        suggestion = imitation(text)
        return Suggestion(
            suggestion.summary,
            suggestion.next_step,
            suggestion.source,
            "Claude šobrīd nav pieejams, tāpēc izmantota imitācija.",
        )
