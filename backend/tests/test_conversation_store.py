"""M0: append-only conversation store (PRD AI-13)."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.llm.conversation import ConversationStore

THINKING = {"type": "thinking", "thinking": "", "signature": "EqQBCkYIBxgCKkA="}


def test_exact_round_trip(session_factory):
    st = ConversationStore(session_factory)
    content = [THINKING, {"type": "text", "text": "₹42/kg — ok", "citations": None}]
    st.append("c1", [{"role": "user", "content": "hi"}, {"role": "assistant", "content": content}])
    assert st.history("c1") == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": content}]


@pytest.mark.parametrize("stmt", [
    "update conversation_message set content_json='[]'",
    "delete from conversation_message",
])
def test_edits_are_blocked(session_factory, stmt):
    st = ConversationStore(session_factory)
    st.append("c1", [{"role": "user", "content": "hi"}])
    with pytest.raises(DatabaseError):
        with session_factory.begin() as s:
            s.execute(text(stmt))
    assert st.history("c1") == [{"role": "user", "content": "hi"}]


def test_append_is_atomic(session_factory):
    st = ConversationStore(session_factory)
    with pytest.raises(ValueError):
        st.append("c1", [{"role": "user", "content": "a"}, {"role": "bogus", "content": "b"}])
    assert st.history("c1") == []


def test_rejection_is_an_annotation_not_an_edit(session_factory):
    st = ConversationStore(session_factory)
    seqs = st.append("c1", [{"role": "user", "content": "q"}, {"role": "assistant", "content": [{"type": "text", "text": "a"}]}])
    st.annotate_rejected("c1", seqs[-1], "grounding failed")
    assert st.history("c1")[-1]["content"] == [{"type": "text", "text": "a"}]
    assert st.rows("c1")[-1].role == "annotation"
