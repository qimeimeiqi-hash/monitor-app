import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiffResult:
    changed: bool
    content_hash: str
    old_value: Optional[str]
    new_value: str


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compare_content(new_content: str, previous_snapshot: Optional[dict]) -> DiffResult:
    new_hash = compute_hash(new_content)

    if previous_snapshot is None:
        return DiffResult(changed=False, content_hash=new_hash, old_value=None, new_value=new_content)

    previous_hash = previous_snapshot.get("content_hash")
    previous_value = previous_snapshot.get("content")

    if previous_hash == new_hash:
        return DiffResult(changed=False, content_hash=new_hash, old_value=previous_value, new_value=new_content)

    return DiffResult(changed=True, content_hash=new_hash, old_value=previous_value, new_value=new_content)
