import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List


API_URL = "https://wxpusher.zjiecode.com/api/send/message"


@dataclass(frozen=True)
class WxPusherResult:
    success: bool
    response_text: str


def send_message(
    app_token: str,
    content: str,
    summary: str,
    uids: List[str],
    topic_ids: List[int],
    attempts: int = 3,
) -> WxPusherResult:
    if not app_token:
        raise ValueError("WXPUSHER_APP_TOKEN is required")
    if not uids and not topic_ids:
        raise ValueError("At least one WxPusher UID or topic id is required")

    payload = {
        "appToken": app_token,
        "content": content,
        "summary": summary[:100],
        "contentType": 3,
    }
    if uids:
        payload["uids"] = uids
    if topic_ids:
        payload["topicIds"] = topic_ids

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response_text = ""
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                response_text = response.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            if 400 <= exc.code < 500:
                return WxPusherResult(False, response_text)
        except urllib.error.URLError as exc:
            response_text = str(exc)

        if attempt < attempts:
            time.sleep(0.75 * attempt)
    else:
        return WxPusherResult(False, response_text)

    try:
        parsed = json.loads(response_text)
        success = parsed.get("code") == 1000 or parsed.get("success") is True
    except json.JSONDecodeError:
        success = False
    return WxPusherResult(success, response_text)
