
import os, json, asyncio, shutil
from typing import Optional, Dict, Any

BACKEND = os.getenv("ENCRYPTBIN_STORAGE", "local").lower()
DATA_DIR = os.getenv("ENCRYPTBIN_DATA_DIR", "data")

class Store:
    async def save(self, paste_id: str, content: str, meta: Dict[str, Any]):
        raise NotImplementedError
    async def get(self, paste_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
    async def delete(self, paste_id: str):
        raise NotImplementedError

class LocalStore(Store):
    def __init__(self, base: str):
        self.base = base
        os.makedirs(self.base, exist_ok=True)

    async def save(self, paste_id: str, content: str, meta: Dict[str, Any]):
        def _w():
            folder = os.path.join(self.base, paste_id)
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "content.txt"), "w", encoding="utf-8") as f:
                f.write(content)
            with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f)
        await asyncio.to_thread(_w)

    async def get(self, paste_id: str) -> Optional[Dict[str, Any]]:
        def _r():
            folder = os.path.join(self.base, paste_id)
            cpath = os.path.join(folder, "content.txt")
            mpath = os.path.join(folder, "meta.json")
            if not os.path.exists(cpath):
                return None
            with open(cpath, "r", encoding="utf-8") as f:
                content = f.read()
            meta = {}
            if os.path.exists(mpath):
                with open(mpath, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            return {"content": content, "meta": meta}
        return await asyncio.to_thread(_r)

    async def delete(self, paste_id: str):
        def _d():
            folder = os.path.join(self.base, paste_id)
            shutil.rmtree(folder, ignore_errors=True)
        await asyncio.to_thread(_d)

class S3Store(Store):
    def __init__(self):
        import boto3
        self.bucket = os.environ["ENCRYPTBIN_S3_BUCKET"]
        self.prefix = os.getenv("ENCRYPTBIN_S3_PREFIX", "pastes/")
        self.s3 = boto3.client("s3")

    def _key(self, paste_id: str, name: str) -> str:
        return f"{self.prefix}{paste_id}/{name}"

    async def save(self, paste_id: str, content: str, meta: Dict[str, Any]):
        import json as _json
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.s3.put_object(Bucket=self.bucket, Key=self._key(paste_id,"content.txt"), Body=content.encode("utf-8"), ContentType="text/plain; charset=utf-8"))
        await loop.run_in_executor(None, lambda: self.s3.put_object(Bucket=self.bucket, Key=self._key(paste_id,"meta.json"), Body=_json.dumps(meta).encode("utf-8"), ContentType="application/json"))

    async def get(self, paste_id: str) -> Optional[Dict[str, Any]]:
        import json as _json, botocore
        loop = asyncio.get_running_loop()
        try:
            obj = await loop.run_in_executor(None, lambda: self.s3.get_object(Bucket=self.bucket, Key=self._key(paste_id, "content.txt")))
            content = obj["Body"].read().decode("utf-8")
            try:
                mobj = await loop.run_in_executor(None, lambda: self.s3.get_object(Bucket=self.bucket, Key=self._key(paste_id, "meta.json")))
                meta = _json.loads(mobj["Body"].read().decode("utf-8"))
            except botocore.exceptions.ClientError:
                meta = {}
            return {"content": content, "meta": meta}
        except Exception:
            return None

    async def delete(self, paste_id: str):
        loop = asyncio.get_running_loop()
        prefix = f"{self.prefix}{paste_id}/"
        def _del():
            resp = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            if "Contents" in resp:
                self.s3.delete_objects(Bucket=self.bucket, Delete={"Objects":[{"Key":o["Key"]} for o in resp["Contents"]]})
        await loop.run_in_executor(None, _del)

def get_store() -> Store:
    if BACKEND == "s3":
        return S3Store()
    return LocalStore(DATA_DIR)
