"""
MCQ Quiz with Snapshot Support
================================
Run the quiz interactively and save/restore your progress at any point.

Usage
-----
    python mcq_quiz.py                  # start a fresh quiz
    python mcq_quiz.py --load snapshot.json   # resume from a saved snapshot
    python mcq_quiz.py --snapshot-only  # print a snapshot of all questions (no interaction)

Snapshot format
---------------
A snapshot is a JSON file that captures the complete quiz state so the quiz can
be paused and resumed without losing answers or score:

    {
        "version": 1,
        "timestamp": "2026-03-23T12:00:00",
        "current_index": 3,
        "score": 2,
        "total": 10,
        "answers": {
            "1": {"selected": "A", "correct": true},
            "2": {"selected": "B", "correct": false},
            "3": {"selected": "C", "correct": true}
        }
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from questions import QUESTIONS


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

SNAPSHOT_VERSION = 1


def build_snapshot(current_index: int, score: int, answers: Dict) -> dict:
    """Return a serialisable snapshot dict for the current quiz state."""
    return {
        "version": SNAPSHOT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_index": current_index,
        "score": score,
        "total": len(QUESTIONS),
        "answers": answers,
    }


def save_snapshot(snapshot: dict, path: str = "snapshot.json") -> None:
    """Write the snapshot to *path* as pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    print(f"\n💾  Snapshot saved → {path}")


def load_snapshot(path: str) -> dict:
    """Load and validate a snapshot from *path*."""
    file = Path(path)
    if not file.exists():
        sys.exit(f"Error: snapshot file '{path}' not found.")
    with open(file, encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("version") != SNAPSHOT_VERSION:
        sys.exit("Error: incompatible snapshot version.")
    return data


def print_snapshot(snapshot: dict) -> None:
    """Pretty-print a snapshot to stdout."""
    print(json.dumps(snapshot, indent=2))


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_question(q: dict, number: int, total: int) -> None:
    """Print a question with its numbered options."""
    topic_tag = f"[{q['topic']}]"
    print(f"\n{'─' * 60}")
    print(f"Question {number}/{total}  {topic_tag}")
    print(f"{'─' * 60}")
    print(q["question"])
    print()
    for key, text in q["options"].items():
        print(f"  {key}) {text}")
    print()


def get_answer(valid_keys: list) -> Optional[str]:
    """
    Prompt the user for an answer.
    Returns the uppercase answer letter, or None if the user wants to save+quit.
    """
    valid_display = "/".join(valid_keys)
    while True:
        raw = input(f"Your answer ({valid_display}) or 'S' to save & quit: ").strip().upper()
        if raw == "S":
            return None
        if raw in valid_keys:
            return raw
        print(f"  ⚠️  Please enter one of: {valid_display}")


def show_feedback(q: dict, selected: str) -> bool:
    """Print immediate feedback and return True if the answer is correct."""
    correct = selected == q["answer"]
    if correct:
        print("  ✅  Correct!")
    else:
        print(f"  ❌  Incorrect. The correct answer is {q['answer']}.")
    print(f"  💡  {q['explanation']}")
    return correct


def show_results(score: int, total: int, answers: Dict) -> None:
    """Print the final score summary."""
    pct = round(score / total * 100, 1) if total else 0
    print(f"\n{'═' * 60}")
    print("  🏁  Quiz Complete!")
    print(f"{'═' * 60}")
    print(f"  Score  : {score} / {total}  ({pct}%)")
    print()
    for q in QUESTIONS:
        entry = answers.get(str(q["id"]))
        if entry is None:
            status = "⏭  skipped"
        elif entry["correct"]:
            status = "✅  correct"
        else:
            status = f"❌  you chose {entry['selected']}, correct: {q['answer']}"
        print(f"  Q{q['id']:>2}. {status}")
    print(f"{'═' * 60}\n")


# ---------------------------------------------------------------------------
# Snapshot-only mode
# ---------------------------------------------------------------------------

def snapshot_only_mode(path: str = "snapshot.json") -> None:
    """
    Generate a snapshot showing all questions without any interaction.
    Useful for a quick 'snapshot of MCQ' overview.
    """
    snapshot = {
        "version": SNAPSHOT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "description": "Full MCQ question bank snapshot (no answers recorded)",
        "total": len(QUESTIONS),
        "questions": [
            {
                "id": q["id"],
                "topic": q["topic"],
                "question": q["question"],
                "options": q["options"],
                "answer": q["answer"],
                "explanation": q["explanation"],
            }
            for q in QUESTIONS
        ],
    }
    save_snapshot(snapshot, path)
    print_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Main quiz loop
# ---------------------------------------------------------------------------

def run_quiz(start_index: int = 0, score: int = 0, answers: Optional[Dict] = None) -> None:
    """Run the interactive MCQ quiz from *start_index*."""
    if answers is None:
        answers = {}

    total = len(QUESTIONS)
    valid_keys = ["A", "B", "C", "D"]

    print("\n" + "═" * 60)
    print("  📝  MCQ Quiz — Machine Learning, Vision & Electronics")
    print("═" * 60)
    if start_index > 0:
        print(f"  ▶  Resuming from question {start_index + 1}  (score so far: {score}/{start_index})")

    for idx in range(start_index, total):
        q = QUESTIONS[idx]
        display_question(q, idx + 1, total)

        selected = get_answer(valid_keys)
        if selected is None:
            # User wants to save and exit
            snapshot = build_snapshot(idx, score, answers)
            save_snapshot(snapshot)
            print("  👋  Progress saved. Run with --load snapshot.json to resume.")
            return

        correct = show_feedback(q, selected)
        if correct:
            score += 1
        answers[str(q["id"])] = {"selected": selected, "correct": correct}

    # All questions answered — show results and save final snapshot
    show_results(score, total, answers)
    snapshot = build_snapshot(total, score, answers)
    save_snapshot(snapshot, "snapshot_final.json")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCQ Quiz with snapshot save/resume support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--load",
        metavar="FILE",
        help="Resume quiz from a previously saved snapshot JSON file.",
    )
    parser.add_argument(
        "--snapshot-only",
        action="store_true",
        help="Export all questions to a JSON snapshot without running the quiz.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default="snapshot.json",
        help="Output file for --snapshot-only mode (default: snapshot.json).",
    )
    args = parser.parse_args()

    if args.snapshot_only:
        snapshot_only_mode(args.output)
        return

    if args.load:
        state = load_snapshot(args.load)
        run_quiz(
            start_index=state["current_index"],
            score=state["score"],
            answers=state["answers"],
        )
    else:
        run_quiz()


if __name__ == "__main__":
    main()
