import base64
import json
import logging
import os
import re
import socket
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import requests

from GramAddict.core.plugin_loader import Plugin

logger = logging.getLogger(__name__)


def encode_image_to_base64(path: Path) -> str:
    """Return a base64 string representation of the image at *path*."""

    with path.open("rb") as image_file:
        encoded = base64.b64encode(image_file.read())
    return encoded.decode("utf-8")


def build_chat_messages(
    message: str, encoded_images: Iterable[str], history: Optional[List[dict]] = None
) -> List[dict]:
    """Compose a chat payload compatible with multimodal LLaMA endpoints."""

    messages: List[dict] = list(history) if history else []
    content = [{"type": "text", "text": message}]
    for encoded_image in encoded_images:
        content.append({"type": "image", "image": encoded_image})
    messages.append({"role": "user", "content": content})
    return messages


SECRET_KEYWORDS = ("api_key", "token", "secret", "password", "key", "credential")
SECRET_VALUE_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9+/=_-]{20,})(?![A-Za-z0-9])")


def mask_secrets(text: str) -> str:
    """Mask potential secrets like API keys or tokens in *text*."""

    if not text:
        return text

    def _mask_keyword(match: re.Match[str]) -> str:
        key = match.group("keyword")
        sep = match.group("separator")
        leading_ws = match.group("leading_ws") or ""
        trailing_ws = match.group("trailing_ws") or ""
        raw_value = match.group("value")

        quote_prefix = ""
        quote_suffix = ""
        core_value = raw_value
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
            quote_prefix = raw_value[0]
            quote_suffix = raw_value[-1]
            core_value = raw_value[1:-1]

        if not core_value:
            masked_core = ""
        elif len(core_value) > 8:
            masked_core = f"{core_value[:4]}***{core_value[-4:]}"
        else:
            masked_core = "***"

        masked_value = f"{quote_prefix}{masked_core}{quote_suffix}"
        return f"{key}{leading_ws}{sep}{trailing_ws}{masked_value}"

    keyword_pattern = re.compile(
        r"(?P<keyword>" + "|".join(re.escape(keyword) for keyword in SECRET_KEYWORDS) + r")"
        r"(?P<leading_ws>\s*)"
        r"(?P<separator>[:=])"
        r"(?P<trailing_ws>\s*)"
        r"(?P<value>[^\s,;]+)",
        flags=re.IGNORECASE,
    )

    text = keyword_pattern.sub(_mask_keyword, text)

    def _mask_long_value(match: re.Match[str]) -> str:
        value = match.group(1)
        if "***" in value:
            return value
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}***{value[-4:]}"

    return SECRET_VALUE_PATTERN.sub(_mask_long_value, text)


def sanitize_messages(messages: Sequence[dict]) -> List[dict]:
    """Return a deep copy of *messages* with text entries masked for secrets."""

    sanitized: List[dict] = []
    for message in messages:
        content_items = []
        for item in message.get("content", []):
            if item.get("type") == "text":
                content_items.append({**item, "text": mask_secrets(str(item.get("text", "")))})
            else:
                content_items.append(dict(item))
        sanitized.append({**message, "content": content_items})
    return sanitized


DEFAULT_SECURITY_PORTS = (22, 80, 443, 8080, 8443)


def scan_network(
    hosts: Iterable[str], ports: Iterable[int], timeout: float = 0.5
) -> dict[str, list[int]]:
    """Attempt to connect to *ports* on each host and return open ports."""

    open_ports: dict[str, list[int]] = {}
    ports_list = sorted({int(port) for port in ports if int(port) > 0})
    for host in hosts:
        host_open_ports: list[int] = []
        for port in ports_list:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                try:
                    result = sock.connect_ex((host, port))
                except OSError:
                    continue
                if result == 0:
                    host_open_ports.append(port)
        if host_open_ports:
            open_ports[host] = host_open_ports
    return open_ports


class LlamaImageChat(Plugin):
    """Send text prompts with image attachments to a LLaMA-compatible endpoint."""

    def __init__(self):
        super().__init__()
        self.description = (
            "Send prompts, images, and maintain conversation history with a"
            " LLaMA-compatible API."
        )
        self.arguments = [
            {
                "arg": "--llama-chat",
                "help": "Send a request to a LLaMA-compatible endpoint with optional images.",
                "action": "store_true",
                "operation": True,
            },
            {
                "arg": "--llama-images",
                "nargs": "+",
                "help": "Path(s) to images that should be attached to the request.",
                "metavar": "IMAGE",
                "default": None,
            },
            {
                "arg": "--llama-message",
                "nargs": None,
                "help": "Prompt text that should be sent to the assistant.",
                "metavar": "TEXT",
                "default": None,
            },
            {
                "arg": "--llama-prompt-file",
                "nargs": None,
                "help": "Path to a file containing the prompt text.",
                "metavar": "FILE",
                "default": None,
            },
            {
                "arg": "--llama-model",
                "nargs": None,
                "help": "Model name to use when talking to the endpoint (default: llama3).",
                "metavar": "MODEL",
                "default": "llama3",
            },
            {
                "arg": "--llama-endpoint",
                "nargs": None,
                "help": "HTTP endpoint for the chat API (default: http://localhost:11434/api/chat).",
                "metavar": "URL",
                "default": "http://localhost:11434/api/chat",
            },
            {
                "arg": "--llama-history-file",
                "nargs": None,
                "help": "Optional JSON file storing the conversation history.",
                "metavar": "FILE",
                "default": None,
            },
            {
                "arg": "--llama-output-file",
                "nargs": None,
                "help": "Optional path to store the assistant response.",
                "metavar": "FILE",
                "default": None,
            },
            {
                "arg": "--llama-scan-hosts",
                "nargs": "+",
                "help": "Hostnames or IPs that should be scanned for open ports.",
                "metavar": "HOST",
                "default": None,
            },
            {
                "arg": "--llama-port-range",
                "nargs": 2,
                "type": int,
                "help": "Port range (inclusive) used during security scans.",
                "metavar": ("START", "END"),
                "default": None,
            },
            {
                "arg": "--llama-security-report",
                "nargs": None,
                "help": "Optional JSON file storing results of the security sweep.",
                "metavar": "FILE",
                "default": None,
            },
        ]

    def run(self, device, configs, storage, sessions, profile_filter, plugin):
        args = configs.args
        if not getattr(args, "llama_chat", False):
            logger.debug("LLaMA chat argument not enabled; skipping execution.")
            return

        security_report = self._security_sweep(args)
        if security_report:
            logger.info("Security sweep completed: %s", json.dumps(security_report, indent=2))

        message = self._get_prompt(args)
        if not message:
            logger.error("No prompt provided for the LLaMA chat request.")
            return

        images = self._load_images(args.llama_images)
        history, history_path = self._load_history(args.llama_history_file)

        payload = {
            "model": args.llama_model or "llama3",
            "messages": build_chat_messages(message, images, history),
        }

        sanitized_payload = dict(payload)
        sanitized_payload["messages"] = sanitize_messages(payload["messages"])
        logger.debug(
            "Sending LLaMA payload: %s",
            json.dumps(sanitized_payload, ensure_ascii=False, indent=2)[:500],
        )
        response_text = self._send_request(args.llama_endpoint, payload)
        if response_text is None:
            return

        sanitized_response = mask_secrets(response_text)
        self._persist_history(history, history_path, message, images, response_text)
        self._write_output(args.llama_output_file, sanitized_response)
        logger.info("LLaMA response: %s", sanitized_response)

    def wyy(
        self, message: str, role: str = "assistant", images: Optional[Iterable[str]] = None
    ) -> dict:
        """Create a conversation entry following the multimodal chat schema."""

        content = [{"type": "text", "text": message}]
        for encoded_image in images or []:
            content.append({"type": "image", "image": encoded_image})
        return {"role": role, "content": content}

    def _get_prompt(self, args) -> Optional[str]:
        if args.llama_message:
            return str(args.llama_message)
        if not args.llama_prompt_file:
            return None
        path = Path(args.llama_prompt_file)
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.error("Prompt file '%s' does not exist.", path)
        except OSError as exc:
            logger.error("Failed to read prompt file '%s': %s", path, exc)
        return None

    def _load_images(self, images: Optional[Iterable[str]]) -> List[str]:
        encoded_images: List[str] = []
        if not images:
            return encoded_images
        for image_path in images:
            path = Path(image_path)
            if not path.exists():
                logger.error("Image file '%s' not found. Skipping.", image_path)
                continue
            try:
                encoded_images.append(encode_image_to_base64(path))
            except OSError as exc:
                logger.error("Unable to read image '%s': %s", image_path, exc)
        return encoded_images

    def _load_history(
        self, history_file: Optional[str]
    ) -> tuple[Optional[List[dict]], Optional[Path]]:
        if not history_file:
            return None, None
        path = Path(history_file)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            return [], path
        try:
            with path.open("r", encoding="utf-8") as history_stream:
                data = json.load(history_stream)
            if isinstance(data, list):
                return data, path
            logger.warning("History file '%s' is not a list. Resetting history.", path)
            return [], path
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode history file '%s': %s", path, exc)
        except OSError as exc:
            logger.error("Failed to read history file '%s': %s", path, exc)
        return [], path

    def _send_request(self, endpoint: str, payload: dict) -> Optional[str]:
        try:
            response = requests.post(endpoint, json=payload, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to send request to '%s': %s", endpoint, exc)
            return None

        try:
            data = response.json()
        except ValueError:
            logger.error("Endpoint '%s' did not return valid JSON.", endpoint)
            return None

        # Handle both OpenAI-compatible and Ollama style responses.
        if isinstance(data, dict):
            if "message" in data and isinstance(data["message"], dict):
                return str(data["message"].get("content", "")).strip()
            if "response" in data:
                return str(data.get("response", "")).strip()
            if "choices" in data:
                choices = data["choices"]
                if isinstance(choices, list) and choices:
                    message = choices[0].get("message", {})
                    if isinstance(message, dict):
                        return str(message.get("content", "")).strip()
        logger.error(
            "Could not find an assistant message in the response from '%s'.", endpoint
        )
        return None

    def _persist_history(
        self,
        history: Optional[List[dict]],
        history_path: Optional[Path],
        message: str,
        images: List[str],
        response_text: str,
    ) -> None:
        if history_path is None:
            return
        updated_history = list(history or [])
        updated_history.append(
            self.wyy(mask_secrets(message), role="user", images=images)
        )
        updated_history.append(self.wyy(mask_secrets(response_text), role="assistant"))
        try:
            with history_path.open("w", encoding="utf-8") as history_stream:
                json.dump(updated_history, history_stream, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error(
                "Failed to write history file '%s': %s", history_path, exc
            )

    def _write_output(self, output_file: Optional[str], response_text: str) -> None:
        if not output_file:
            return
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(response_text, encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to write response file '%s': %s", path, exc)

    def _security_sweep(self, args) -> Optional[dict]:
        hosts = getattr(args, "llama_scan_hosts", None)
        if not hosts:
            return None

        port_range = getattr(args, "llama_port_range", None)
        if port_range and len(port_range) == 2:
            start, end = sorted(int(port) for port in port_range)
            ports = range(max(start, 1), end + 1)
        else:
            ports = DEFAULT_SECURITY_PORTS

        open_ports = scan_network(hosts, ports)
        sanitized_env = {
            key: "***MASKED***"
            for key in os.environ
            if any(keyword in key.lower() for keyword in SECRET_KEYWORDS)
        }
        report = {
            "network": open_ports,
            "environment": sanitized_env,
        }

        report_path = getattr(args, "llama_security_report", None)
        if report_path:
            try:
                path = Path(report_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            except OSError as exc:
                logger.error("Failed to write security report '%s': %s", report_path, exc)

        return report if (open_ports or sanitized_env) else {}
