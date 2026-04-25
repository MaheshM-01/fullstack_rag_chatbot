import argparse
import json
from pathlib import Path

import httpx


def load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array")
    return data


def ask_question(worker_url: str, namespace: str, question: str) -> dict:
    response = httpx.post(
        f"{worker_url}/chat",
        json={
            "question": question,
            "namespace": namespace,
            "chat_history": [],
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def evaluate_answer(answer: str, expected_keywords: list[str]) -> bool:
    lowered = answer.lower()
    return all(keyword.lower() in lowered for keyword in expected_keywords)


def main():
    parser = argparse.ArgumentParser(description="Simple keyword-based evaluation for worker /chat")
    parser.add_argument(
        "--dataset",
        default="scripts/sample_eval.json",
        help="Path to evaluation JSON dataset",
    )
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--worker-url", default="http://localhost:8000")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise SystemExit(f"Dataset not found: {dataset_path}")

    dataset = load_dataset(dataset_path)
    passed = 0

    print(f"Running {len(dataset)} evaluation cases against {args.worker_url}/chat")
    print("-" * 80)

    for index, sample in enumerate(dataset, start=1):
        question = sample.get("question", "").strip()
        expected_keywords = sample.get("expected_keywords", [])

        if not question or not isinstance(expected_keywords, list):
            print(f"[{index}] INVALID sample format, skipping")
            continue

        try:
            result = ask_question(args.worker_url, args.namespace, question)
            answer = result.get("answer", "")
            ok = evaluate_answer(answer, expected_keywords)
            passed += int(ok)

            status = "PASS" if ok else "FAIL"
            print(f"[{index}] {status} | Q: {question}")
            print(f"      Keywords: {expected_keywords}")
            print(f"      Answer: {answer[:180]}{'...' if len(answer) > 180 else ''}")
        except Exception as error:
            print(f"[{index}] ERROR | Q: {question} | {error}")

    total = len(dataset)
    score = (passed / total * 100) if total else 0
    print("-" * 80)
    print(f"Final Score: {passed}/{total} ({score:.1f}%)")


if __name__ == "__main__":
    main()
