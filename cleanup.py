import json
import os
import shutil
import time

BACKEND = os.getenv("ENCRYPTBIN_STORAGE", "local").lower()
DATA_DIR = os.getenv("ENCRYPTBIN_DATA_DIR", "data")


def cleanup_local():
    now = int(time.time())
    removed = 0
    if not os.path.exists(DATA_DIR):
        print("No data dir")
        return
    for pid in os.listdir(DATA_DIR):
        folder = os.path.join(DATA_DIR, pid)
        mpath = os.path.join(folder, "meta.json")
        if not os.path.exists(mpath):
            continue
        try:
            with open(mpath, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
        exp = int(meta.get("expires", 0) or 0)
        if exp != 0 and now > exp:
            shutil.rmtree(folder, ignore_errors=True)
            print("Removed expired", pid)
            removed += 1
    print("Cleanup complete. Removed", removed)


def cleanup_s3():
    import json as _json

    import boto3

    bucket = os.environ["ENCRYPTBIN_S3_BUCKET"]
    prefix = os.getenv("ENCRYPTBIN_S3_PREFIX", "pastes/")
    s3 = boto3.client("s3")
    now = int(time.time())
    removed = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("meta.json"):
                try:
                    body = (
                        s3.get_object(Bucket=bucket, Key=key)["Body"]
                        .read()
                        .decode("utf-8")
                    )
                    meta = _json.loads(body)
                    exp = int(meta.get("expires", 0) or 0)
                    if exp != 0 and now > exp:
                        paste_prefix = key.rsplit("/", 1)[0] + "/"
                        to_delete = s3.list_objects_v2(
                            Bucket=bucket, Prefix=paste_prefix
                        )
                        if "Contents" in to_delete:
                            s3.delete_objects(
                                Bucket=bucket,
                                Delete={
                                    "Objects": [
                                        {"Key": o["Key"]} for o in to_delete["Contents"]
                                    ]
                                },
                            )
                        removed += 1
                        print("Removed expired prefix", paste_prefix)
                except Exception as e:
                    print("Error", key, e)
    print("Cleanup complete. Removed", removed)


if __name__ == "__main__":
    if BACKEND == "s3":
        cleanup_s3()
    else:
        cleanup_local()
