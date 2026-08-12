from __future__ import annotations

import base64
from typing import Iterable

import numpy as np
import requests


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs):
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Could not reach Ollama at {self.base_url}. Start Ollama and make sure the requested model is installed. Details: {exc}"
            ) from exc

    def is_running(self) -> bool:
        try:
            self._request("GET", "/api/tags")
            return True
        except OllamaError:
            return False

    def installed_models(self) -> list[str]:
        payload = self._request("GET", "/api/tags")
        return [item.get("name", "") for item in payload.get("models", [])]

    def embed(self, texts: Iterable[str], model: str, batch_size: int = 24) -> np.ndarray:
        values = list(texts)
        if not values:
            return np.empty((0, 0), dtype=np.float32)
        vectors: list[list[float]] = []
        for start in range(0, len(values), batch_size):
            payload = self._request(
                "POST",
                "/api/embed",
                json={"model": model, "input": values[start : start + batch_size]},
            )
            vectors.extend(payload.get("embeddings", []))
        if len(vectors) != len(values):
            raise OllamaError("Ollama returned an unexpected number of embeddings.")
        matrix = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.clip(norms, 1e-12, None)

    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.1) -> str:
        payload = self._request(
            "POST",
            "/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {"temperature": temperature, "num_ctx": 8192},
            },
        )
        return payload.get("message", {}).get("content", "").strip()

    def vision(self, model: str, prompt: str, image_bytes: bytes) -> str:
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        payload = self._request(
            "POST",
            "/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_base64],
                    }
                ],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.0, "num_ctx": 8192},
            },
        )
        return payload.get("message", {}).get("content", "").strip()
