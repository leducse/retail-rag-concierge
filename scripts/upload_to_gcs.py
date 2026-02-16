#!/usr/bin/env python3
"""
Magic Apron — Day 1: Ingestion — Upload data to Cloud Storage (GCS)

GCP CONCEPTS (teaching):
------------------------
• Cloud Storage (GCS) is object storage. Buckets hold "objects" (files). This is
  like S3. Vertex AI Search can ingest from a GCS bucket (or prefix), so we put
  our product_catalog.csv and diy_guides/*.md here.

• Why upload to GCS? The Data Store in Vertex AI Search is configured with a
  source (e.g. gs://your-bucket/your-prefix/). Google's crawler reads from that
  location and builds the search index. No GCS → no indexed content for RAG.

• In production, you might: (1) Export from BigQuery to GCS on a schedule,
  (2) Have a CI job that builds and uploads docs, (3) Use Eventarc to trigger
  re-ingestion when new objects land in the bucket.
"""

import argparse
from pathlib import Path

try:
    from google.cloud import storage
except ImportError:
    print("Install: pip install google-cloud-storage")
    raise

def upload_dir_to_gcs(local_dir: Path, bucket_name: str, prefix: str = "") -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    local_dir = local_dir.resolve()
    if not local_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {local_dir}")

    for f in local_dir.rglob("*"):
        if f.is_file():
            rel = f.relative_to(local_dir)
            blob_path = f"{prefix}/{rel}".lstrip("/") if prefix else str(rel)
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(f), content_type=_content_type(f.suffix))
            print(f"Uploaded {f.name} -> gs://{bucket_name}/{blob_path}")

def upload_file_to_gcs(local_path: Path, bucket_name: str, blob_name: str | None = None) -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    local_path = local_path.resolve()
    name = blob_name or local_path.name
    blob = bucket.blob(name)
    blob.upload_from_filename(str(local_path), content_type=_content_type(local_path.suffix))
    print(f"Uploaded {local_path.name} -> gs://{bucket_name}/{name}")

def _content_type(suffix: str) -> str:
    if suffix == ".csv":
        return "text/csv"
    if suffix == ".md":
        return "text/markdown"
    return "application/octet-stream"

def main():
    parser = argparse.ArgumentParser(description="Upload Magic Apron mock data to GCS")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--prefix", default="magic_apron", help="Object prefix (default: magic_apron)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    data_dir = base / "data"
    if not data_dir.exists():
        print("Run generate_mock_data.py first to create data/")
        return

    # Upload CSV
    csv_path = data_dir / "product_catalog.csv"
    if csv_path.exists():
        upload_file_to_gcs(csv_path, args.bucket, f"{args.prefix}/product_catalog.csv")

    # Upload DIY guides folder
    diy_dir = data_dir / "diy_guides"
    if diy_dir.exists():
        upload_dir_to_gcs(diy_dir, args.bucket, f"{args.prefix}/diy_guides")

    print("Done. In Vertex AI Search, set the data store source to:")
    print(f"  gs://{args.bucket}/{args.prefix}/")

if __name__ == "__main__":
    main()
