#!/usr/bin/env python3
"""Offline translation pipeline for Apographon JSON documents."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

GERMAN_TO_EN: Dict[str, str] = {
    "aus": "from",
    "der": "the",
    "die": "the",
    "das": "the",
    "den": "the",
    "dem": "the",
    "des": "the",
    "ein": "a",
    "eine": "a",
    "einer": "a",
    "durch": "through",
    "popularisierung": "popularization",
    "seines": "his",
    "lehrers": "teacher",
    "abhandlung": "treatise",
    "arzt": "physician",
    "ärzte": "physicians",
    "ärztlichen": "medical",
    "apparat": "critical apparatus",
    "asklepiades": "Asclepiades",
    "droge": "drug",
    "entwicklung": "development",
    "gemeinde": "community",
    "geschichte": "history",
    "große": "large",
    "zahl": "number",
    "hand": "hand",
    "handschrift": "manuscript",
    "hat": "has",
    "lehre": "teaching",
    "lehrer": "teacher",
    "methodischen": "Methodic",
    "pneumatischen": "pneumatic",
    "spricht": "speaks",
    "rezension": "recension",
    "schule": "school",
    "schüler": "student",
    "schrift": "writing",
    "stemma": "stemma",
    "theorie": "theory",
    "thatsächlich": "actually",
    "vorlage": "exemplar",
    "bekannteste": "best-known",
    "vertreter": "representative",
    "schamloser": "shameless",
    "selbstsucht": "self-interest",
    "marktschreierischer": "loudmouthed",
    "großthuerei": "grandstanding",
    "unrecht": "unjustly",
    "folgezeit": "later generations",
    "typische": "typical",
    "geworden": "became",
    "ist": "is"
}

GERMAN_PHRASES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"im sinne", re.IGNORECASE), "in the sense"),
    (re.compile(r"so genannt", re.IGNORECASE), "so-called"),
    (re.compile(r"mit bezug auf", re.IGNORECASE), "with reference to"),
    (re.compile(r"unter zugrundelegung", re.IGNORECASE), "on the basis of")
]

LATIN_GLOSSARY: Dict[str, str] = {
    "eius": "its",
    "carbunculi": "of the carbuncle",
    "hae": "these",
    "notae": "signs",
    "sunt": "are",
    "rubor": "redness",
    "somnus": "sleep",
    "urget": "presses upon",
    "febris": "fever",
    "oriuntur": "arise",
    "circumque": "and around",
    "stomachum": "stomach",
    "fauces": "throat",
    "subito": "suddenly",
    "spiritum": "breath",
    "saepe": "often",
    "elidit": "cuts off"
}

GREEK_GLOSSARY: Dict[str, str] = {
    "καιτοι": "yet",
    "σχεδόν": "almost",
    "ουδείς": "no one",
    "νεωτέρων": "of the younger",
    "ιατρών": "physicians",
    "ούτως": "so",
    "τέχνην": "art",
    "ιατρικήν": "medical",
    "λόγον": "discourse",
    "ως": "as",
    "αθηναίος": "Athenaeus"
}

DOMAIN_TERMS: Iterable[str] = {
    "methodic",
    "pneumatic",
    "theory",
    "school",
    "physician",
    "medicine",
    "stoic",
    "manuscript",
    "treatise"
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the offline translator over an Apographon JSON document."
    )
    parser.add_argument("input_json", help="Path to the source JSON produced by html_to_json.py")
    parser.add_argument("output_json", help="Path for the translated JSON")
    return parser.parse_args()


TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÿ\u0370-\u03FF\u1F00-\u1FFF'’°·]+")


def tokenise(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text)


def translate_german(text: str) -> Tuple[str, List[str], int]:
    working = text
    for pattern, replacement in GERMAN_PHRASES:
        working = pattern.sub(replacement, working)

    unresolved: List[str] = []
    domain_hits = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal domain_hits
        word = match.group(0)
        lower = word.lower()
        if lower in GERMAN_TO_EN:
            english = GERMAN_TO_EN[lower]
            if english in DOMAIN_TERMS:
                domain_hits += 1
            if lower in {"arzt", "ärzte", "schul", "schule", "methodischen", "pneumatischen"}:
                domain_hits += 1
            return preserve_case(word, english)
        unresolved.append(word)
        return "[??]"

    translated = re.sub(r"[A-Za-zÄÖÜäöüß]+", replace, working)
    domain_hits += sum(1 for term in DOMAIN_TERMS if term in translated.lower())
    translated = tidy_sentence(neaten_spacing(translated))
    return translated, dedupe(unresolved), domain_hits


def translate_latin(text: str) -> Tuple[str, List[str], int]:
    words = tokenise(text)
    unresolved: List[str] = []
    domain_hits = 0
    translated_words: List[str] = []

    for word in words:
        lower = word.lower()
        if lower in LATIN_GLOSSARY:
            english = LATIN_GLOSSARY[lower]
            translated_words.append(english)
            if any(term in english for term in DOMAIN_TERMS):
                domain_hits += 1
        elif lower in {"graeci", "elephantiasim"}:
            translated_words.append("the Greeks call elephantiasis")
            domain_hits += 1
        else:
            unresolved.append(word)
            translated_words.append("[??]")
    sentence = tidy_sentence(neaten_spacing(" ".join(translated_words)))
    return sentence, dedupe(unresolved), domain_hits


def translate_greek(text: str) -> Tuple[str, List[str], int]:
    words = tokenise(text)
    unresolved: List[str] = []
    domain_hits = 0
    english_tokens: List[str] = []

    for word in words:
        lower = word.lower()
        if lower in GREEK_GLOSSARY:
            english = GREEK_GLOSSARY[lower]
            english_tokens.append(english)
            if any(term in english for term in DOMAIN_TERMS):
                domain_hits += 1
        elif lower in {"ιατρών"}:
            english_tokens.append("physicians")
            domain_hits += 1
        else:
            unresolved.append(word)
            english_tokens.append("[??]")
    sentence = tidy_sentence(neaten_spacing(" ".join(english_tokens)))
    return sentence, dedupe(unresolved), domain_hits


def preserve_case(source: str, target: str) -> str:
    if source.isupper():
        return target.upper()
    if source[0].isupper():
        return target.capitalize()
    return target


def dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def neaten_spacing(text: str) -> str:
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tidy_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text
    if not text[0].isupper():
        text = text[0].upper() + text[1:]
    if text[-1] not in {".", "?", "!"}:
        text += "."
    return text


def score_confidence(unresolved: List[str], text: str, domain_hits: int) -> str:
    unresolved_count = len(unresolved)
    if unresolved_count <= 2 and domain_hits >= 3:
        return "high"
    if unresolved_count >= 6 or "[??" in text:
        return "flagged"
    return "pending_review"


def compile_notes(unresolved: List[str], domain_hits: int) -> str:
    if not unresolved:
        return f"Glossary coverage satisfactory. Domain hits: {domain_hits}."
    return (
        f"Needs review: unresolved tokens {', '.join(unresolved)}. "
        f"Domain hits: {domain_hits}."
    )


def translate_paragraph(original: Dict[str, str]) -> Tuple[str, List[str], int]:
    lang = original.get("lang", "de")
    text = original.get("text", "")
    if lang == "de":
        return translate_german(text)
    if lang == "la":
        return translate_latin(text)
    if lang == "grc":
        return translate_greek(text)
    return text, [], 0


def run_pipeline(data: Dict[str, object]) -> Dict[str, object]:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    document = data.get("document", {})
    paragraphs: List[Dict[str, object]] = document.get("paragraphs", [])  # type: ignore

    for paragraph in paragraphs:
        original = paragraph.get("original", {})  # type: ignore
        translation = paragraph.get("translation", {})  # type: ignore
        translated_text, unresolved, domain_hits = translate_paragraph(original)
        translation.update(
            {
                "lang": "en",
                "text": translated_text,
                "translator": "translator-agent-v1",
                "vetted_by": "",
                "vetting_notes": compile_notes(unresolved, domain_hits),
                "vetting_date": "",
                "confidence": score_confidence(unresolved, translated_text, domain_hits),
                "timestamp": now
            }
        )
        paragraph["translation"] = translation
    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        metadata["translator"] = "translator-agent-v1"
    data["document"] = document
    return data


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_json)
    output_path = Path(args.output_json)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    translated = run_pipeline(payload)
    output_path.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Translated {len(translated['document']['paragraphs'])} paragraphs -> {output_path}")


if __name__ == "__main__":
    main()
