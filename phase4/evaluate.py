"""
Phase 4: Evaluation – accuracy and citation quality on held-out questions.
Loads a list of (question, expected_keywords); runs RAG; reports keyword match and source presence.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Default held-out questions (example)
DEFAULT_QUESTIONS = [
    {"q": "What is the nav for ICICI large cap fund?", "expected_keywords": ["121", "nav", "ICICI", "large cap"]},
    {"q": "What is the expense ratio of SBI Contra Fund?", "expected_keywords": ["expense", "0.71", "0.7", "SBI", "Contra"]},
    {"q": "What is the minimum SIP for SBI Small Cap Fund?", "expected_keywords": ["500", "SIP", "minimum", "SBI", "small cap"]},
    {"q": "Does SBI ELSS have a lock-in?", "expected_keywords": ["lock", "3", "year", "ELSS"]},
    {"q": "How do I download capital gains statement on IndMoney?", "expected_keywords": ["More", "Taxation", "Download", "financial year"]},
]


def _run_rag(question: str) -> tuple[str, list]:
    """Run RAG (Phase 1 ask). Returns (answer, sources)."""
    from phase1.rag import ask
    answer, sources = ask(question, top_k=5)
    return answer, sources


def _keyword_match(answer: str, keywords: list[str]) -> bool:
    """True if answer (lower) contains at least one of the expected keywords (lower)."""
    if not keywords:
        return True
    a = answer.lower()
    return any(k.lower() in a for k in keywords)


def evaluate(questions: list[dict] | None = None, questions_path: Path | None = None) -> dict:
    """
    Run evaluation. Returns dict with accuracy (keyword match rate), citation_rate, and per-question results.
    questions: list of {"q": str, "expected_keywords": list[str]}
    questions_path: optional path to JSON file with same structure.
    """
    if questions_path and Path(questions_path).exists():
        data = json.loads(Path(questions_path).read_text(encoding="utf-8"))
        questions = data.get("questions", data) if isinstance(data, dict) else data
    if not questions:
        questions = DEFAULT_QUESTIONS

    results = []
    keyword_hits = 0
    citation_hits = 0
    for i, item in enumerate(questions):
        q = item.get("q", item.get("question", ""))
        expected = item.get("expected_keywords", item.get("keywords", []))
        if not q:
            continue
        try:
            answer, sources = _run_rag(q)
        except Exception as e:
            results.append({"q": q, "keyword_match": False, "has_sources": False, "error": str(e)})
            continue
        kw_ok = _keyword_match(answer, expected)
        has_src = len(sources) > 0 and any(s.get("url") for s in sources)
        if kw_ok:
            keyword_hits += 1
        if has_src:
            citation_hits += 1
        results.append({
            "q": q,
            "keyword_match": kw_ok,
            "has_sources": has_src,
            "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
            "num_sources": len(sources),
        })
    n = len(results)
    return {
        "accuracy_keyword": keyword_hits / n if n else 0,
        "citation_rate": citation_hits / n if n else 0,
        "total": n,
        "results": results,
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="Phase 4 evaluation: accuracy and citation on held-out questions")
    p.add_argument("--questions", type=Path, default=None, help="JSON file with questions and expected_keywords")
    p.add_argument("--output", type=Path, default=None, help="Write results JSON here")
    args = p.parse_args()
    out = evaluate(questions_path=args.questions)
    print(f"Accuracy (keyword match): {out['accuracy_keyword']:.2%} ({out['total']} questions)")
    print(f"Citation rate:           {out['citation_rate']:.2%}")
    for r in out["results"]:
        print(f"  - {r['q'][:50]}... -> kw={r['keyword_match']}, sources={r['has_sources']}")
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
