"""Shared helper for mocked model replies: plain JSON, or a server-sent-event stream when the request streams."""
import json

import httpx2 as httpx


def message(content, stop="end_turn"):
    return {"id": "m", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}


def respond(request, content, stop="end_turn"):
    body = json.loads(request.content)
    if not body.get("stream"):
        return httpx.Response(200, json=message(content, stop))
    events = [("message_start", {"type": "message_start", "message": {**message([], None), "stop_reason": None}})]
    for i, block in enumerate(content):
        if block["type"] == "text":
            events += [("content_block_start", {"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}}),
                       ("content_block_delta", {"type": "content_block_delta", "index": i,
                                                "delta": {"type": "text_delta", "text": block["text"]}}),
                       ("content_block_stop", {"type": "content_block_stop", "index": i})]
    events += [("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None},
                                  "usage": {"output_tokens": 1}}),
               ("message_stop", {"type": "message_stop"})]
    sse = "".join(f"event: {e}\ndata: {json.dumps(d)}\n\n" for e, d in events)
    return httpx.Response(200, content=sse.encode(), headers={"content-type": "text/event-stream"})
