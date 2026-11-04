"""Object storage adapter. Interface is S3-shaped; VM proof driver is local disk.
Production driver must be S3-compatible (R2/B2) — that driver is an interface stub
here until S3 credentials are supplied on the VPS. Do not claim local = S3.
Path layout (both drivers): <user_id>/<brand_id>/<kind>/<filename>
"""
import os, shutil
from pathlib import Path

class Storage:
    def put(self, user_id, brand_id, kind, filename, src_path): raise NotImplementedError
    def get_path(self, storage_path): raise NotImplementedError

class LocalStorage(Storage):
    def __init__(self, root): self.root = Path(root)
    def put(self, user_id, brand_id, kind, filename, src_path):
        # Reject path traversal in every component.
        for part in (str(user_id), str(brand_id), kind, filename):
            if not part or "/" in part or "\\" in part or part in (".", ".."):
                raise ValueError("invalid storage component")
        dest = self.root / str(user_id) / str(brand_id) / kind / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dest)
        return str(dest.relative_to(self.root))
    def get_path(self, storage_path):
        p = (self.root / storage_path).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError("storage path escapes root")
        return str(p)

class S3Storage(Storage):
    def __init__(self, endpoint, bucket):
        self.endpoint, self.bucket = endpoint, bucket
    def put(self, *a, **k):
        raise RuntimeError("S3 driver not configured: set KLIPR_STORAGE_ENDPOINT, bucket and credentials on the VPS, and install/configure the S3 client there. Local driver is the VM proof only.")
    def get_path(self, *a, **k):
        raise RuntimeError("S3 objects have no local path; use a signed URL in production.")

def get_storage(cfg):
    if cfg.storage_driver == "s3":
        return S3Storage(cfg.storage_endpoint, cfg.storage_bucket)
    return LocalStorage(cfg.storage_root)
