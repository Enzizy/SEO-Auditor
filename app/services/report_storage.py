from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings


@dataclass(slots=True)
class StoredReport:
    location: str
    filename: str
    media_type: str


class ReportStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = self.settings.storage_backend.lower()
        self._s3_client = None

    def save_text(self, audit_run_id: int, filename: str, content: str, media_type: str) -> StoredReport:
        return self._save(audit_run_id, filename, content.encode("utf-8"), media_type)

    def save_bytes(self, audit_run_id: int, filename: str, content: bytes, media_type: str) -> StoredReport:
        return self._save(audit_run_id, filename, content, media_type)

    def open(self, location: str, media_type: str) -> tuple[bytes, str]:
        if location.startswith("s3://"):
            bucket, key = _parse_s3_location(location)
            try:
                body = self._client().get_object(Bucket=bucket, Key=key)["Body"].read()
            except ClientError as exc:
                raise FileNotFoundError(location) from exc
            return body, media_type
        path = Path(location)
        return path.read_bytes(), media_type

    def _save(self, audit_run_id: int, filename: str, content: bytes, media_type: str) -> StoredReport:
        if self.backend == "s3":
            bucket = self.settings.s3_bucket
            if not bucket:
                raise ValueError("SEO_AUDITOR_S3_BUCKET is required when storage backend is s3")
            key = f"reports/audit-{audit_run_id}/{filename}"
            self._client().put_object(Bucket=bucket, Key=key, Body=content, ContentType=media_type)
            return StoredReport(location=f"s3://{bucket}/{key}", filename=filename, media_type=media_type)

        report_dir = self.settings.reports_path / f"audit-{audit_run_id}"
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / filename
        path.write_bytes(content)
        return StoredReport(location=str(path), filename=filename, media_type=media_type)

    def _client(self):
        if self._s3_client is None:
            session = boto3.session.Session(region_name=self.settings.s3_region)
            self._s3_client = session.client("s3", endpoint_url=self.settings.s3_endpoint_url)
        return self._s3_client


def _parse_s3_location(location: str) -> tuple[str, str]:
    parsed = urlparse(location)
    return parsed.netloc, parsed.path.lstrip("/")
