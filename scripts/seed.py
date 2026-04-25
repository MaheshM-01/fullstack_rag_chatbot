import argparse
import json
from pathlib import Path

import httpx


def ingest_file(worker_url: str, file_path: Path, namespace: str, force_reingest: bool) -> dict:
    with file_path.open("rb") as handle:
        response = httpx.post(
            f"{worker_url}/ingest/file",
            params={"namespace": namespace, "force_reingest": force_reingest},
            files={"file": (file_path.name, handle, "application/octet-stream")},
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def ingest_url(worker_url: str, url: str, namespace: str, force_reingest: bool) -> dict:
    response = httpx.post(
        f"{worker_url}/ingest/url",
        json={"url": url, "namespace": namespace, "force_reingest": force_reingest},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Seed worker with one file or URL")
    parser.add_argument("--source", required=True, help="File path or URL")
    parser.add_argument("--namespace", default="default", help="Namespace in vector store")
    parser.add_argument("--worker-url", default="http://localhost:8000", help="Worker base URL")
    parser.add_argument("--force-reingest", action="store_true", help="Reingest even if already processed")
    args = parser.parse_args()

    source = args.source.strip()

    try:
        if source.startswith("http://") or source.startswith("https://"):
            result = ingest_url(args.worker_url, source, args.namespace, args.force_reingest)
        else:
            file_path = Path(source)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            result = ingest_file(args.worker_url, file_path, args.namespace, args.force_reingest)

        print(json.dumps(result, indent=2))

    except Exception as error:
        print(f"Seeding failed: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
