import base64
import json
import socket
import threading
import time
from types import SimpleNamespace

from GramAddict.plugins.llama_image_chat import (
    LlamaImageChat,
    build_chat_messages,
    encode_image_to_base64,
    mask_secrets,
    scan_network,
)


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_encode_image_to_base64(tmp_path):
    image_path = tmp_path / "sample.bin"
    image_bytes = b"test-bytes"
    image_path.write_bytes(image_bytes)

    encoded = encode_image_to_base64(image_path)

    assert encoded == base64.b64encode(image_bytes).decode("utf-8")


def test_build_chat_messages_with_history():
    history = [{"role": "system", "content": [{"type": "text", "text": "Hi"}]}]
    messages = build_chat_messages("Hello", ["img"], history)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"][1]["image"] == "img"


def test_plugin_run_persists_history_and_output(tmp_path, mocker):
    plugin = LlamaImageChat()
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"fake-image")

    history_file = tmp_path / "history.json"
    output_file = tmp_path / "out.txt"

    args = SimpleNamespace(
        llama_chat=True,
        llama_images=[str(image_path)],
        llama_message="Describe the scene with key=ABCDEFGHIJKL1234567890",
        llama_prompt_file=None,
        llama_model="llama3",
        llama_endpoint="http://localhost:11434/api/chat",
        llama_history_file=str(history_file),
        llama_output_file=str(output_file),
    )
    configs = SimpleNamespace(args=args)

    payload = {
        "message": {
            "content": "It looks like a sunset with token=ABCDEFGH123456789",
        }
    }
    mocker.patch(
        "GramAddict.plugins.llama_image_chat.requests.post",
        return_value=DummyResponse(payload),
    )

    plugin.run(
        device=None,
        configs=configs,
        storage=None,
        sessions=None,
        profile_filter=None,
        plugin=None,
    )

    output_text = output_file.read_text(encoding="utf-8")
    assert output_text.startswith("It looks like a sunset")
    assert "ABCDEFGH123456789" not in output_text
    saved_history = json.loads(history_file.read_text(encoding="utf-8"))
    assert len(saved_history) == 2
    assert saved_history[0]["role"] == "user"
    assert saved_history[1]["role"] == "assistant"
    assert saved_history[0]["content"][1]["type"] == "image"
    assert "ABCDEFGHIJKL1234567890" not in saved_history[0]["content"][0]["text"]
    assert "ABCDEFGH123456789" not in saved_history[1]["content"][0]["text"]


def test_wyy_creates_expected_structure():
    plugin = LlamaImageChat()
    entry = plugin.wyy("response", role="assistant", images=["abc"])

    assert entry["role"] == "assistant"
    assert entry["content"][0]["text"] == "response"
    assert entry["content"][1]["image"] == "abc"


def test_mask_secrets_masks_sensitive_values():
    text = (
        'api_key = "sk-1234567890ABCDEFGHIJ" secret '
        "token=abcd1234 password:ZXCVBNMASDFGHJKL"
    )
    masked = mask_secrets(text)

    assert '"sk-1234567890ABCDEFGHIJ"' not in masked
    assert "sk-1***GHIJ" in masked
    assert "token=***" in masked
    assert "password:ZXCV***HJKL" in masked


def test_scan_network_detects_open_port():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def _accept_once():
        try:
            server.accept()
        except OSError:
            pass

    thread = threading.Thread(target=_accept_once, daemon=True)
    thread.start()
    time.sleep(0.05)

    results = scan_network(["127.0.0.1"], [port])
    server.close()
    thread.join(timeout=0.1)

    assert "127.0.0.1" in results
    assert port in results["127.0.0.1"]


def test_security_sweep_creates_report(tmp_path):
    plugin = LlamaImageChat()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def _accept_once():
        try:
            server.accept()
        except OSError:
            pass

    thread = threading.Thread(target=_accept_once, daemon=True)
    thread.start()
    time.sleep(0.05)

    report_path = tmp_path / "report.json"
    args = SimpleNamespace(
        llama_scan_hosts=["127.0.0.1"],
        llama_port_range=(port, port),
        llama_security_report=str(report_path),
    )

    report = plugin._security_sweep(args)
    server.close()
    thread.join(timeout=0.1)

    assert report["network"]["127.0.0.1"] == [port]
    stored = json.loads(report_path.read_text(encoding="utf-8"))
    assert stored["network"]["127.0.0.1"] == [port]
