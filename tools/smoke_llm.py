from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def run(base_url: str, pdf_path: Path, owner_id: str) -> int:
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 1

    with pdf_path.open("rb") as f:
        files = {"file": (pdf_path.name, f.read(), "application/pdf")}
    data = {"owner_id": owner_id}

    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        create = client.post("/documents", data=data, files=files)
        if create.status_code != 201:
            print("Upload failed:")
            print(create.status_code, create.text)
            return 1
        doc = create.json()
        doc_id = doc["id"]

        parse = client.post(f"/documents/{doc_id}/llm-parse")
        if parse.status_code != 200:
            print("LLM parse failed:")
            print(parse.status_code, parse.text)
            return 1

        print("Document created:", doc_id)
        print(json.dumps(parse.json(), indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test LLM parse endpoint.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--pdf",
        default="local/test-pdfs/Experian - Access your credit report.pdf",
        help="Path to PDF file for smoke test",
    )
    parser.add_argument(
        "--owner-id",
        default="smoke-user",
        help="Owner ID for uploaded document",
    )
    args = parser.parse_args()
    return run(base_url=args.base_url, pdf_path=Path(args.pdf), owner_id=args.owner_id)


if __name__ == "__main__":
    raise SystemExit(main())

