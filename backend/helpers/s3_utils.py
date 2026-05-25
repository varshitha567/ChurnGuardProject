import os
import json
import boto3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _get_client():
    """Returns a boto3 S3 client.
    In Lambda: uses IAM role credentials automatically.
    Locally: uses credentials from .env via environment variables.
    """
    kwargs = {"region_name": os.getenv("AWS_REGION", "ap-south-1")}
    key = os.getenv("AWS_ACCESS_KEY_ID", "")
    if key and key != "your_aws_access_key_here":
        kwargs["aws_access_key_id"] = key
        kwargs["aws_secret_access_key"] = os.getenv("AWS_SECRET_ACCESS_KEY")
    return boto3.client("s3", **kwargs)


def _is_aws_configured() -> bool:
    key = os.getenv("AWS_ACCESS_KEY_ID", "")
    return bool(key and key != "your_aws_access_key_here")


def upload_csv(local_path: str, s3_key: str = "customer_data.csv") -> None:
    """
    Upload the customer CSV from local disk to S3.
    Called once at the start of the pipeline run.
    """
    if not _is_aws_configured():
        print(f"[DEV] Skipping S3 upload — using local file: {local_path}")
        return

    bucket = os.getenv("S3_BUCKET_NAME")
    s3 = _get_client()
    s3.upload_file(local_path, bucket, s3_key)
    print(f"Uploaded {local_path} to s3://{bucket}/{s3_key}")


def save_pipeline_results(results: dict) -> str:
    """
    Save signal pipeline results as a dated JSON file in S3.
    Returns the S3 key it was saved under.
    Falls back to saving locally in dev mode.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    s3_key = f"results/pipeline_{timestamp}.json"
    payload = json.dumps(results, indent=2, default=str)

    if not _is_aws_configured():
        local_out = os.path.join(
            os.path.dirname(__file__), "..", "data", f"pipeline_{timestamp}.json"
        )
        with open(local_out, "w") as f:
            f.write(payload)
        print(f"[DEV] Results saved locally: {local_out}")
        return local_out

    bucket = os.getenv("S3_BUCKET_NAME")
    s3 = _get_client()
    s3.put_object(Bucket=bucket, Key=s3_key, Body=payload, ContentType="application/json")
    print(f"Results saved to s3://{bucket}/{s3_key}")
    return s3_key


def get_latest_pipeline_results() -> dict:
    """
    Fetch the most recent pipeline results JSON from S3.
    Falls back to the most recent local JSON in dev mode.
    """
    if not _is_aws_configured():
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        files = sorted(
            [f for f in os.listdir(data_dir) if f.startswith("pipeline_") and f.endswith(".json")],
            reverse=True,
        )
        for fname in files:
            with open(os.path.join(data_dir, fname)) as f:
                data = json.load(f)
            if "signal_responses" in data and "signal_counts" in data:
                return data
        return {}

    bucket = os.getenv("S3_BUCKET_NAME")
    s3 = _get_client()
    response = s3.list_objects_v2(Bucket=bucket, Prefix="results/pipeline_")
    objects = response.get("Contents", [])
    if not objects:
        return {}

    latest = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[0]
    obj = s3.get_object(Bucket=bucket, Key=latest["Key"])
    return json.loads(obj["Body"].read())


def list_all_pipeline_results() -> list[dict]:
    """
    Return metadata for all past pipeline runs — used by the dashboard
    to populate a run history dropdown.
    """
    if not _is_aws_configured():
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        files = sorted(
            [f for f in os.listdir(data_dir) if f.startswith("pipeline_") and f.endswith(".json")],
            reverse=True,
        )
        return [
            {"key": f, "timestamp": f.replace("pipeline_", "").replace(".json", "")}
            for f in files
        ]

    bucket = os.getenv("S3_BUCKET_NAME")
    s3 = _get_client()
    response = s3.list_objects_v2(Bucket=bucket, Prefix="results/pipeline_")
    objects = response.get("Contents", [])
    return [
        {"key": obj["Key"], "timestamp": obj["LastModified"].isoformat()}
        for obj in sorted(objects, key=lambda x: x["LastModified"], reverse=True)
    ]