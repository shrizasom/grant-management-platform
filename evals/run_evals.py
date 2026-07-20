import json
import os
from pathlib import Path

from agent.agent import run_agent


def main():
    cases = json.loads((Path(__file__).parent / "golden_set.json").read_text())
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is required to run live agent evaluations.")
    passed = 0
    print("PASS  LATENCY  TOKENS  QUESTION")
    for case in cases:
        answer, metrics = run_agent(case["question"])
        ok = case["expected"].lower() in answer.lower()
        passed += ok
        print(f"{'PASS' if ok else 'FAIL':4}  {metrics['latencySeconds']:>7}s  {metrics['inputTokens'] + metrics['outputTokens']:>6}  {case['question']}")
        if not ok: print(f"      expected text: {case['expected']!r}; got: {answer!r}")
    print(f"Accuracy: {passed}/{len(cases)} ({passed / len(cases):.0%})")

if __name__ == "__main__":
    main()
