import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


class LocalStore:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, paste_id: str) -> Path:
        return self.data_dir / f"{paste_id}.json"

    async def save(self, paste_id: str, content: str, meta: dict):
        rec = {"content": content, "meta": meta}
        path = self._path(paste_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(rec, f)

    async def save_encrypted(
        self, paste_id: str, ciphertext_b64: str, iv_b64: str, alg: str, meta: dict
    ):
        rec = {
            "encrypted_payload": {
                "ciphertext_b64": ciphertext_b64,
                "iv_b64": iv_b64,
                "alg": alg,
            },
            "meta": meta,
        }
        path = self._path(paste_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(rec, f)

    async def get(self, paste_id: str):
        path = self._path(paste_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    async def put(self, paste_id: str, rec: dict):
        path = self._path(paste_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(rec, f)

    async def delete(self, paste_id: str):
        path = self._path(paste_id)
        if path.exists():
            path.unlink()


class S3Store:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.client = boto3.client("s3")

    def _key(self, paste_id: str) -> str:
        return f"{paste_id}.json"

    async def save(self, paste_id: str, content: str, meta: dict):
        rec = {"content": content, "meta": meta}
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(paste_id),
            Body=json.dumps(rec).encode("utf-8"),
        )

    async def save_encrypted(
        self, paste_id: str, ciphertext_b64: str, iv_b64: str, alg: str, meta: dict
    ):
        rec = {
            "encrypted_payload": {
                "ciphertext_b64": ciphertext_b64,
                "iv_b64": iv_b64,
                "alg": alg,
            },
            "meta": meta,
        }
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(paste_id),
            Body=json.dumps(rec).encode("utf-8"),
        )

    async def get(self, paste_id: str):
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=self._key(paste_id))
            return json.loads(resp["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    async def put(self, paste_id: str, rec: dict):
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(paste_id),
            Body=json.dumps(rec).encode("utf-8"),
        )

    async def delete(self, paste_id: str):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._key(paste_id))
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise


def get_store():
    backend = os.getenv("ENCRYPTBIN_STORAGE", "local")
    if backend == "s3":
        bucket = os.getenv("ENCRYPTBIN_S3_BUCKET")
        if not bucket:
            raise RuntimeError("ENCRYPTBIN_S3_BUCKET must be set for S3 storage")
        return S3Store(bucket)
    else:
        data_dir = os.getenv("ENCRYPTBIN_DATA_DIR", "./data")
        return LocalStore(data_dir)
