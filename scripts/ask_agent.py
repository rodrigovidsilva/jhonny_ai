from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app_factory import create_agent


def main() -> None:
    question = " ".join(sys.argv[1:]) or "How much did we sell today?"
    agent = create_agent(ROOT)
    response = agent.answer(question)
    print(response["answer"])


if __name__ == "__main__":
    main()
