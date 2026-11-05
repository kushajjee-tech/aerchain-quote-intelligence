"""Append-only conversation store (PRD AI-13, architecture §7.1).

- Messages are stored exactly as sent to / returned by the API (JSON text, including thinking blocks).
- The only write operation is appending. UPDATE/DELETE are blocked by database triggers.
- A turn (user message + assistant response) is appended atomically, and only after success, so a
  failed turn never enters the history.
- Rejecting an answer (grounding/lint failure) appends an annotation row; history is never edited.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import ConversationMessage

API_ROLES = ("user", "assistant", "system")
ANNOTATION_ROLE = "annotation"


def _dumps(content: Any) -> str:
    # Stable, lossless serialisation of what was sent/returned.
    return json.dumps(content, ensure_ascii=False, separators=(",", ":"))


class ConversationStore:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def _next_seq(self, s: Session, conversation_id: str) -> int:
        current = s.scalar(
            select(func.max(ConversationMessage.seq)).where(
                ConversationMessage.conversation_id == conversation_id
            )
        )
        return 0 if current is None else current + 1

    def append(self, conversation_id: str, messages: list[dict[str, Any]]) -> list[int]:
        """Append one or more API messages atomically (all or nothing). Returns their seq numbers."""
        for m in messages:
            if m.get("role") not in API_ROLES:
                raise ValueError(f"invalid role for API history: {m.get('role')}")
        with self._sf.begin() as s:
            seq = self._next_seq(s, conversation_id)
            for i, m in enumerate(messages):
                s.add(ConversationMessage(
                    conversation_id=conversation_id, seq=seq + i, role=m["role"],
                    content_json=_dumps(m["content"]),
                ))
        return [seq + i for i in range(len(messages))]

    def annotate_rejected(self, conversation_id: str, assistant_seq: int, reason: str) -> None:
        """Record that an assistant answer was rejected, without touching the answer itself."""
        with self._sf.begin() as s:
            seq = self._next_seq(s, conversation_id)
            s.add(ConversationMessage(
                conversation_id=conversation_id, seq=seq, role=ANNOTATION_ROLE,
                content_json=_dumps({"rejected_seq": assistant_seq, "reason": reason}),
            ))

    def rows(self, conversation_id: str) -> list[ConversationMessage]:
        with self._sf() as s:
            return list(s.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.seq)
            ))

    def history(self, conversation_id: str) -> list[dict[str, Any]]:
        """The exact message list to send back to the API (annotations excluded)."""
        return [
            {"role": r.role, "content": json.loads(r.content_json)}
            for r in self.rows(conversation_id) if r.role in API_ROLES
        ]
