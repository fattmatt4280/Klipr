"""Klipr Phase 0 config. No secrets in code. All secrets come from env only.
billing_enabled is OFF until Phase 7 (public launch) per spec. Admin bypasses
credits during testing, but every AI call is still metered and logged.
"""
import os
from dataclasses import dataclass

def _bool(v, default=False):
    return str(v).lower() in ("1", "true", "yes") if v is not None else default

@dataclass
class Config:
    env: str = os.environ.get("KLIPR_ENV", "production")  # production | staging
    database_url: str = os.environ.get("KLIPR_DATABASE_URL", "")
    # Storage: s3-compatible when KLIPR_STORAGE_DRIVER=s3 and endpoint/keys are set.
    # VM proof uses local driver, which implements the same interface/path layout
    # (user_id/brand_id/...) — it is NOT S3, and must not be presented as S3.
    storage_driver: str = os.environ.get("KLIPR_STORAGE_DRIVER", "local")
    storage_root: str = os.environ.get("KLIPR_STORAGE_ROOT", "storage")
    storage_endpoint: str = os.environ.get("KLIPR_STORAGE_ENDPOINT", "")
    storage_bucket: str = os.environ.get("KLIPR_STORAGE_BUCKET", "klipr")
    openrouter_api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    openrouter_base: str = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    billing_enabled: bool = _bool(os.environ.get("KLIPR_BILLING_ENABLED"), False)
    crm_log_path: str = os.environ.get("KLIPR_CRM_LOG", "crm/events.jsonl")
    auth_token_file: str = os.environ.get("KLIPR_AUTH_TOKEN_FILE", ".klipr_admin_token")

CONFIG = Config()
