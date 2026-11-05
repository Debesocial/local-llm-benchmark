#!/usr/bin/env python3
"""Mock OpenAI/vLLM-compatible streaming server for testing llmload.py locally.

Usage:
  python mock_llm.py [PORT] [--reasoning N] [--throttle-after N] [--max-active N]

Endpoints:
  POST /v1/chat/completions  SSE streaming chat completions (optionally with reasoning tokens)
  GET  /metrics              vLLM-style Prometheus gauges (running, waiting, KV-cache usage)
"""
import argparse
import json
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFILL = 0.25         # Prompt processing / prefill latency (seconds)
PER_TOKEN = 0.012      # Generation latency per token (seconds)


class MockState:
    def __init__(self, reasoning=0, throttle_after=6, max_active=25):
        self.reasoning = reasoning            # reasoning tokens streamed before the answer
        self.throttle_after = throttle_after  # above this concurrency, simulate GPU contention
        self.max_active = max_active          # above this, reject with HTTP 429 (queue overflow)
        self.active = 0
        self.preemptions = 0
        self.lock = threading.Lock()

    def enter(self):
        with self.lock:
            if self.active >= self.max_active:
                return None
            self.active += 1
            return self.active

    def leave(self):
        with self.lock:
            self.active -= 1


def make_handler(state):
    class MockLLMHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send_empty(self, code):
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _chunk(self, payload):
            self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
            self.wfile.flush()

        def do_GET(self):
            if self.path.rstrip("/") != "/metrics":
                return self._send_empty(404)
            with state.lock:
                running = state.active
                preemptions = state.preemptions
            waiting = max(0, running - state.throttle_after)
            body = (
                "# TYPE vllm:num_requests_running gauge\n"
                'vllm:num_requests_running{model_name="mock"} %d\n'
                "# TYPE vllm:num_requests_waiting gauge\n"
                'vllm:num_requests_waiting{model_name="mock"} %d\n'
                "# TYPE vllm:kv_cache_usage_perc gauge\n"
                'vllm:kv_cache_usage_perc{model_name="mock"} %.4f\n'
                "# TYPE vllm:num_preemptions_total counter\n"
                'vllm:num_preemptions_total{model_name="mock"} %d\n'
            ) % (running, waiting, min(1.0, running / float(state.max_active)), preemptions)
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._send_empty(400)
            if not self.path.rstrip("/").endswith("/chat/completions"):
                return self._send_empty(404)

            active = state.enter()
            if active is None:  # Simulate queue overflow with HTTP 429
                return self._send_empty(429)
            try:
                max_tokens = int(body.get("max_tokens") or 50)
                messages = body.get("messages") or [{}]
                prompt_chars = sum(len(m.get("content") or "") for m in messages)
                load_factor = max(1.0, active / float(state.throttle_after))

                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                time.sleep((PREFILL + prompt_chars / 20000.0) * load_factor)
                if body.get("ignore_eos"):
                    answer_tokens = max_tokens
                else:
                    answer_tokens = min(max_tokens, max(int(body.get("min_tokens") or 0), random.randint(40, 90)))
                reasoning_tokens = min(state.reasoning, max(0, max_tokens - 1))
                answer_tokens = min(answer_tokens, max_tokens - reasoning_tokens)

                for i in range(reasoning_tokens):
                    time.sleep(PER_TOKEN * load_factor)
                    self._chunk({"choices": [{"index": 0, "delta": {"reasoning_content": "think%d " % i}}]})
                for i in range(answer_tokens):
                    time.sleep(PER_TOKEN * load_factor)
                    self._chunk({"choices": [{"index": 0, "delta": {"content": "token%d " % i}}]})
                if (body.get("stream_options") or {}).get("include_usage"):
                    self._chunk({"choices": [], "usage": {
                        "prompt_tokens": max(1, prompt_chars // 4),
                        "completion_tokens": reasoning_tokens + answer_tokens,
                        "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
                    }})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                state.leave()

    return MockLLMHandler


def make_server(port=8899, host="127.0.0.1", **kwargs):
    return ThreadingHTTPServer((host, port), make_handler(MockState(**kwargs)))


def cli(argv=None):
    """Console-script entry point (`llm-benchmark-mock`, `python mock_llm.py`)."""
    ap = argparse.ArgumentParser(description="Mock OpenAI-compatible streaming LLM server")
    ap.add_argument("port", nargs="?", type=int, default=8899)
    ap.add_argument("--reasoning", type=int, default=0, help="Reasoning tokens to stream before each answer")
    ap.add_argument("--throttle-after", type=int, default=6, help="Concurrency above which generation slows down")
    ap.add_argument("--max-active", type=int, default=25, help="Concurrency above which requests get HTTP 429")
    args = ap.parse_args(argv)
    server = make_server(args.port, reasoning=args.reasoning, throttle_after=args.throttle_after,
                         max_active=args.max_active)
    print("Mock LLM server running at http://127.0.0.1:%d/v1/chat/completions" % args.port)
    print("Prometheus metrics at       http://127.0.0.1:%d/metrics" % args.port)
    if args.reasoning:
        print("Streaming %d reasoning tokens before each answer." % args.reasoning)
    print("Press Ctrl+C to stop the mock server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMock LLM server stopped.")
        sys.exit(0)


if __name__ == "__main__":
    cli()
