#!/usr/bin/env python3
"""
llmload.py - LLM Server Load Testing & Benchmarking Tool (vLLM / LiteLLM / OpenAI-compatible APIs)

Goal: Determine maximum concurrent user capacity while maintaining responsive SLA standards.

Zero external dependencies: 100% pure Python 3.9+ standard library. No pip install needed.

Quick Start (Interactive Menu):
  Windows : run.bat or .\\run.ps1
  Linux   : ./run.sh
  or      : python llmload.py menu            (add --lang id for Bahasa Indonesia)

Headless CLI (for automation / CI-CD):
  python3 llmload.py baseline --url http://localhost:4000/v1/chat/completions --model qwen-30b
  python3 llmload.py ramp     --url ... --model ... --levels 5,10,20,30 --duration 300
  python3 llmload.py rate     --url ... --model ... --rates 0.5,1,2,4 --duration 120
  python3 llmload.py soak     --url ... --model ... --users 30 --duration 3600
  python3 llmload.py compare  hasil/ramp-A-summary.json hasil/ramp-B-summary.json
  python3 llmload.py report   hasil/soak-B-summary.json

Exit codes: 0 = SLA passed, 1 = setup/connection error, 2 = SLA failed, 130 = interrupted.
"""

import argparse
import csv
import getpass
import html
import http.client
import json
import math
import os
import platform
import random
import socket
import ssl
import sys
import threading
import time
import types
import urllib.error
import urllib.parse
import urllib.request

try:
    from llmload_lang import TRANSLATIONS
except ImportError:  # llmload.py copied on its own: English only
    TRANSLATIONS = {}

TOOL_NAME = "LLM Benchmark"
TOOL_VERSION = "2.0.0"
SCHEMA_VERSION = 2

EXIT_OK, EXIT_SETUP, EXIT_SLA_FAILED, EXIT_INTERRUPTED = 0, 1, 2, 130

# Terminal initialization for Windows ANSI & UTF-8 encoding
if sys.platform == "win32":
    try:
        os.system("")  # Enable ANSI/VT100 mode on Windows 10/11
    except Exception:
        pass
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

IS_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

# Set terminal window title if interactive (Linux, macOS, Windows Terminal)
if IS_TTY:
    try:
        sys.stdout.write("\033]0;%s\007" % TOOL_NAME)
        sys.stdout.flush()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Language (en / id)
# ---------------------------------------------------------------------------
LANGUAGES = {"en": "English", "id": "Bahasa Indonesia"}
LANG = "en"


def set_language(lang):
    global LANG
    lang = (lang or "en").strip().lower()
    LANG = lang if lang in LANGUAGES and (lang == "en" or lang in TRANSLATIONS) else "en"
    return LANG


def _(text):
    """Translate a user-facing English string (format placeholders are kept as-is)."""
    if LANG == "en":
        return text
    return TRANSLATIONS.get(LANG, {}).get(text, text)


set_language(os.environ.get("LLMLOAD_LANG", "en"))


# ---------------------------------------------------------------------------
# Simple & Clean Color Palette (Minimalist, easy on the eyes)
# ---------------------------------------------------------------------------
class C:
    R = "\033[0m"              # Reset to default
    BOLD = "\033[1m"           # Bold text
    DIM = "\033[90m"           # Subtle gray for borders & hints
    CYAN = "\033[36m"          # Soft cyan for menu numbers
    ORANGE = "\033[38;5;208m"  # Warm orange for Clawd mascot
    GREEN = "\033[32m"         # Green for [OK], [PASSED], Saved
    YELLOW = "\033[33m"        # Yellow for thinking & warnings
    RED = "\033[31m"           # Red for [FAILED]


# Plain output for CI logs, pipes, and users who opt out (https://no-color.org)
if not IS_TTY or os.environ.get("NO_COLOR"):
    for _attr in ("R", "BOLD", "DIM", "CYAN", "ORANGE", "GREEN", "YELLOW", "RED"):
        setattr(C, _attr, "")

CONFIG_NAME = "llmload.conf"


def default_config_path():
    """Where settings are stored.

    1. LLMLOAD_CONFIG overrides everything.
    2. A source checkout (pyproject.toml beside this file) or an existing llmload.conf beside this file keeps
       using that file, so existing setups and `python llmload.py` behave exactly as before.
    3. An installed package (pip/pipx) uses the per-user config directory, never site-packages.
    """
    override = os.environ.get("LLMLOAD_CONFIG")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    here = os.path.dirname(os.path.abspath(__file__))
    beside = os.path.join(here, CONFIG_NAME)
    if os.path.exists(beside) or os.path.exists(os.path.join(here, "pyproject.toml")):
        return beside
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, "llm-benchmark", CONFIG_NAME)


CONFIG_FILE = default_config_path()

# Global stop signal: set on Ctrl+C so every virtual user winds down and partial results are kept
STOP = threading.Event()
OUTPUT_LOCK = threading.Lock()

# Fewer successful requests than this makes p95/p99 equal to (or near) the maximum sample
MIN_SAMPLES = 20

# Minimum pause before a virtual user retries after a failed request
FAILURE_BACKOFF_S = 1.0

# Average English words per token, and typical adult silent reading speed (~240 wpm)
WORDS_PER_TOKEN = 0.75
READING_WORDS_PER_S = 4.0

# ---------------------------------------------------------------------------
# Default prompt dataset. Replace with real questions using --prompts file.txt
# (one question per line) to evaluate real-world production workload.
# ---------------------------------------------------------------------------
DEFAULT_PROMPTS = [
    "Explain what artificial intelligence (AI) is in simple terms for a beginner.",
    "Draft a concise email requesting two days of annual leave.",
    "Give 5 practical tips for maintaining a healthy and productive daily routine.",
    "How can someone create a realistic and organized monthly household budget?",
    "Explain the difference between the Internet and Wi-Fi in plain, accessible language.",
    "Suggest a healthy, nutritious breakfast idea that can be prepared in under 10 minutes.",
    "Write a short summary on why personal data security and privacy matter online.",
    "What are the best initial steps to take when starting to learn a new skill?",
]

# Indonesian counterpart of the defaults. Select with --prompts builtin:id (works without any file, so it also
# works from an installed package). Keep in sync with prompts-id.txt (checked by the test suite).
INDONESIAN_PROMPTS = [
    "Jelaskan apa itu kecerdasan buatan (AI) dengan bahasa sederhana untuk pemula.",
    "Buatkan email singkat untuk mengajukan cuti tahunan selama dua hari.",
    "Berikan 5 tips praktis untuk menjaga rutinitas harian yang sehat dan produktif.",
    "Bagaimana cara menyusun anggaran rumah tangga bulanan yang realistis dan teratur?",
    "Jelaskan perbedaan antara internet dan Wi-Fi dengan bahasa yang mudah dipahami.",
    "Sarankan ide sarapan sehat dan bergizi yang bisa disiapkan dalam waktu kurang dari 10 menit.",
    "Tuliskan ringkasan singkat mengapa keamanan dan privasi data pribadi penting saat online.",
    "Apa langkah awal terbaik ketika mulai mempelajari keterampilan baru?",
    "Bagaimana prosedur mengajukan klaim penggantian biaya asuransi kesehatan?",
    "Jelaskan kebijakan pengembalian barang dan dana untuk produk yang rusak saat diterima.",
]

BUILTIN_PREFIX = "builtin:"
BUILTIN_PROMPT_SETS = {"en": DEFAULT_PROMPTS, "id": INDONESIAN_PROMPTS}

FILLER = (
    "This document outlines standard corporate operational procedures, covering inter-departmental "
    "workflows, assigned responsibilities for each team member, and periodic reporting requirements "
    "mandated across all operational business units. "
)
FILLER_WORDS = FILLER.split()

DEFAULTS = {
    "lang": "en",
    "url": "http://localhost:4000/v1/chat/completions",
    "model": "",
    "key": "",
    "save_key": False,
    "max_tokens": 400,
    "min_tokens": 0,
    "ignore_eos": False,
    "temperature": 0.7,
    "prompts": None,
    "pad_words": "0",
    "system_words": 0,
    "prefix_mode": "shared",
    "turns": 1,
    "think_min": 10.0,
    "think_max": 60.0,
    "stagger": 10.0,
    "warmup": 30.0,
    "cooldown": 5.0,
    "timeout": 300.0,
    "seed": 42,
    "usage": True,
    "insecure": False,
    "out": "hasil",
    "html": True,
    "quiet": False,
    "target_ttft": 3.0,
    "target_error": 0.01,
    "target_tps": 15.0,
    "ttft_basis": "token",
    "requests": 10,
    "levels": "5,10,20,30",
    "rates": "0.5,1,2,4",
    "arrival": "poisson",
    "max_concurrency": 128,
    "duration": 300,
    "level_pause": 30,
    "users": 30,
    "metrics_url": "",
    "metrics_interval": 5.0,
}

# Config keys renamed since v1; old llmload.conf files are migrated on load
LEGACY_CONFIG_KEYS = {"jeda_level": "level_pause"}

# Streaming delta fields used by reasoning models (DeepSeek-R1, Qwen3, QwQ, gpt-oss ...)
REASONING_FIELDS = ("reasoning_content", "reasoning")

CSV_COLUMNS = [
    "stage", "load", "user", "turn", "started_s", "finished_s", "status", "error_detail",
    "ttft_s", "ttfa_s", "e2e_s", "queue_wait_s", "input_tokens", "output_tokens",
    "reasoning_tokens", "token_source", "tok_per_s", "tpot_ms", "itl_p50_ms", "itl_p95_ms",
    "itl_max_ms", "prompt_chars",
]

# Server-side gauges scraped from Prometheus /metrics (first matching name wins)
SERVER_METRICS = [
    ("running", ("vllm:num_requests_running", "llamacpp:requests_processing",
                 "sglang:num_running_reqs", "tgi_batch_current_size")),
    ("waiting", ("vllm:num_requests_waiting", "llamacpp:requests_deferred",
                 "sglang:num_queue_reqs", "tgi_queue_size")),
    ("kv_cache_pct", ("vllm:kv_cache_usage_perc", "vllm:gpu_cache_usage_perc",
                      "llamacpp:kv_cache_usage_ratio", "sglang:token_usage")),
    ("preemptions", ("vllm:num_preemptions_total",)),
]
COUNTER_METRICS = {"preemptions"}
FRACTION_METRICS = {"kv_cache_pct"}

ERROR_HINTS = [
    ("http_429", "HTTP 429: the server or gateway is rate limiting; raise provider limits or lower the load."),
    ("http_5", "HTTP 5xx: the backend or gateway failed under load; check server logs for OOM or crashes."),
    ("http_4", "HTTP 4xx: the request was rejected; verify model name, API key and request parameters."),
    ("timeout", "Timeouts: the server is overloaded or --timeout is too low for long generations."),
    ("conn_error", "Connection errors: the server refused, dropped or reset connections (crash/restart?)."),
    ("protocol_error", "Protocol errors: the stream was cut off mid-response."),
    ("no_answer", "No answer: the model spent all max_tokens on reasoning; raise --max-tokens."),
    ("stream_error", "Stream errors: the server reported an error inside the SSE stream."),
    ("client_overflow", "Client overflow: requests piled up faster than the server completed them."),
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def now():
    return time.perf_counter()


def percentile(values, p):
    """Nearest-rank percentile, consistent with standard inference benchmarks."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = max(0, math.ceil(p / 100.0 * len(vals)) - 1)
    return vals[k]


def mean(values):
    vals = [v for v in values if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def parse_range(text):
    """Parse '2000' or '500-4000' into an inclusive (low, high) word range."""
    raw = str(text if text not in (None, "") else "0").replace(" ", "")
    if "-" in raw:
        lo_txt, hi_txt = raw.split("-", 1)
        lo, hi = int(lo_txt), int(hi_txt)
    else:
        lo = hi = int(raw)
    if lo < 0 or hi < lo:
        raise ValueError("invalid range %r (use N or MIN-MAX)" % text)
    return lo, hi


def parse_number_list(text, kind=float):
    values = [kind(x) for x in str(text).replace(" ", "").split(",") if x]
    if not values or any(v <= 0 for v in values):
        raise ValueError("expected a comma-separated list of positive numbers, got %r" % text)
    return values


def filler_text(n_words):
    if n_words <= 0:
        return ""
    reps = n_words // len(FILLER_WORDS) + 1
    return " ".join((FILLER_WORDS * reps)[:n_words])


def fmt_num(v, pattern="%.2f", none="-"):
    return none if v is None else pattern % v


def fmt_s(v):
    return fmt_num(v, "%.2fs")


def fmt_pct(v):
    return fmt_num(None if v is None else v * 100, "%.1f%%")


def fmt_load(value, unit="users"):
    if value is None:
        return "-"
    if unit == "req/s":
        return "%g req/s" % value
    value = int(value)
    return (_("%d user") if value == 1 else _("%d users")) % value


def summary_load(s):
    return fmt_load(s.get("load"), s.get("load_unit", "users"))


def round_floats(obj, digits=4):
    if isinstance(obj, float):
        return round(obj, digits) if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: round_floats(v, digits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_floats(v, digits) for v in obj]
    return obj


def write_line(text=""):
    """Print a full line without clobbering the live progress line."""
    with OUTPUT_LOCK:
        sys.stdout.write(("\r\033[K" if IS_TTY else "") + text + "\n")
        sys.stdout.flush()


def write_status(text):
    """Overwrite the single live status line (TTY only; CI logs stay clean)."""
    if not IS_TTY:
        return
    with OUTPUT_LOCK:
        sys.stdout.write("\r\033[K" + text)
        sys.stdout.flush()


def clear_status():
    if IS_TTY:
        with OUTPUT_LOCK:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()


def rule(char="=", width=78):
    print(C.DIM + char * width + C.R)


def kv_line(label, value, width=15):
    print("  %-*s: %s" % (width, label, value))


def section(title):
    print("\n%s--- %s%s%s%s ---%s" % (C.CYAN, C.BOLD, title, C.R, C.CYAN, C.R))


def interruptible_sleep(seconds):
    """Sleep that reports Ctrl+C instead of raising. Returns True if interrupted."""
    try:
        end = now() + seconds
        while now() < end:
            time.sleep(min(0.25, end - now()))
        return False
    except KeyboardInterrupt:
        STOP.set()
        return True


# ---------------------------------------------------------------------------
# SSE stream parsing & single request worker
# ---------------------------------------------------------------------------
def iter_sse_data(lines):
    """Yield decoded JSON payloads from an SSE line stream; stops at [DONE]."""
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            return
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def build_payload(cfg, messages):
    body = {
        "model": cfg.model,
        "stream": True,
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
        "messages": messages,
    }
    if cfg.usage:
        # Request server to report actual token usage in the final stream chunk
        body["stream_options"] = {"include_usage": True}
    if cfg.min_tokens:
        body["min_tokens"] = cfg.min_tokens  # vLLM extension: fixes output length
    if cfg.ignore_eos:
        body["ignore_eos"] = True  # vLLM extension: always generate max_tokens
    return body


def _error_text(err):
    if isinstance(err, dict):
        return str(err.get("message") or err.get("type") or err)[:200]
    return str(err)[:200]


def send_request(cfg, messages, opener, on_progress=None, keep_text=False):
    """Send one streaming chat request and measure its latency profile.

    Timing points:
      ttft  - first streamed token of any kind (reasoning or answer)
      ttfa  - first token of the visible answer (equals ttft for non-reasoning models)
      e2e   - full duration until the stream ends
    """
    prompt_chars = sum(len(m.get("content") or "") for m in messages)
    t0 = now()
    first_any = first_answer = last_chunk = None
    gaps = []
    content_chunks = reasoning_chunks = 0
    usage = None
    text_parts = []
    status, detail = "ok", ""

    def progress(stage):
        if on_progress:
            try:
                on_progress(stage, content_chunks + reasoning_chunks, t0,
                            None if first_any is None else first_any - t0)
            except Exception:
                pass

    progress("sending")
    try:
        if not (cfg.url.startswith("http://") or cfg.url.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        req = urllib.request.Request(cfg.url, data=json.dumps(build_payload(cfg, messages)).encode("utf-8"),
                                     method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "text/event-stream")
        if cfg.key:
            req.add_header("Authorization", "Bearer " + cfg.key)

        with opener.open(req, timeout=cfg.timeout) as resp:
            progress("connected")
            for obj in iter_sse_data(resp):
                if STOP.is_set():
                    status = "aborted"
                    break
                if obj.get("error"):
                    status, detail = "stream_error", _error_text(obj["error"])
                    break
                if isinstance(obj.get("usage"), dict):
                    usage = obj["usage"]
                for choice in obj.get("choices") or []:
                    delta = choice.get("delta") or {}
                    reasoning = next((delta[k] for k in REASONING_FIELDS if delta.get(k)), None)
                    content = delta.get("content")
                    if not reasoning and not content:
                        continue
                    t = now()
                    if first_any is None:
                        first_any = t
                    else:
                        gaps.append(t - last_chunk)
                    last_chunk = t
                    if reasoning:
                        reasoning_chunks += 1
                    if content:
                        content_chunks += 1
                        if first_answer is None:
                            first_answer = t
                        if keep_text:
                            text_parts.append(content)
                    progress("answering" if first_answer is not None else "reasoning")
    except urllib.error.HTTPError as e:
        status = "http_%d" % e.code
        try:
            detail = e.read(300).decode("utf-8", "replace").strip()
        except Exception:
            detail = str(e.reason)
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason).lower():
            status = "timeout"
        else:
            status = "conn_error"
        detail = str(reason)[:200]
    except (socket.timeout, TimeoutError) as e:
        status, detail = "timeout", str(e)[:200]
    except http.client.HTTPException as e:
        status, detail = "protocol_error", "%s: %s" % (type(e).__name__, e)
    except OSError as e:
        status, detail = "conn_error", str(e)[:200]
    except ValueError as e:
        status, detail = "invalid_url", str(e)[:200]
    except Exception as e:  # Safety guard so a single failure never crashes the load test
        status, detail = type(e).__name__, str(e)[:200]

    e2e = now() - t0
    if status == "ok" and first_any is None:
        status = "empty_response"
    elif status == "ok" and first_answer is None:
        status, detail = "no_answer", "only reasoning tokens were streamed"

    completion = usage.get("completion_tokens") if usage else None
    details = (usage or {}).get("completion_tokens_details") or {}
    if completion:
        output_tokens, source = completion, "usage"
    else:
        output_tokens, source = content_chunks + reasoning_chunks, "chunks"
    reasoning_tokens = details.get("reasoning_tokens") or reasoning_chunks

    ttft = None if first_any is None else first_any - t0
    tpot = None
    if ttft is not None and output_tokens and output_tokens > 1 and e2e > ttft:
        tpot = (e2e - ttft) / (output_tokens - 1)

    rec = {
        "status": status,
        "error_detail": detail.replace("\n", " ")[:200],
        "ttft_s": ttft,
        "ttfa_s": None if first_answer is None else first_answer - t0,
        "e2e_s": e2e,
        "input_tokens": usage.get("prompt_tokens") if usage else None,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "token_source": source,
        "tok_per_s": (1.0 / tpot) if tpot else None,
        "tpot_ms": tpot * 1000 if tpot else None,
        "itl_p50_ms": None if not gaps else percentile(gaps, 50) * 1000,
        "itl_p95_ms": None if not gaps else percentile(gaps, 95) * 1000,
        "itl_max_ms": None if not gaps else max(gaps) * 1000,
        "prompt_chars": prompt_chars,
        "_gaps": gaps,
    }
    if keep_text:
        rec["_text"] = "".join(text_parts)
    return rec


# ---------------------------------------------------------------------------
# Workload: prompt shaping (documents, system prefix, multi-turn history)
# ---------------------------------------------------------------------------
class Workload:
    def __init__(self, cfg, prompts):
        self.prompts = prompts
        self.pad_range = parse_range(cfg.pad_words)
        self.turns = max(1, int(cfg.turns or 1))
        self.prefix_mode = cfg.prefix_mode
        self.system_words = int(cfg.system_words or 0)
        self.system_text = ""
        if self.system_words > 0:
            self.system_text = ("You are a helpful assistant. Apply the operating guidelines below when relevant.\n"
                                + filler_text(self.system_words))

    def system_prompt(self, nonce):
        if not self.system_text:
            return ""
        if self.prefix_mode == "unique":
            # A unique leading line defeats server-side prefix caching
            return "Session %s.\n%s" % (nonce, self.system_text)
        return self.system_text

    def wrap_document(self, prompt, rng):
        lo, hi = self.pad_range
        if hi <= 0:
            return prompt
        n = rng.randint(lo, hi) if hi > lo else hi
        if n <= 0:
            return prompt
        return "Here is the reference document:\n" + filler_text(n) + "\n\nQuestion: " + prompt

    def new_conversation(self, rng):
        return Conversation(self, rng)

    def describe(self):
        parts = []
        lo, hi = self.pad_range
        if hi > 0:
            parts.append(_("document %s words") % (hi if lo == hi else "%d-%d" % (lo, hi)))
        if self.system_words:
            parts.append(_("system prompt %d words (%s prefix)") % (self.system_words, self.prefix_mode))
        if self.turns > 1:
            parts.append(_("%d-turn conversations") % self.turns)
        return ", ".join(parts) or _("single-turn chat")


class Conversation:
    """Per-user chat state. With turns > 1 the history grows, like a real chat session."""

    def __init__(self, workload, rng):
        self.w = workload
        self.rng = rng
        self.reset()

    def reset(self):
        self.history = []
        self.turn = 0
        self.nonce = "%08x" % self.rng.getrandbits(32)
        self.pending = None

    def messages(self, prompt):
        self.turn += 1
        msgs = []
        system = self.w.system_prompt(self.nonce)
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(self.history)
        content = prompt if self.history else self.w.wrap_document(prompt, self.rng)
        self.pending = {"role": "user", "content": content}
        msgs.append(self.pending)
        return msgs

    def advance(self, rec):
        text = rec.pop("_text", None)
        if self.w.turns <= 1 or rec["status"] != "ok" or text is None or self.turn >= self.w.turns:
            self.reset()
            return
        self.history.extend([self.pending, {"role": "assistant", "content": text}])


# ---------------------------------------------------------------------------
# Server metrics scraping (Prometheus text format: vLLM, llama.cpp, SGLang, TGI)
# ---------------------------------------------------------------------------
def parse_prometheus(text):
    """Return {metric_name: value summed across label sets}."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "{" in line and "}" in line:
            name = line[:line.index("{")]
            rest = line[line.rindex("}") + 1:].split()
        else:
            parts = line.split()
            name, rest = parts[0], parts[1:]
        if not rest:
            continue
        try:
            value = float(rest[0])
        except ValueError:
            continue
        if math.isnan(value):
            continue
        out[name] = out.get(name, 0.0) + value
    return out


def pick_server_metrics(raw):
    sample = {}
    for label, names in SERVER_METRICS:
        for name in names:
            if name in raw:
                value = raw[name]
                sample[label] = value * 100.0 if label in FRACTION_METRICS else value
                break
    return sample


def resolve_metrics_url(cfg):
    url = (cfg.metrics_url or "").strip()
    if url.lower() != "auto":
        return url
    parts = urllib.parse.urlsplit(cfg.url)
    return "%s://%s/metrics" % (parts.scheme, parts.netloc)


def fetch_metrics(url, opener, timeout=5.0):
    req = urllib.request.Request(url, method="GET")
    with opener.open(req, timeout=timeout) as resp:
        return pick_server_metrics(parse_prometheus(resp.read().decode("utf-8", "replace")))


class MetricsPoller:
    def __init__(self, url, interval, opener, t_start):
        self.url, self.interval, self.opener, self.t_start = url, max(1.0, interval), opener, t_start
        self.samples, self.errors = [], 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        while not self._stop.is_set():
            try:
                sample = fetch_metrics(self.url, self.opener)
                self.samples.append((now() - self.t_start, sample))
            except Exception:
                self.errors += 1
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=6)
        return self

    def summary(self, start, end):
        window = [(t, s) for t, s in self.samples if start <= t <= end] or self.samples
        result = {"url": self.url, "samples": len(window), "errors": self.errors, "metrics": {}, "timeline": []}
        labels = sorted({k for _t, s in window for k in s})
        for label in labels:
            vals = [s[label] for _t, s in window if label in s]
            if label in COUNTER_METRICS:
                result["metrics"][label] = {"delta": vals[-1] - vals[0]}
            else:
                result["metrics"][label] = {"avg": mean(vals), "max": max(vals)}
        result["timeline"] = [[t, s] for t, s in self.samples]
        return result


def start_poller(cfg, opener, t_start):
    url = resolve_metrics_url(cfg)
    if not url:
        return None
    return MetricsPoller(url, cfg.metrics_interval, opener, t_start).start()


# ---------------------------------------------------------------------------
# Shared stage state & live progress
# ---------------------------------------------------------------------------
class StageState:
    def __init__(self):
        self.lock = threading.Lock()
        self.records = []
        self.in_flight = 0
        self.pending = 0

    def begin(self):
        with self.lock:
            self.in_flight += 1

    def end(self):
        with self.lock:
            self.in_flight -= 1

    def add(self, rec):
        with self.lock:
            self.records.append(rec)

    def counts(self):
        with self.lock:
            done = len(self.records)
            failed = sum(1 for r in self.records if r["status"] not in ("ok", "aborted"))
            return done, failed, self.in_flight

    def snapshot(self):
        with self.lock:
            return list(self.records)


SPINNER = "|/-\\"


def show_progress(state, t_start, t_stop, tick):
    done, failed, in_flight = state.counts()
    t = now()
    if t < t_stop:
        tail = _("remaining %.0fs") % (t_stop - t)
    else:
        tail = _("draining %d in-flight") % in_flight
    failed_txt = "0" if failed == 0 else "%s%d%s" % (C.RED, failed, C.R)
    write_status("  %s [%4.0fs] " % (SPINNER[tick % 4], t - t_start)
                 + _("answered: %d (failed: %s) | in-flight: %d | %s") % (done, failed_txt, in_flight, tail))


def log_request(cfg, rec, prompt, who):
    if cfg.quiet:
        return
    snippet = prompt.replace("\n", " ")
    snippet = (snippet[:35] + "...") if len(snippet) > 35 else snippet
    if rec["status"] == "ok":
        mark = "%s[OK]%s" % (C.GREEN, C.R)
    elif rec["status"] == "aborted":
        mark = "%s[ABORTED]%s" % (C.YELLOW, C.R)
    else:
        mark = "%s[FAILED:%s]%s" % (C.RED, rec["status"], C.R)
    write_line("  [%s] \"%s\" -> %.1fs (TTFT %s | %d tok | %s tok/s) %s" % (
        who, snippet, rec["e2e_s"], fmt_s(rec["ttft_s"]), rec["output_tokens"] or 0,
        fmt_num(rec["tok_per_s"], "%.0f"), mark))


# ---------------------------------------------------------------------------
# Load generators
# ---------------------------------------------------------------------------
def user_loop(cfg, workload, opener, uid, state, t_start, t_stop):
    """Closed-loop virtual user: ask -> read answer (think time) -> ask again."""
    rng = random.Random(cfg.seed + uid)
    # Stagger initial start times to avoid artificial burst concurrency
    if STOP.wait(rng.uniform(0, cfg.stagger)):
        return
    conv = workload.new_conversation(rng)
    while now() < t_stop and not STOP.is_set():
        prompt = rng.choice(workload.prompts)
        messages = conv.messages(prompt)
        turn = conv.turn
        started = now()
        state.begin()
        try:
            rec = send_request(cfg, messages, opener, keep_text=workload.turns > 1)
        finally:
            state.end()
        rec.update(user=uid, turn=turn, started_s=started - t_start, finished_s=now() - t_start)
        conv.advance(rec)
        state.add(rec)
        log_request(cfg, rec, prompt, "User %d" % (uid + 1))
        if now() >= t_stop:
            break
        pause = rng.uniform(cfg.think_min, cfg.think_max)
        if rec["status"] != "ok":
            # Real users retry after a moment; without this, instant 429s turn into a hot loop
            pause = max(pause, FAILURE_BACKOFF_S)
        if STOP.wait(pause):
            break


def _announce_interrupt():
    clear_status()
    write_line("  %s%s%s" % (C.YELLOW, _("Interrupted - stopping virtual users and keeping partial results..."), C.R))


def _join_all(threads, seconds=3.0):
    deadline = now() + seconds
    for th in threads:
        th.join(max(0.0, deadline - now()))


def _wait_threads(threads, state, t_start, t_stop):
    """Wait for worker threads while showing progress. Returns True on Ctrl+C."""
    tick = 0
    try:
        while any(th.is_alive() for th in threads):
            show_progress(state, t_start, t_stop, tick)
            tick += 1
            time.sleep(0.3)
        return False
    except KeyboardInterrupt:
        STOP.set()
        _announce_interrupt()
        _join_all(threads)
        return True


def eval_window(cfg, planned, elapsed):
    """Measurement window: skip warmup, trim cooldown, never extend past what actually ran."""
    start = cfg.warmup
    end = min(planned - cfg.cooldown, elapsed)
    if end <= start:
        return 0.0, max(elapsed, 1e-6)
    return start, end


def _finish_stage(cfg, state, poller, t_start, duration, load, unit, stage, interrupted):
    clear_status()
    elapsed = now() - t_start
    records = state.snapshot()
    for r in records:
        r["stage"], r["load"] = stage, load
    window = eval_window(cfg, duration, elapsed)
    summary = summarize(cfg, records, window, load, unit)
    summary["elapsed_s"] = elapsed
    if poller:
        poller.stop()
        summary["server_metrics"] = poller.summary(*window)
    summary["interrupted"] = interrupted
    return summary, records


def run_closed_loop(cfg, workload, opener, users, duration, label, stage=1):
    write_line("\n>>> " + _("%s | %d concurrent users | %ds (warmup %ds)") % (label, users, duration, int(cfg.warmup)))
    state = StageState()
    t_start = now()
    t_stop = t_start + duration
    poller = start_poller(cfg, opener, t_start)
    threads = [threading.Thread(target=user_loop, args=(cfg, workload, opener, uid, state, t_start, t_stop),
                                daemon=True) for uid in range(users)]
    for th in threads:
        th.start()
    interrupted = _wait_threads(threads, state, t_start, t_stop)
    return _finish_stage(cfg, state, poller, t_start, duration, users, "users", stage, interrupted)


def run_open_loop(cfg, workload, opener, rate, duration, label, stage=1):
    """Open-loop arrivals at a fixed rate: load does not back off when the server slows down."""
    write_line("\n>>> " + _("%s | %g req/s (%s arrivals) | %ds (warmup %ds)")
               % (label, rate, cfg.arrival, duration, int(cfg.warmup)))
    state = StageState()
    sem = threading.Semaphore(cfg.max_concurrency)
    rng = random.Random(cfg.seed * 7919 + int(rate * 1000))
    t_start = now()
    t_stop = t_start + duration
    poller = start_poller(cfg, opener, t_start)

    def gap():
        return rng.expovariate(rate) if cfg.arrival == "poisson" else 1.0 / rate

    def fire(idx, scheduled):
        local = random.Random(cfg.seed * 1000003 + idx)
        try:
            while not sem.acquire(timeout=0.25):
                if STOP.is_set():
                    return
            try:
                if STOP.is_set():
                    return
                prompt = local.choice(workload.prompts)
                messages = workload.new_conversation(local).messages(prompt)
                sent = now()
                state.begin()
                try:
                    rec = send_request(cfg, messages, opener)
                finally:
                    state.end()
            finally:
                sem.release()
            rec.update(user=idx, turn=1, started_s=scheduled - t_start, finished_s=now() - t_start,
                       queue_wait_s=sent - scheduled)
            state.add(rec)
            log_request(cfg, rec, prompt, "Req %d" % (idx + 1))
        finally:
            with state.lock:
                state.pending -= 1

    threads, idx, tick, last_tick = [], 0, 0, 0.0
    next_t = t_start + gap()
    try:
        while not STOP.is_set():
            t = now()
            if next_t >= t_stop:
                break
            if t >= next_t:
                with state.lock:
                    overflow = state.pending >= cfg.max_concurrency * 4
                    if not overflow:
                        state.pending += 1
                if overflow:
                    state.add({"status": "client_overflow", "error_detail": "client backlog full", "e2e_s": 0.0,
                               "user": idx, "turn": 1, "started_s": next_t - t_start,
                               "finished_s": next_t - t_start, "output_tokens": 0, "_gaps": []})
                else:
                    th = threading.Thread(target=fire, args=(idx, next_t), daemon=True)
                    th.start()
                    threads.append(th)
                idx += 1
                next_t += gap()
                continue
            if t - last_tick >= 0.3:
                show_progress(state, t_start, t_stop, tick)
                tick += 1
                last_tick = t
                threads = [th for th in threads if th.is_alive()]
            time.sleep(min(0.05, max(0.0, next_t - t)))
        # Wait out the remaining stage time, then drain in-flight requests
        while now() < t_stop and not STOP.is_set():
            show_progress(state, t_start, t_stop, tick)
            tick += 1
            time.sleep(min(0.3, max(0.0, t_stop - now())))
    except KeyboardInterrupt:
        STOP.set()
        _announce_interrupt()
        _join_all(threads)
        return _finish_stage(cfg, state, poller, t_start, duration, rate, "req/s", stage, True)
    interrupted = _wait_threads(threads, state, t_start, t_stop)
    return _finish_stage(cfg, state, poller, t_start, duration, rate, "req/s", stage, interrupted)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------
def ttft_key(targets):
    return "ttfa" if getattr(targets, "ttft_basis", "token") == "answer" else "ttft"


def meets_request_sla(r, targets):
    """Per-request SLA check used for goodput."""
    first = r.get("ttfa_s") if ttft_key(targets) == "ttfa" else r.get("ttft_s")
    if first is None or first > targets.target_ttft:
        return False
    tps = r.get("tok_per_s")
    return not (targets.target_tps and tps is not None and tps < targets.target_tps)


def summarize(cfg, records, window, load, unit):
    """Compute stage metrics from requests that STARTED inside the measurement window.

    Selecting by start time (not finish time) keeps slow requests that run past the end
    of the stage, so tail latency and error rate are not flattered.
    """
    start, end = window
    valid = [r for r in records if r["status"] != "aborted"]
    rows = [r for r in valid if start <= r["started_s"] < end]
    if not rows and valid:
        rows = valid
        start, end = 0.0, max([r["finished_s"] for r in valid] + [end])
    span = max(end - start, 1e-6)

    ok = [r for r in rows if r["status"] == "ok"]
    reasons = {}
    for r in rows:
        if r["status"] != "ok":
            reasons[r["status"]] = reasons.get(r["status"], 0) + 1
    gaps = [g for r in ok for g in (r.get("_gaps") or [])]
    reasoning = [r for r in ok if (r.get("reasoning_tokens") or 0) > 0]
    good = [r for r in ok if meets_request_sla(r, cfg)]
    prefill = [r["input_tokens"] / r["ttft_s"] for r in ok if r.get("input_tokens") and r.get("ttft_s")]

    def col(key, src=ok):
        return [r.get(key) for r in src]

    tps = [v for v in col("tok_per_s") if v]
    return {
        "load": load,
        "load_unit": unit,
        "n_total": len(rows),
        "n_ok": len(ok),
        "error_rate": (1 - len(ok) / len(rows)) if rows else None,
        "failure_reasons": reasons,
        "window_s": span,
        "req_per_s": len(ok) / span,
        "goodput_req_per_s": len(good) / span,
        "goodput_ratio": (len(good) / len(rows)) if rows else None,
        "output_tok_per_s": sum(r.get("output_tokens") or 0 for r in ok) / span,
        "input_tok_per_s": (sum(r.get("input_tokens") or 0 for r in ok) / span) if any(col("input_tokens")) else None,
        "ttft_p50": percentile(col("ttft_s"), 50),
        "ttft_p95": percentile(col("ttft_s"), 95),
        "ttft_p99": percentile(col("ttft_s"), 99),
        "ttfa_p50": percentile(col("ttfa_s"), 50),
        "ttfa_p95": percentile(col("ttfa_s"), 95),
        "e2e_p50": percentile(col("e2e_s"), 50),
        "e2e_p95": percentile(col("e2e_s"), 95),
        "e2e_p99": percentile(col("e2e_s"), 99),
        "tpot_ms_p50": percentile(col("tpot_ms"), 50),
        "tpot_ms_p95": percentile(col("tpot_ms"), 95),
        "itl_ms_p50": None if not gaps else percentile(gaps, 50) * 1000,
        "itl_ms_p95": None if not gaps else percentile(gaps, 95) * 1000,
        "itl_ms_p99": None if not gaps else percentile(gaps, 99) * 1000,
        "tok_per_s_avg": mean(tps),
        "tok_per_s_p50": percentile(tps, 50),
        "tok_per_s_p5": percentile(tps, 5),
        "avg_input_tokens": mean(col("input_tokens")),
        "avg_output_tokens": mean(col("output_tokens")),
        "avg_reasoning_tokens": mean(col("reasoning_tokens", reasoning)),
        "reasoning_share": (len(reasoning) / len(ok)) if ok else None,
        "prefill_tok_per_s_p50": percentile(prefill, 50),
        "queue_wait_p95": percentile([r.get("queue_wait_s") for r in rows], 95),
        "token_source": "usage" if ok and all(r.get("token_source") == "usage" for r in ok) else "chunks",
        "low_sample": len(ok) < MIN_SAMPLES,
    }


def sla_failures(s, targets):
    """Return [(code, text)] describing why a stage misses the SLA (empty list = passed)."""
    out = []
    key = "%s_p95" % ttft_key(targets)
    label = _("First-answer p95") if key == "ttfa_p95" else "TTFT p95"
    value = s.get(key)
    if not s.get("n_ok"):
        out.append(("errors", _("no successful requests")))
        return out
    if value is None or value > targets.target_ttft:
        out.append(("ttft", "%s %s > %.1fs" % (label, fmt_s(value), targets.target_ttft)))
    err = s.get("error_rate")
    if err is not None and err > targets.target_error:
        out.append(("errors", _("errors %.1f%% > %.1f%%") % (err * 100, targets.target_error * 100)))
    tps = s.get("tok_per_s_avg")
    if targets.target_tps and tps is not None and tps < targets.target_tps:
        out.append(("tps", _("speed %.1f tok/s < %.0f tok/s") % (tps, targets.target_tps)))
    return out


def overall_verdict(summaries, targets):
    passing = [s for s in summaries if not sla_failures(s, targets)]
    if summaries and len(passing) == len(summaries):
        return "passed", passing
    return ("partial" if passing else "failed"), passing


def choose_bucket(span):
    for b in (10, 15, 30, 60, 120, 300, 600, 900):
        if span / b <= 30:
            return b
    return 1800


def build_timeline(records, window, bucket=None):
    start, end = window
    bucket = bucket or choose_bucket(end - start)
    rows = [r for r in records if r["status"] != "aborted" and start <= r["started_s"] < end]
    out = []
    t = start
    while t < end:
        b = [r for r in rows if t <= r["started_s"] < t + bucket]
        ok = [r for r in b if r["status"] == "ok"]
        out.append({
            "t_start": t,
            "t_end": min(t + bucket, end),
            "n": len(b),
            "n_ok": len(ok),
            "error_rate": (1 - len(ok) / len(b)) if b else None,
            "ttft_p50": percentile([r.get("ttft_s") for r in ok], 50),
            "ttft_p95": percentile([r.get("ttft_s") for r in ok], 95),
            "tok_per_s_avg": mean([r.get("tok_per_s") for r in ok]),
        })
        t += bucket
    return out


def analyze_drift(records, window):
    """Compare the first and last third of the window to spot leaks or queue buildup."""
    start, end = window
    third = (end - start) / 3.0
    ok = [r for r in records if r["status"] == "ok" and start <= r["started_s"] < end]
    first = [r for r in ok if r["started_s"] < start + third]
    last = [r for r in ok if r["started_s"] >= end - third]
    result = {"first_n": len(first), "last_n": len(last), "verdict": "insufficient data"}
    if len(first) < 5 or len(last) < 5:
        return result
    f_ttft = percentile([r["ttft_s"] for r in first], 95)
    l_ttft = percentile([r["ttft_s"] for r in last], 95)
    f_tps = mean([r.get("tok_per_s") for r in first])
    l_tps = mean([r.get("tok_per_s") for r in last])
    result.update(first_ttft_p95=f_ttft, last_ttft_p95=l_ttft, first_tok_per_s=f_tps, last_tok_per_s=l_tps)
    degraded = l_ttft > f_ttft * 1.25 and (l_ttft - f_ttft) > 0.25
    if f_tps and l_tps and l_tps < f_tps * 0.8:
        degraded = True
    result["verdict"] = "degrading" if degraded else "stable"
    return result


DRIFT_LABELS = {"stable": "stable", "degrading": "degrading", "insufficient data": "insufficient data"}


# ---------------------------------------------------------------------------
# Conclusions (shared by the terminal output and the HTML report)
# ---------------------------------------------------------------------------
def build_conclusion(summaries, targets):
    """Return [(kind, text)] with kind in ok | warn | fail | info | rec."""
    if not summaries:
        return [("fail", _("No results were collected."))]
    verdict, passing = overall_verdict(summaries, targets)
    failing = [s for s in summaries if sla_failures(s, targets)]
    by_load = lambda s: s.get("load") or 0  # noqa: E731
    out = []
    best = max(passing, key=by_load) if passing else None
    first_fail = min(failing, key=by_load) if failing else None

    if verdict == "passed":
        if len(summaries) > 1:
            out.append(("ok", _("All %d stages met the SLA. Highest load tested: %s.")
                        % (len(summaries), summary_load(best))))
            out.append(("info", _("The capacity limit was not reached; add higher load levels to find it.")))
        else:
            out.append(("ok", _("The test met the SLA at %s.") % summary_load(best)))
            out.append(("info", _("Run a stepped or fixed-rate load test to find the capacity limit.")))
    elif verdict == "partial":
        out.append(("warn", _("SLA held up to %s and broke at %s: %s.") % (
            summary_load(best), summary_load(first_fail),
            "; ".join(t for _c, t in sla_failures(first_fail, targets)))))
    else:
        out.append(("fail", _("SLA already failed at %s: %s.") % (
            summary_load(first_fail), "; ".join(t for _c, t in sla_failures(first_fail, targets)))))

    ref = best or first_fail
    where = summary_load(ref)
    err = ref.get("error_rate")
    if err is not None:
        if err == 0:
            out.append(("info", _("Reliability at %s: no failed requests (%d/%d succeeded).")
                        % (where, ref.get("n_ok", 0), ref.get("n_total", 0))))
        else:
            reasons = ", ".join("%s x%d" % kv for kv in sorted((ref.get("failure_reasons") or {}).items()))
            out.append(("warn" if err <= targets.target_error else "fail",
                        _("Reliability at %s: %.1f%% of requests failed (%s).") % (where, err * 100, reasons)))

    first_token = ref.get("%s_p95" % ttft_key(targets))
    if first_token is not None:
        if first_token < 1:
            feel = _("feels instant")
        elif first_token <= 3:
            feel = _("acceptable")
        elif first_token <= 6:
            feel = _("a noticeable wait")
        else:
            feel = _("a long wait; users may give up")
        if ttft_key(targets) == "ttfa":
            out.append(("info", _("First answer token p95 at %s: %.2fs (%s).") % (where, first_token, feel)))
        else:
            out.append(("info", _("First token p95 at %s: %.2fs (%s).") % (where, first_token, feel)))

    tps = ref.get("tok_per_s_avg")
    if tps:
        words = tps * WORDS_PER_TOKEN
        ratio = words / READING_WORDS_PER_S
        out.append(("info", _("Streaming speed at %s: ~%.0f tok/s (~%.0f words/s), %.1fx typical silent reading "
                              "speed (~%.0f words/s).") % (where, tps, words, ratio, READING_WORDS_PER_S)))
        if ratio < 1:
            out.append(("warn", _("Text streams slower than people read; users will be waiting on the stream.")))

    if ref.get("reasoning_share"):
        out.append(("info", _("The model streams reasoning before answering (%.0f%% of responses, avg %.0f reasoning "
                              "tokens). First answer token p95: %s.") % (
            ref["reasoning_share"] * 100, ref.get("avg_reasoning_tokens") or 0, fmt_s(ref.get("ttfa_p95")))))
        if ttft_key(targets) != "ttfa":
            out.append(("info", _("Use --ttft-basis answer to apply the SLA to the visible answer instead.")))

    if first_fail:
        codes = {c for c, _t in sla_failures(first_fail, targets)}
        if "ttft" in codes:
            out.append(("rec", _("Time to first token is the bottleneck: requests queue or prefill is slow. Add "
                                 "replicas or GPUs, cap concurrent sequences per instance, enable prefix caching / "
                                 "chunked prefill, or shorten prompts.")))
        if "tps" in codes:
            out.append(("rec", _("Per-user generation speed collapsed: decode is saturated. Lower the batch size per "
                                 "GPU, use a smaller or quantized model, enable speculative decoding, or scale out.")))
        if "errors" in codes:
            hints = []
            for st in (first_fail.get("failure_reasons") or {}):
                hint = next((h for prefix, h in ERROR_HINTS if st.startswith(prefix)), None)
                if hint and hint not in hints:
                    hints.append(hint)
            out.extend(("rec", _(h)) for h in hints)

    low = [s for s in summaries if s.get("low_sample")]
    if low:
        out.append(("warn", _("Fewer than %d successful requests at %s: p95/p99 are not statistically reliable. Run "
                              "longer stages or reduce think time.") % (
            MIN_SAMPLES, ", ".join(summary_load(s) for s in low))))
    queue = max([s.get("queue_wait_p95") or 0 for s in summaries])
    if queue > 0.5:
        out.append(("warn", _("The client concurrency cap delayed dispatch (queue wait p95 %.2fs); raise "
                              "--max-concurrency so latency reflects the server only.") % queue))
    if any(s.get("token_source") == "chunks" and s.get("n_ok") for s in summaries):
        out.append(("info", _("The server did not report token usage; token counts are estimated from stream "
                              "chunks.")))
    return out


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
KIND_STYLE = {
    "ok": lambda: "%s[OK]%s" % (C.GREEN, C.R),
    "warn": lambda: "%s[!]%s" % (C.YELLOW, C.R),
    "fail": lambda: "%s[X]%s" % (C.RED, C.R),
    "info": lambda: " - ",
    "rec": lambda: "%s->%s " % (C.CYAN, C.R),
}


def format_server_metrics(sm):
    if not sm or not sm.get("metrics"):
        return None
    m = sm["metrics"]
    parts = []
    if "running" in m:
        parts.append(_("running max %.0f") % m["running"]["max"])
    if "waiting" in m:
        parts.append(_("waiting max %.0f") % m["waiting"]["max"])
    if "kv_cache_pct" in m:
        parts.append(_("KV-cache max %.0f%%") % m["kv_cache_pct"]["max"])
    if "preemptions" in m:
        parts.append(_("preemptions +%.0f") % m["preemptions"]["delta"])
    return " | ".join(parts) or None


def print_results(cfg, summaries, title, interrupted=False):
    clear_status()
    print()
    rule("=")
    print(C.BOLD + ("LLM Benchmark - " + _(title)).center(78) + C.R)
    rule("=")
    basis = _(" (first answer token)") if ttft_key(cfg) == "ttfa" else ""
    kv_line(_("AI Server"), cfg.url)
    kv_line(_("AI Model"), cfg.model)
    kv_line(_("SLA Target"), _("TTFT p95 < %.1fs%s | speed >= %.0f tok/s/user | errors < %.1f%%")
            % (cfg.target_ttft, basis, cfg.target_tps, cfg.target_error * 100))
    verdict, _p = overall_verdict(summaries, cfg)
    label = {"passed": C.GREEN + _("PASSED") + C.R,
             "partial": C.YELLOW + _("CONDITIONAL PASS (capacity limit found)") + C.R,
             "failed": C.RED + _("FAILED") + C.R}[verdict]
    kv_line(_("Overall Status"), label)
    if interrupted:
        kv_line(_("Note"), C.YELLOW + _("run was interrupted; results below are partial") + C.R)
    rule("-")
    row = "  %-11s %5s  %-7s %-7s %-10s %-7s %-6s %-9s %s"
    print(C.DIM + row % (_("Load"), "n", "TTFT95", "E2E95", _("Speed"), "ITL95", _("Err"), "Goodput", "SLA") + C.R)
    for s in summaries:
        fails = sla_failures(s, cfg)
        status = "%s%s%s" % (C.GREEN, _("PASS"), C.R) if not fails else "%s%s%s" % (C.RED, _("FAIL"), C.R)
        n_txt = "%d%s" % (s.get("n_total", 0), "*" if s.get("low_sample") else "")
        print(row % (
            summary_load(s), n_txt, fmt_s(s.get("ttft_p95")), fmt_num(s.get("e2e_p95"), "%.1fs"),
            fmt_num(s.get("tok_per_s_avg"), "%.0f tok/s"), fmt_num(s.get("itl_ms_p95"), "%.0fms"),
            fmt_pct(s.get("error_rate")), fmt_num(s.get("goodput_req_per_s"), "%.2f/s"), status))
        if s.get("reasoning_share"):
            print(C.DIM + "  %-11s        " % "" + _("reasoning in %.0f%% of answers, avg %.0f tok, first-answer p95 %s")
                  % (s["reasoning_share"] * 100, s.get("avg_reasoning_tokens") or 0, fmt_s(s.get("ttfa_p95"))) + C.R)
        server = format_server_metrics(s.get("server_metrics"))
        if server:
            print(C.DIM + "  %-11s        server: %s" % ("", server) + C.R)
    if any(s.get("low_sample") for s in summaries):
        print(C.DIM + "  " + _("* fewer than %d successful requests: percentiles are indicative only") % MIN_SAMPLES
              + C.R)
    rule("-")
    print("  %s%s%s" % (C.BOLD, _("CONCLUSION & USER EXPERIENCE INSIGHTS:"), C.R))
    for kind, text in build_conclusion(summaries, cfg):
        print("  %s %s" % (KIND_STYLE[kind](), text))
    rule("=")


def print_timeline(timeline, drift):
    if len(timeline) < 2:
        return
    print("\n  %s%s%s" % (C.BOLD, _("Timeline (post-warmup):"), C.R))
    row = "  %-13s %5s  %-8s %-8s %-10s %s"
    print(C.DIM + row % (_("Window"), "n", "TTFT50", "TTFT95", _("Speed"), _("Err")) + C.R)
    for b in timeline:
        print(row % ("%.0f-%.0fs" % (b["t_start"], b["t_end"]), b["n"], fmt_s(b["ttft_p50"]), fmt_s(b["ttft_p95"]),
                     fmt_num(b["tok_per_s_avg"], "%.0f tok/s"), fmt_pct(b["error_rate"])))
    verdict = drift.get("verdict")
    if verdict == "insufficient data":
        print("  " + _("Stability: not enough requests in the first/last third to judge drift."))
        return
    color = C.GREEN if verdict == "stable" else C.RED
    print("  " + _("Stability: %s - TTFT p95 %s -> %s, speed %s -> %s tok/s (first vs last third)") % (
        color + _(DRIFT_LABELS[verdict]).upper() + C.R, fmt_s(drift["first_ttft_p95"]), fmt_s(drift["last_ttft_p95"]),
        fmt_num(drift.get("first_tok_per_s"), "%.0f"), fmt_num(drift.get("last_tok_per_s"), "%.0f")))
    if verdict == "degrading":
        print("  %s%s%s" % (C.YELLOW, _("Latency grew or speed dropped over time: suspect KV-cache pressure, memory "
                                        "leaks or a growing queue."), C.R))


# ---------------------------------------------------------------------------
# Saving results (CSV + JSON + HTML)
# ---------------------------------------------------------------------------
def workload_context(cfg, prompts):
    return {
        "max_tokens": cfg.max_tokens,
        "min_tokens": cfg.min_tokens,
        "ignore_eos": cfg.ignore_eos,
        "temperature": cfg.temperature,
        "think_time": [cfg.think_min, cfg.think_max],
        "stagger": cfg.stagger,
        "warmup": cfg.warmup,
        "cooldown": cfg.cooldown,
        "timeout": cfg.timeout,
        "seed": cfg.seed,
        "pad_words": str(cfg.pad_words),
        "system_words": cfg.system_words,
        "prefix_mode": cfg.prefix_mode,
        "turns": cfg.turns,
        "arrival": cfg.arrival,
        "max_concurrency": cfg.max_concurrency,
        "prompts": prompt_source_id(cfg),
        "prompt_count": len(prompts),
    }


def save_reports(cfg, mode, summaries, records, prompts, extra=None, interrupted=False):
    os.makedirs(cfg.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = os.path.join(cfg.out, "%s-%s%s" % (mode, stamp, "-partial" if interrupted else ""))

    with open(base + "-requests.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(round_floats({k: v for k, v in r.items() if not k.startswith("_")}))

    verdict, passing = overall_verdict(summaries, cfg)
    best = max(passing, key=lambda s: s.get("load") or 0) if passing else None
    doc = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "timestamp": stamp,
        "mode": mode,
        "lang": LANG,
        "interrupted": interrupted,
        "url": cfg.url,
        "model": cfg.model,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "workload": workload_context(cfg, prompts),
        "target": {"ttft_p95": cfg.target_ttft, "error_rate": cfg.target_error,
                   "tok_per_s_per_user": cfg.target_tps, "ttft_basis": cfg.ttft_basis},
        "overall": {"status": verdict, "max_passing_load": best.get("load") if best else None,
                    "load_unit": summaries[0].get("load_unit") if summaries else None},
        "results": summaries,
    }
    doc.update(extra or {})
    doc = round_floats(doc)
    with open(base + "-summary.json", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)

    print("\n" + _("Generated report files:"))
    print("  " + base + "-requests.csv")
    print("  " + base + "-summary.json")
    if cfg.html:
        with open(base + "-report.html", "w", encoding="utf-8") as fh:
            fh.write(build_html_report(doc))
        print("  " + base + "-report.html")
    return base


def finish_run(cfg, mode, title, summaries, records, prompts, extra=None, interrupted=False, after_results=None):
    print_results(cfg, summaries, title, interrupted)
    if after_results:
        after_results()
    if records or summaries:
        save_reports(cfg, mode, summaries, records, prompts, extra, interrupted)
    STOP.clear()
    if interrupted:
        return EXIT_INTERRUPTED
    verdict, _p = overall_verdict(summaries, cfg)
    return EXIT_OK if verdict == "passed" else EXIT_SLA_FAILED


# ---------------------------------------------------------------------------
# Loading existing reports (v2 and legacy v1 'ringkasan.json')
# ---------------------------------------------------------------------------
LEGACY_RESULT_KEYS = {
    "total_request": "n_total",
    "request_ok": "n_ok",
    "sebab_gagal": "failure_reasons",
    "req_per_detik": "req_per_s",
    "token_per_detik_server": "output_tok_per_s",
    "tok_per_detik_per_user": "tok_per_s_avg",
    "jendela_detik": "window_s",
}


def load_report(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema_version", 1) >= 2:
        return doc
    results = []
    for r in doc.get("results") or []:
        row = {LEGACY_RESULT_KEYS.get(k, k): v for k, v in r.items()}
        row.setdefault("load", row.get("users"))
        row.setdefault("load_unit", "users")
        if row.get("n_ok") is not None:
            row.setdefault("low_sample", row["n_ok"] < MIN_SAMPLES)
        results.append(row)
    target = doc.get("target") or {}
    doc.update({
        "schema_version": 1,
        "mode": doc.get("mode") or os.path.basename(path).split("-")[0],
        "results": results,
        "target": {"ttft_p95": target.get("ttft_p95", DEFAULTS["target_ttft"]),
                   "error_rate": target.get("error_rate", DEFAULTS["target_error"]),
                   "tok_per_s_per_user": target.get("tok_per_detik_per_user", DEFAULTS["target_tps"]),
                   "ttft_basis": "token"},
    })
    return doc


def targets_from_doc(doc):
    t = doc.get("target") or {}
    return types.SimpleNamespace(
        target_ttft=t.get("ttft_p95", DEFAULTS["target_ttft"]),
        target_error=t.get("error_rate", DEFAULTS["target_error"]),
        target_tps=t.get("tok_per_s_per_user", DEFAULTS["target_tps"]),
        ttft_basis=t.get("ttft_basis", "token"),
    )


COMPARE_METRICS = [
    ("ttft_p50", "TTFT p50", "lower", fmt_s),
    ("ttft_p95", "TTFT p95", "lower", fmt_s),
    ("ttfa_p95", "First-answer p95", "lower", fmt_s),
    ("e2e_p95", "E2E p95", "lower", fmt_s),
    ("itl_ms_p95", "ITL p95", "lower", lambda v: fmt_num(v, "%.0fms")),
    ("tok_per_s_avg", "Speed/user", "higher", lambda v: fmt_num(v, "%.1f tok/s")),
    ("output_tok_per_s", "Throughput", "higher", lambda v: fmt_num(v, "%.0f tok/s")),
    ("req_per_s", "Requests/s", "higher", lambda v: fmt_num(v, "%.2f")),
    ("goodput_req_per_s", "Goodput/s", "higher", lambda v: fmt_num(v, "%.2f")),
    ("error_rate", "Error rate", "lower", fmt_pct),
]


def compare_reports(path_a, path_b):
    try:
        a, b = load_report(path_a), load_report(path_b)
    except (OSError, ValueError) as e:
        print("%s%s%s" % (C.RED, _("Could not read report: %s") % e, C.R))
        return EXIT_SETUP
    print()
    rule("=")
    print(C.BOLD + ("LLM Benchmark - " + _("REPORT COMPARISON")).center(78) + C.R)
    rule("=")
    for tag, path, doc in (("A", path_a, a), ("B", path_b, b)):
        print("  %s: %s" % (tag, os.path.basename(path)))
        print("     %s | %s | %s" % (doc.get("model") or "-", doc.get("url") or "-", doc.get("timestamp") or "-"))
    rule("-")
    index_b = {(r.get("load_unit", "users"), r.get("load")): r for r in b.get("results") or []}
    common = [(r, index_b[(r.get("load_unit", "users"), r.get("load"))]) for r in a.get("results") or []
              if (r.get("load_unit", "users"), r.get("load")) in index_b]
    if not common:
        print("  " + _("No common load levels between the two reports; nothing to compare side by side."))
        rule("=")
        return EXIT_OK
    better_txt, worse_txt = _("better"), _("worse")
    for ra, rb in common:
        print("  %s%s%s" % (C.BOLD, summary_load(ra), C.R))
        for key, label, better, fmt in COMPARE_METRICS:
            va, vb = ra.get(key), rb.get(key)
            if va is None and vb is None:
                continue
            change = ""
            if va is not None and vb is not None:
                if va == vb:
                    change = C.DIM + _("same") + C.R
                elif va:
                    pct = (vb - va) / abs(va) * 100
                    improved = (pct < 0) if better == "lower" else (pct > 0)
                    if abs(pct) < 5:
                        change = C.DIM + "%+.1f%% (%s)" % (pct, _("~same")) + C.R
                    else:
                        change = "%s%+.1f%% %s%s" % (C.GREEN if improved else C.RED, pct,
                                                     better_txt if improved else worse_txt, C.R)
                else:
                    improved = (vb < va) if better == "lower" else (vb > va)
                    change = "%s%s%s" % (C.GREEN if improved else C.RED, better_txt if improved else worse_txt, C.R)
            print("    %-17s %12s  ->  %-12s %s" % (_(label), fmt(va), fmt(vb), change))
    rule("=")
    return EXIT_OK


def regenerate_report(path):
    try:
        doc = load_report(path)
    except (OSError, ValueError) as e:
        print("%s%s%s" % (C.RED, _("Could not read report: %s") % e, C.R))
        return EXIT_SETUP
    base = path
    for suffix in ("-summary.json", "-ringkasan.json", ".json"):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    out = base + "-report.html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build_html_report(doc))
    print(_("HTML report written: %s") % out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# HTML report (single self-contained file, inline SVG charts, light & dark)
# ---------------------------------------------------------------------------
REPORT_CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--text:#0b0b0b;--text-2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--good:#0ca30c;
--warn:#fab219;--crit:#d03b3b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;
--surface:#1a1a19;--text:#f0efec;--text-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
--border:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--text:#f0efec;--text-2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--text);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1120px;margin:0 auto;padding:32px 16px 48px}
h1{font-size:24px;font-weight:600;margin:0 0 4px}
h2{font-size:16px;font-weight:600;margin:32px 0 12px}
h3{font-size:14px;font-weight:600;margin:0}
p{margin:0}
.meta{color:var(--text-2);margin-bottom:16px;overflow-wrap:anywhere}
.badge{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border:1px solid var(--border);
border-radius:999px;background:var(--surface);font-weight:600;font-size:13px}
.ico{font-weight:700}.pass .ico{color:var(--good)}.partial .ico{color:var(--warn)}.fail .ico{color:var(--crit)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:20px}
.tile,.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;min-width:0}
.tile .label{color:var(--text-2);font-size:13px}.tile .value{font-size:24px;font-weight:600;margin-top:2px}
.tile .sub{color:var(--muted);font-size:12px}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:12px}
.card p.sub{color:var(--text-2);font-size:13px;margin:2px 0 8px}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--text-2);margin-bottom:4px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.key{display:inline-block;width:14px;height:2px;border-radius:1px}
svg.chart{width:100%;height:auto;display:block}
.chart .grid{stroke:var(--grid);stroke-width:1}.chart .axis{stroke:var(--axis);stroke-width:1}
.chart .tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.chart .sla{stroke:var(--text-2);stroke-width:1}.chart .sla-label{fill:var(--text-2);font-size:11px}
.chart .line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.chart .dot{stroke:var(--surface);stroke-width:2}
.chart .hit{fill:transparent;cursor:default}.chart .hit:focus{outline:none;stroke:var(--text-2);stroke-width:1}
.conclusion{list-style:none;padding:0;margin:0;display:grid;gap:6px}
.conclusion li{display:flex;gap:8px;align-items:baseline}
.conclusion .k{flex:0 0 auto;font-weight:700;width:18px;text-align:center}
.k.ok{color:var(--good)}.k.warn{color:var(--warn)}.k.fail{color:var(--crit)}.k.info,.k.rec{color:var(--muted)}
.tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 10px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--grid)}
th{color:var(--text-2);font-weight:600}th:first-child,td:first-child{text-align:left}
td{font-variant-numeric:tabular-nums}tr:last-child td{border-bottom:none}
.kv td{text-align:left;white-space:normal;overflow-wrap:anywhere}.kv td:first-child{color:var(--text-2);width:35%}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--text);border:1px solid var(--border);
border-radius:6px;padding:6px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.12);z-index:10;max-width:260px}
footer{margin-top:40px;color:var(--muted);font-size:12px}
"""

REPORT_JS = """
(function(){var tip=document.getElementById('tip');
function show(el,x,y){tip.textContent=el.getAttribute('data-tip');tip.hidden=false;
var w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.min(x+12,innerWidth-w-8)+'px';
tip.style.top=Math.min(y+12,innerHeight-h-8)+'px';}
document.querySelectorAll('[data-tip]').forEach(function(el){
el.addEventListener('mousemove',function(e){show(el,e.clientX,e.clientY);});
el.addEventListener('mouseleave',function(){tip.hidden=true;});
el.addEventListener('focus',function(){var r=el.getBoundingClientRect();show(el,r.right,r.top);});
el.addEventListener('blur',function(){tip.hidden=true;});});})();
"""


def _nice_scale(max_value, ticks=4):
    if not max_value or max_value <= 0:
        return 1.0, 1.0
    raw = max_value / ticks
    exp = 10 ** math.floor(math.log10(raw))
    step = next(m * exp for m in (1, 2, 2.5, 5, 10) if m * exp >= raw)
    return step, step * math.ceil(max_value / step - 1e-9)


def _tick_label(v, step, unit):
    decimals = 0 if step >= 1 else min(3, int(math.ceil(-math.log10(step))))
    if v >= 10000:
        text = "%gK" % round(v / 1000.0, 1)
    else:
        text = "%.*f" % (decimals, v)
    return text + unit


def svg_line_chart(xs, series, x_fmt, y_unit="", threshold=None, threshold_label="", aria=""):
    """Render a small line chart. series = [(name, values, css_color_var)]."""
    w, h, ml, mr, mt, mb = 640, 240, 52, 18, 14, 34
    pw, ph = w - ml - mr, h - mt - mb
    values = [v for _n, vals, _c in series for v in vals if v is not None]
    if threshold is not None:
        values.append(threshold)
    if not values or not xs:
        return ""
    step, top = _nice_scale(max(values) * 1.05)
    xmin, xmax = min(xs), max(xs)

    def px(x):
        return ml + (pw / 2.0 if xmax == xmin else (x - xmin) / float(xmax - xmin) * pw)

    def py(y):
        return mt + ph - (y / top) * ph

    e = html.escape
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="%s">' % (w, h, e(aria))]
    v = 0.0
    while v <= top + step * 1e-6:
        y = py(v)
        out.append('<line class="%s" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (
            "axis" if v == 0 else "grid", ml, w - mr, y, y))
        out.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">%s</text>' % (
            ml - 8, y + 4, e(_tick_label(v, step, y_unit))))
        v += step
    tick_xs = xs if len(xs) <= 10 else [xs[int(round(i * (len(xs) - 1) / 5.0))] for i in range(6)]
    for x in tick_xs:
        out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (px(x), h - 12, e(x_fmt(x))))
    if threshold is not None:
        y = py(threshold)
        out.append('<line class="sla" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (ml, w - mr, y, y))
        out.append('<text class="sla-label" x="%d" y="%.1f" text-anchor="end">%s</text>' % (
            w - mr, y - 5, e(threshold_label)))
    for name, vals, color in series:
        pts = [(px(x), py(v)) for x, v in zip(xs, vals) if v is not None]
        if len(pts) >= 2:
            d = "M" + " L".join("%.1f %.1f" % p for p in pts)
            out.append('<path class="line" d="%s" style="stroke:var(%s)"/>' % (d, color))
    for name, vals, color in series:
        for x, v in zip(xs, vals):
            if v is None:
                continue
            tip = "%s @ %s: %s" % (name, x_fmt(x), _tick_label(v, min(step, 0.01) if v < 10 else 1, y_unit))
            out.append('<circle class="dot" cx="%.1f" cy="%.1f" r="4" style="fill:var(%s)"/>' % (px(x), py(v), color))
            out.append('<circle class="hit" cx="%.1f" cy="%.1f" r="11" tabindex="0" data-tip="%s" aria-label="%s"/>'
                       % (px(x), py(v), e(tip), e(tip)))
    out.append("</svg>")
    return "".join(out)


def chart_card(title, subtitle, xs, series, x_fmt, y_unit="", threshold=None, threshold_label=""):
    svg = svg_line_chart(xs, series, x_fmt, y_unit, threshold, threshold_label, aria=title)
    if not svg:
        return ""
    e = html.escape
    legend = ""
    if len(series) >= 2:
        legend = '<div class="legend">%s</div>' % "".join(
            '<span><i class="key" style="background:var(%s)"></i>%s</span>' % (c, e(n)) for n, _v, c in series)
    return '<figure class="card" style="margin:0"><h3>%s</h3><p class="sub">%s</p>%s%s</figure>' % (
        e(title), e(subtitle), legend, svg)


def _time_fmt(span):
    if span > 900:
        return lambda v: "%.0fm" % (v / 60.0)
    return lambda v: "%.0fs" % v


def build_html_report(doc):
    e = html.escape
    results = doc.get("results") or []
    targets = targets_from_doc(doc)
    unit = results[0].get("load_unit", "users") if results else "users"
    verdict, passing = overall_verdict(results, targets)
    if doc.get("interrupted"):
        badge = '<span class="badge partial"><span class="ico">&#9888;</span>%s</span>' % e(_("Interrupted (partial)"))
    else:
        icon, cls, text = {"passed": ("&#10003;", "pass", _("SLA passed")),
                           "partial": ("&#9680;", "partial", _("Capacity limit found")),
                           "failed": ("&#10005;", "fail", _("SLA failed"))}[verdict]
        badge = '<span class="badge %s"><span class="ico">%s</span>%s</span>' % (cls, icon, e(text))
    host = urllib.parse.urlsplit(doc.get("url") or "").netloc or (doc.get("url") or "-")
    key = ttft_key(targets)
    ttft_label = _("First answer token") if key == "ttfa" else _("Time to first token")

    ref = max(passing, key=lambda s: s.get("load") or 0) if passing else (results[0] if results else {})
    tiles = [
        (_("Max load within SLA"), fmt_load(ref.get("load"), unit) if passing else _("None"),
         _("highest tested level that passed") if passing else _("first stage already failed")),
        ("%s p95" % ttft_label, fmt_s(ref.get("%s_p95" % key)), (_("at %s") % summary_load(ref)) if ref else ""),
        (_("Speed per user"), fmt_num(ref.get("tok_per_s_avg"), "%.0f tok/s"),
         _("target at least %.0f tok/s") % targets.target_tps),
        (_("Error rate"), fmt_pct(ref.get("error_rate")), _("target below %.1f%%") % (targets.target_error * 100)),
    ]
    parts = ['<!doctype html><html lang="%s"><head><meta charset="utf-8">' % LANG,
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>%s</title><style>%s</style></head><body><main>' % (e(_("LLM Benchmark Report")), REPORT_CSS),
             '<h1>%s</h1>' % e(_("LLM benchmark report")),
             '<p class="meta">%s &middot; %s &middot; %s &middot; %s</p>' % (
                 e(doc.get("model") or "-"), e(host), e(_("%s test") % (doc.get("mode") or "-")),
                 e(doc.get("timestamp") or "-")),
             badge, '<div class="tiles">']
    for label, value, sub in tiles:
        parts.append('<div class="tile"><div class="label">%s</div><div class="value">%s</div>'
                     '<div class="sub">%s</div></div>' % (e(label), e(value), e(sub)))
    parts.append("</div>")

    parts.append('<h2>%s</h2><div class="card"><ul class="conclusion">' % e(_("Conclusion")))
    symbols = {"ok": "&#10003;", "warn": "!", "fail": "&#10005;", "info": "&middot;", "rec": "&rarr;"}
    for kind, text in build_conclusion(results, targets):
        parts.append('<li><span class="k %s">%s</span><span>%s</span></li>' % (kind, symbols[kind], e(text)))
    parts.append("</ul></div>")

    charts = []
    sla_label = "SLA %.1fs" % targets.target_ttft
    tps_label = "SLA %.0f tok/s" % targets.target_tps
    if len(results) >= 2:
        xs = [r.get("load") for r in results]
        x_fmt = (lambda v: "%g" % v)
        x_name = _("concurrent users") if unit == "users" else _("requests per second")
        charts.append(chart_card(_("%s vs load") % ttft_label, _("Seconds, by %s") % x_name, xs, [
            ("p50", [r.get("%s_p50" % key) for r in results], "--s1"),
            ("p95", [r.get("%s_p95" % key) for r in results], "--s2")], x_fmt, "s", targets.target_ttft, sla_label))
        charts.append(chart_card(_("Generation speed per user"), _("Tokens per second, by %s") % x_name, xs, [
            (_("average"), [r.get("tok_per_s_avg") for r in results], "--s1"),
            (_("slowest 5%"), [r.get("tok_per_s_p5") for r in results], "--s2")],
            x_fmt, "", targets.target_tps, tps_label))
        charts.append(chart_card(_("Server output throughput"), _("Output tokens per second, all users combined"),
                                 xs, [(_("output tok/s"), [r.get("output_tok_per_s") for r in results], "--s1")],
                                 x_fmt))
        charts.append(chart_card(_("Throughput vs goodput"),
                                 _("Requests per second; goodput counts only requests that met the SLA"), xs, [
                                     (_("completed"), [r.get("req_per_s") for r in results], "--s1"),
                                     (_("within SLA"), [r.get("goodput_req_per_s") for r in results], "--s2")], x_fmt))

    timeline = [b for b in (doc.get("timeline") or []) if b.get("n")]
    if len(timeline) >= 2:
        xs = [(b["t_start"] + b["t_end"]) / 2.0 for b in timeline]
        tf = _time_fmt(xs[-1])
        charts.append(chart_card(_("%s over time") % ttft_label, _("Seconds, per time window after warmup"), xs, [
            ("p50", [b.get("ttft_p50") for b in timeline], "--s1"),
            ("p95", [b.get("ttft_p95") for b in timeline], "--s2")], tf, "s", targets.target_ttft, sla_label))
        charts.append(chart_card(_("Generation speed over time"), _("Average tokens per second per user"), xs, [
            (_("speed"), [b.get("tok_per_s_avg") for b in timeline], "--s1")], tf, "", targets.target_tps,
            tps_label))

    if len(results) == 1:
        sm = (results[0].get("server_metrics") or {}).get("timeline") or []
        if len(sm) >= 2:
            xs = [t for t, _s in sm]
            tf = _time_fmt(xs[-1])
            if any("running" in s or "waiting" in s for _t, s in sm):
                charts.append(chart_card(_("Server queue"), _("Requests running and waiting (from /metrics)"), xs, [
                    (_("running"), [s.get("running") for _t, s in sm], "--s1"),
                    (_("waiting"), [s.get("waiting") for _t, s in sm], "--s2")], tf))
            if any("kv_cache_pct" in s for _t, s in sm):
                charts.append(chart_card(_("KV-cache usage"), _("Percent of KV-cache in use (from /metrics)"), xs, [
                    ("KV-cache", [s.get("kv_cache_pct") for _t, s in sm], "--s1")], tf, "%"))

    series = doc.get("requests_series") or []
    if len(series) >= 2:
        xs = [r["i"] for r in series]
        charts.append(chart_card(_("Latency per query"), _("Seconds, sequential single-user queries"), xs, [
            (_("first token"), [r.get("ttft_s") for r in series], "--s1"),
            (_("full response"), [r.get("e2e_s") for r in series], "--s2")], lambda v: "#%d" % v, "s"))

    charts = [c for c in charts if c]
    if charts:
        parts.append('<h2>%s</h2><div class="charts">%s</div>' % (e(_("Charts")), "".join(charts)))

    cols = [(_("Load"), lambda r: summary_load(r)),
            (_("Requests"), lambda r: "%s/%s" % (r.get("n_ok", "-"), r.get("n_total", "-"))),
            ("TTFT p50", lambda r: fmt_s(r.get("ttft_p50"))),
            ("TTFT p95", lambda r: fmt_s(r.get("ttft_p95"))),
            (_("Answer p95"), lambda r: fmt_s(r.get("ttfa_p95"))),
            ("E2E p95", lambda r: fmt_s(r.get("e2e_p95"))),
            (_("Speed avg"), lambda r: fmt_num(r.get("tok_per_s_avg"), "%.1f")),
            (_("Speed p5"), lambda r: fmt_num(r.get("tok_per_s_p5"), "%.1f")),
            ("ITL p95", lambda r: fmt_num(r.get("itl_ms_p95"), "%.0f ms")),
            (_("Output tok/s"), lambda r: fmt_num(r.get("output_tok_per_s"), "%.0f")),
            ("Req/s", lambda r: fmt_num(r.get("req_per_s"), "%.2f")),
            ("Goodput/s", lambda r: fmt_num(r.get("goodput_req_per_s"), "%.2f")),
            (_("Errors"), lambda r: fmt_pct(r.get("error_rate"))),
            ("SLA", lambda r: ("&#10003; " + e(_("Pass"))) if not sla_failures(r, targets)
             else ("&#10005; " + e(_("Fail")))),
            (_("Server"), lambda r: format_server_metrics(r.get("server_metrics")) or "-")]
    parts.append('<h2>%s</h2><div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>' % (
        e(_("Results per stage")), "".join("<th>%s</th>" % e(n) for n, _f in cols)))
    for r in results:
        cells = []
        for name, fn in cols:
            text = fn(r)
            cells.append("<td>%s</td>" % (text if name == "SLA" else e(text)))
        parts.append("<tr>%s</tr>" % "".join(cells))
    parts.append("</tbody></table></div>")

    if timeline:
        parts.append('<h2>%s</h2><div class="tablewrap"><table><thead><tr><th>%s</th><th>%s</th><th>TTFT p50</th>'
                     '<th>TTFT p95</th><th>%s</th><th>%s</th></tr></thead><tbody>' % (
                         e(_("Timeline")), e(_("Window")), e(_("Requests")), e(_("Speed avg")), e(_("Errors"))))
        for b in timeline:
            parts.append("<tr><td>%.0f-%.0fs</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                b["t_start"], b["t_end"], b["n"], fmt_s(b.get("ttft_p50")), fmt_s(b.get("ttft_p95")),
                fmt_num(b.get("tok_per_s_avg"), "%.1f"), fmt_pct(b.get("error_rate"))))
        parts.append("</tbody></table></div>")
        drift = doc.get("drift") or {}
        if drift.get("verdict") in ("stable", "degrading"):
            parts.append('<p class="meta" style="margin-top:8px">%s</p>' % e(
                _("Stability verdict: %s. TTFT p95 %s -> %s, speed %s -> %s tok/s (first vs last third of the "
                  "window).") % (_(DRIFT_LABELS[drift["verdict"]]), fmt_s(drift.get("first_ttft_p95")),
                                 fmt_s(drift.get("last_ttft_p95")), fmt_num(drift.get("first_tok_per_s"), "%.0f"),
                                 fmt_num(drift.get("last_tok_per_s"), "%.0f"))))

    rows = [(_("Server URL"), doc.get("url") or "-"), (_("Model"), doc.get("model") or "-"),
            ("SLA", _("%s p95 < %.1fs, speed >= %.0f tok/s/user, errors < %.1f%%") % (
                ttft_label, targets.target_ttft, targets.target_tps, targets.target_error * 100))]
    for k, v in sorted((doc.get("workload") or {}).items()):
        rows.append((k.replace("_", " "), v if not isinstance(v, list) else " - ".join(str(x) for x in v)))
    env = doc.get("environment") or {}
    if env:
        rows.append((_("environment"), "Python %s / %s" % (env.get("python", "-"), env.get("platform", "-"))))
    parts.append('<h2>%s</h2><div class="tablewrap"><table class="kv"><tbody>%s</tbody></table></div>' % (
        e(_("Test configuration")),
        "".join("<tr><td>%s</td><td>%s</td></tr>" % (e(str(k)), e(str(v))) for k, v in rows)))
    parts.append('<footer>%s</footer>' % e(
        _("Generated by %s %s. Percentiles use the nearest-rank method; requests are attributed to the window in "
          "which they started.") % (doc.get("tool") or TOOL_NAME, doc.get("tool_version") or "")))
    parts.append('</main><div id="tip" role="tooltip" hidden></div><script>%s</script></body></html>' % REPORT_JS)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Setup & Initial Checks
# ---------------------------------------------------------------------------
def is_builtin_prompts(spec):
    return bool(spec) and spec.strip("\"' ").lower().startswith(BUILTIN_PREFIX)


def prompt_source_id(cfg):
    """Machine-readable prompt source stored in the JSON report (no directory names)."""
    if not cfg.prompts:
        return "default"
    spec = cfg.prompts.strip("\"' ")
    return spec if is_builtin_prompts(spec) else os.path.basename(spec)


def prompt_source_label(cfg):
    """Short description of the prompt source for reports and the test plan."""
    if not cfg.prompts:
        return _("curated defaults")
    return _("built-in set") if is_builtin_prompts(cfg.prompts) else _("custom file")


def load_prompts(cfg):
    if is_builtin_prompts(cfg.prompts):
        name = cfg.prompts.strip("\"' ")[len(BUILTIN_PREFIX):].strip().lower()
        if name not in BUILTIN_PROMPT_SETS:
            print("%s%s%s" % (C.RED, _("Unknown built-in prompt set: %s (available: %s)")
                              % (name, ", ".join(sorted(BUILTIN_PROMPT_SETS))), C.R))
            return None
        return list(BUILTIN_PROMPT_SETS[name])
    if cfg.prompts:
        path = cfg.prompts.strip("\"' ")
        try:
            with open(path, encoding="utf-8") as fh:
                prompts = [line.strip() for line in fh if line.strip()]
        except OSError as e:
            print("%s%s%s" % (C.RED, _("Failed to open prompts file: %s") % e, C.R))
            return None
        if not prompts:
            print("%s%s%s" % (C.RED, _("Prompts file is empty: %s") % path, C.R))
            return None
        return prompts
    return list(DEFAULT_PROMPTS)


def build_opener(cfg):
    if cfg.insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener()


def normalize_url(url):
    """Automatically append /chat/completions if user provided only the /v1 base URL."""
    if not url:
        return url
    clean = url.strip().rstrip("/")
    if clean.endswith("/v1"):
        return clean + "/chat/completions"
    return url.strip()


CONNECTION_HINTS = {
    "http_404": "Endpoint URL not found. Ensure the path ends with '/chat/completions'.",
    "http_401": "Authentication error: API key invalid or missing.",
    "http_403": "Forbidden: API key lacks access, or quota is exhausted.",
    "http_400": "Request rejected. Check the model name; vLLM-only options (--min-tokens, --ignore-eos) are refused "
                "by other servers.",
    "invalid_url": "Invalid URL format.",
    "no_answer": "The model only produced reasoning tokens before max_tokens ran out; raise max_tokens.",
    "timeout": "No response before --timeout; the server may be loading the model or overloaded.",
    "conn_error": "Could not connect. Is the server running and reachable from this machine?",
}


def check_connection(cfg, workload, opener, interactive):
    if not (cfg.url.startswith("http://") or cfg.url.startswith("https://")):
        print("%s[FAILED]%s %s" % (C.RED, C.R, _("Invalid URL format: it must start with http:// or https://")))
        print("  " + _("Example: %s") % "http://localhost:4000/v1/chat/completions")
        if interactive:
            print("  %s%s%s" % (C.YELLOW, _("Fix the URL via the Server Config menu (s)."), C.R))
        return False

    print(_("Checking connection to %s ...") % cfg.url)
    spin = [0]

    def progress(stage, tokens, t0, ttft):
        spin[0] += 1
        sp = SPINNER[spin[0] % 4]
        if stage in ("sending", "connected"):
            write_status("  %s " % sp + _("[Thinking] waiting for the first token... (%.1fs)") % (now() - t0))
        elif stage == "reasoning":
            write_status("  %s " % sp + _("[Reasoning] model is thinking: %d tokens (%.1fs)") % (tokens, now() - t0))
        else:
            write_status("  %s " % sp + _("[Streaming] receiving answer: %d tokens (%.1fs)") % (tokens, now() - t0))

    messages = workload.new_conversation(random.Random(cfg.seed)).messages(workload.prompts[0])
    r = send_request(cfg, messages, opener, on_progress=progress)
    clear_status()

    if r["status"] == "http_400" and cfg.usage:
        # Some gateways reject stream_options; retry once without it before failing
        cfg.usage = False
        retry = send_request(cfg, messages, opener)
        if retry["status"] == "ok":
            print("  %s(%s)%s" % (C.DIM, _("server rejected stream_options; token usage reporting disabled for this "
                                           "run"), C.R))
            r = retry
        else:
            cfg.usage = True

    if r["status"] != "ok":
        detail = (" - %s" % r["error_detail"]) if r.get("error_detail") else ""
        print("%s[FAILED]%s status=%s%s" % (C.RED + C.BOLD, C.R, r["status"], detail))
        hint = CONNECTION_HINTS.get(r["status"], "Please verify URL, API key and model name.")
        print("  %s%s%s\n" % (C.YELLOW, _(hint), C.R))
        return False

    msg = "%s[OK] %s%s " % (C.GREEN, _("Connected."), C.R) + _("First token %.2fs") % r["ttft_s"]
    if (r.get("reasoning_tokens") or 0) > 0:
        msg += ", " + _("first answer token %s (model streams reasoning: %d tokens)") % (
            fmt_s(r["ttfa_s"]), r["reasoning_tokens"])
    msg += ", " + _("%d tokens generated") % (r["output_tokens"] or 0)
    if r.get("token_source") == "chunks":
        msg += " %s(%s)%s" % (C.DIM, _("estimated from stream chunks"), C.R)
    print(msg + ".")

    metrics_url = resolve_metrics_url(cfg)
    if metrics_url:
        try:
            sample = fetch_metrics(metrics_url, opener)
            if sample:
                print("  " + _("Server metrics: %s (%s)") % (metrics_url, ", ".join(sorted(sample))))
            else:
                print("  %s%s%s" % (C.YELLOW, _("Server metrics: %s responded but no known vLLM/llama.cpp/SGLang/TGI "
                                                "gauges were found.") % metrics_url, C.R))
        except Exception as e:
            print("  %s%s%s" % (C.YELLOW, _("Server metrics unavailable at %s (%s); continuing without them.")
                                % (metrics_url, e), C.R))
            cfg.metrics_url = ""
    print()
    return True


# ---------------------------------------------------------------------------
# Benchmark Test Modes
# ---------------------------------------------------------------------------
def mode_baseline(cfg, workload, opener):
    """Single user sequential requests with real-time thinking status and token stream display."""
    records = []
    interrupted = False
    conv = workload.new_conversation(random.Random(cfg.seed))
    t_start = now()
    print("\n%s>>>%s %s" % (C.CYAN, C.R, _("Starting Quick Baseline Test (1 user - %d sequential queries)...")
                            % cfg.requests))
    try:
        for i in range(cfg.requests):
            prompt = workload.prompts[i % len(workload.prompts)]
            snippet = prompt.replace("\n", " ")
            snippet = (snippet[:45] + "...") if len(snippet) > 45 else snippet
            print("\n[%d/%d] %s: \"%s\"" % (i + 1, cfg.requests, _("Query"), snippet))
            spin = [0, 0.0]

            def progress(stage, tokens, t0, ttft):
                t = now()
                if t - spin[1] < 0.1 and stage in ("reasoning", "answering"):
                    return
                spin[0] += 1
                spin[1] = t
                sp = SPINNER[spin[0] % 4]
                if stage in ("sending", "connected"):
                    write_status("  %s " % sp + _("[Thinking] waiting for the first token... (%.1fs)") % (t - t0))
                else:
                    decode = (t - t0 - ttft) if ttft and t - t0 > ttft else 0
                    rate = tokens / decode if decode > 0 else 0
                    phase = _("Reasoning") if stage == "reasoning" else _("Streaming")
                    write_status("  %s [%s] %d tok (~%.0f tok/s) | %.1fs" % (sp, phase, tokens, rate, t - t0))

            messages = conv.messages(prompt)
            turn = conv.turn
            started = now()
            rec = send_request(cfg, messages, opener, on_progress=progress, keep_text=workload.turns > 1)
            rec.update(stage=1, load=1, user=0, turn=turn, started_s=started - t_start, finished_s=now() - t_start)
            conv.advance(rec)
            records.append(rec)
            clear_status()
            if rec["status"] == "ok":
                extra = ""
                if rec.get("reasoning_tokens"):
                    extra = " | " + _("answer after %s, %d reasoning tok") % (fmt_s(rec["ttfa_s"]),
                                                                            rec["reasoning_tokens"])
                print("  -> " + _("Completed in %.1fs (TTFT: %s | %d tokens | %s tok/s%s)") % (
                    rec["e2e_s"], fmt_s(rec["ttft_s"]), rec["output_tokens"] or 0,
                    fmt_num(rec["tok_per_s"], "%.0f"), extra) + " %s[OK]%s" % (C.GREEN, C.R))
            else:
                detail = (" - %s" % rec["error_detail"][:80]) if rec.get("error_detail") else ""
                print("  -> %s[FAILED]%s " % (C.RED, C.R) + _("status=%s after %.1fs") % (rec["status"], rec["e2e_s"])
                      + detail)
    except KeyboardInterrupt:
        clear_status()
        print("\n  %s%s%s" % (C.YELLOW, _("Interrupted - keeping %d completed queries.") % len(records), C.R))
        interrupted = True

    elapsed = now() - t_start
    summary = summarize(cfg, records, (0.0, elapsed + 1e-6), 1, "users")
    summary["elapsed_s"] = elapsed
    extra = {"requests_series": [{"i": i + 1, "ttft_s": r.get("ttft_s"), "e2e_s": r.get("e2e_s"),
                                  "tok_per_s": r.get("tok_per_s")} for i, r in enumerate(records)]}
    return finish_run(cfg, "baseline", "QUICK BASELINE TEST RESULTS (1 USER)", [summary], records,
                      workload.prompts, extra, interrupted)


def _run_stepped(cfg, workload, opener, mode, title, loads, runner, label_fmt):
    summaries, records = [], []
    interrupted = False
    for idx, load in enumerate(loads):
        label = _("Stage %d/%d (%s)") % (idx + 1, len(loads), label_fmt(load))
        s, recs = runner(cfg, workload, opener, load, cfg.duration, label, idx + 1)
        summaries.append(s)
        records.extend(recs)
        if s.get("interrupted"):
            interrupted = True
            break
        fails = sla_failures(s, cfg)
        status = "%s[%s]%s" % (C.GREEN, _("PASSED"), C.R) if not fails else "%s[%s]%s" % (C.RED, _("FAILED"), C.R)
        print("  %s>>%s " % (C.CYAN, C.R) + _("%s completed: %d requests | TTFT p95 %s | speed %s tok/s | errors %s")
              % (label, s["n_total"], fmt_s(s.get("ttft_p95")), fmt_num(s.get("tok_per_s_avg"), "%.0f"),
                 fmt_pct(s.get("error_rate"))) + " " + status)
        server = format_server_metrics(s.get("server_metrics"))
        if server:
            print("     %sserver: %s%s" % (C.DIM, server, C.R))
        if fails:
            print("\n%s%s%s" % (C.YELLOW, _("Stage exceeded SLA limits (%s). Stopping test early.")
                                % "; ".join(t for _c, t in fails), C.R))
            break
        if idx < len(loads) - 1 and cfg.level_pause:
            print("  %s%s%s" % (C.DIM, _("Cooling down for %ds before next stage...") % cfg.level_pause, C.R))
            if interruptible_sleep(cfg.level_pause):
                interrupted = True
                break
    return finish_run(cfg, mode, title, summaries, records, workload.prompts, None, interrupted)


def mode_ramp(cfg, workload, opener):
    """Ramp up concurrent users progressively to discover server capacity and breaking points."""
    return _run_stepped(cfg, workload, opener, "ramp", "STEPPED LOAD TEST RESULTS",
                        parse_number_list(cfg.levels, int), run_closed_loop, lambda n: fmt_load(n))


def mode_rate(cfg, workload, opener):
    """Open-loop fixed arrival rates: shows where latency explodes once the server falls behind."""
    return _run_stepped(cfg, workload, opener, "rate", "FIXED-RATE LOAD TEST RESULTS",
                        parse_number_list(cfg.rates, float), run_open_loop, lambda r: "%g req/s" % r)


SOAK_LABELS = {
    "soak": "Stability Soak Test",
    "rag": "Long Document Test (RAG)",
    "multiturn": "Multi-Turn Chat Test",
}


def mode_soak(cfg, workload, opener, mode="soak", title="STABILITY TEST RESULTS"):
    """Sustained concurrency over long duration to test stability and detect memory leaks."""
    label = _(SOAK_LABELS.get(mode, "Stability Soak Test"))
    s, records = run_closed_loop(cfg, workload, opener, cfg.users, cfg.duration, label)
    window = eval_window(cfg, cfg.duration, s["elapsed_s"])
    timeline = build_timeline(records, window)
    drift = analyze_drift(records, window)
    return finish_run(cfg, mode, title, [s], records, workload.prompts, {"timeline": timeline, "drift": drift},
                      s.get("interrupted"), after_results=lambda: print_timeline(timeline, drift))


MODES = {
    "baseline": mode_baseline,
    "ramp": mode_ramp,
    "rate": mode_rate,
    "soak": mode_soak,
}


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------
class Exit(Exception):
    pass


def ask(message, default=None, kind=str, allow_empty=False, choices=None):
    """Prompt user for a value with a clean, clear terminal style."""
    if default not in (None, ""):
        prompt = "  %s %s[%s]%s: " % (message, C.DIM, default, C.R)
    else:
        prompt = "  %s: " % message
    while True:
        try:
            answer = input(prompt).strip()
        except EOFError:
            raise Exit()
        if not answer:
            if default not in (None, ""):
                answer = str(default)
            elif allow_empty:
                return None
            else:
                print("    (%s)" % _("required"))
                continue
        try:
            value = kind(answer)
        except ValueError:
            print("    (%s)" % _("invalid value"))
            continue
        if choices and value not in choices:
            print("    (%s)" % (_("choose one of: %s") % ", ".join(str(c) for c in choices)))
            continue
        return value


def ask_yes(message, default=True):
    choice = "Y/n" if default else "y/N"
    prompt = "  %s %s[%s]%s: " % (message, C.DIM, choice, C.R)
    while True:
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            raise Exit()
        if not answer:
            return default
        if answer in ("y", "ya", "yes"):
            return True
        if answer in ("n", "no", "tidak", "t"):
            return False
        print("    %s(%s)%s" % (C.RED, _("please enter y or n"), C.R))


def range_text(text):
    parse_range(text)
    return text.replace(" ", "")


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    for old, new in LEGACY_CONFIG_KEYS.items():
        if old in data:
            data.setdefault(new, data.pop(old))
    if data.get("key") and "save_key" not in data:
        data["save_key"] = True  # v1 always stored the key; keep that behavior until the user changes it
    if "pad_words" in data:
        data["pad_words"] = str(data["pad_words"])
    return data


def save_config(cfg):
    data = {k: getattr(cfg, k) for k in DEFAULTS if hasattr(cfg, k)}
    if not cfg.save_key or getattr(cfg, "key_from_env", False):
        data["key"] = ""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        if sys.platform != "win32":
            try:
                os.chmod(CONFIG_FILE, 0o600)  # may contain an API key
            except OSError:
                pass
    except OSError as e:
        print("  (%s)" % (_("configuration could not be saved: %s") % e))


def configure_language(cfg):
    section("Language / Bahasa")
    for code, name in LANGUAGES.items():
        print("  %s%s%s  %s" % (C.CYAN, code, C.R, name))
    cfg.lang = set_language(ask("Language / Bahasa (en/id)", cfg.lang or "en", lambda t: t.strip().lower(),
                                choices=tuple(LANGUAGES)))
    save_config(cfg)
    print("  %s[OK] %s%s" % (C.GREEN, _("Language set to English."), C.R))


def configure_server(cfg):
    section(_("AI Server Configuration"))
    while True:
        url = ask(_("Server endpoint URL (e.g., http://localhost:4000/v1/chat/completions)"),
                  cfg.url or DEFAULTS["url"])
        if not (url.startswith("http://") or url.startswith("https://")):
            if url.startswith("localhost") or url.startswith("127.0.0.1") or ":" in url:
                url = "http://" + url
                print("  %s(%s)%s" % (C.DIM, _("URL automatically updated to: %s") % url, C.R))
            else:
                print("    %s(%s)%s" % (C.RED, _("URL must start with http:// or https://"), C.R))
                continue
        cfg.url = normalize_url(url)
        break
    cfg.model = ask(_("AI model name (e.g., qwen-30b, llama3, mistral-small-latest)"),
                    cfg.model or "mistral-small-latest")
    if getattr(cfg, "key_from_env", False):
        print("  %s%s%s" % (C.DIM, _("API key is taken from the LLM_API_KEY environment variable."), C.R))
    else:
        print("  " + (_("API Key (Enter = keep current key):") if cfg.key else _("API Key (Enter = none):")))
        try:
            key = getpass.getpass("  API Key: ").strip()
        except EOFError:
            raise Exit()
        if key:
            cfg.key = key
        if cfg.key:
            cfg.save_key = ask_yes(_("Store the API key in llmload.conf? It is saved as plain text (n = keep it for "
                                     "this session only)"), cfg.save_key)
    cfg.max_tokens = ask(_("Max generation length (tokens)"), cfg.max_tokens, int)
    if cfg.url.startswith("https://"):
        cfg.insecure = ask_yes(_("Skip HTTPS certificate verification?"), cfg.insecure)
    cfg.usage = ask_yes(_("Request server token usage reporting?"), cfg.usage)
    save_config(cfg)
    print("  %s[OK] %s%s" % (C.GREEN, _("Server configuration saved to %s") % CONFIG_FILE, C.R))


def configure_targets(cfg):
    section(_("Performance SLA Standards (Passing Criteria)"))
    print("  " + _("These thresholds determine whether a load stage is PASSED or FAILED."))
    cfg.target_ttft = ask(_("Max first token wait time / TTFT p95 (seconds)"), cfg.target_ttft, float)
    cfg.target_error = ask(_("Max acceptable error rate (%)"), cfg.target_error * 100, float) / 100.0
    cfg.target_tps = ask(_("Min generation speed per user (tokens/second)"), cfg.target_tps, float)
    print("  " + _("For reasoning models: 'token' = any first token (incl. thinking), 'answer' = first visible "
                   "answer token."))
    cfg.ttft_basis = ask(_("TTFT basis (token/answer)"), cfg.ttft_basis, str, choices=("token", "answer"))
    save_config(cfg)
    print("  %s[OK] %s%s" % (C.GREEN, _("SLA passing standards updated."), C.R))


def configure_prompts(cfg):
    section(_("Custom Prompts Setup"))
    print("  " + _("Provide a .txt file with one query per line, or press Enter for the default queries."))
    print("  " + _("Indonesian sample set: %s") % (BUILTIN_PREFIX + "id"))
    path = ask(_("Path to .txt prompt file (Enter = use default queries)"), None, str, allow_empty=True)
    cfg.prompts = path.strip("\"' ") if path else None
    save_config(cfg)
    print("  %s[OK] %s%s" % (C.GREEN, _("Prompt list updated."), C.R))


def configure_advanced(cfg):
    section(_("Advanced Workload Options"))
    print("  " + _("System prompt words > 0 adds a fixed system prompt; 'unique' gives each conversation its own"))
    print("  " + _("prefix so server prefix caching cannot help (compare both to measure the cache benefit)."))
    cfg.system_words = ask(_("System prompt length (words, 0 = none)"), cfg.system_words, int)
    if cfg.system_words:
        cfg.prefix_mode = ask(_("Prefix mode (shared/unique)"), cfg.prefix_mode, str, choices=("shared", "unique"))
    print("  " + _("Fixed output length (vLLM only): min_tokens / ignore_eos make runs comparable across models."))
    cfg.min_tokens = ask(_("Min output tokens (0 = off)"), cfg.min_tokens, int)
    cfg.ignore_eos = ask_yes(_("Ignore end-of-sequence (always generate max_tokens)?"), cfg.ignore_eos)
    print("  " + _("Prometheus metrics URL, e.g. http://host:8000/metrics, 'auto' (same host as the API), or empty."))
    metrics = ask(_("Server metrics URL"), cfg.metrics_url or "", str, allow_empty=True)
    cfg.metrics_url = (metrics or "").strip()
    cfg.html = ask_yes(_("Write an HTML report after each test?"), cfg.html)
    cfg.quiet = ask_yes(_("Hide the per-request log lines during load tests?"), cfg.quiet)
    save_config(cfg)
    print("  %s[OK] %s%s" % (C.GREEN, _("Advanced options saved."), C.R))


def configure_load(cfg):
    """Configure user think time between responses and warmup duration."""
    print("\n  " + _("Simulate User Reading Time (Think Time):"))
    print("  " + _("(Enter 0 and 0 for continuous aggressive stress testing)"))
    cfg.think_min = ask(_("Min reading delay / think time (seconds)"), cfg.think_min, float)
    cfg.think_max = max(cfg.think_min, ask(_("Max reading delay / think time (seconds)"),
                                           max(cfg.think_max, cfg.think_min), float))
    cfg.warmup = ask(_("Initial warmup duration to exclude from metrics (seconds)"),
                     min(cfg.warmup, cfg.duration * 0.3), float)
    clamp_warmup(cfg)


def clamp_warmup(cfg):
    if cfg.warmup >= cfg.duration * 0.7:
        cfg.warmup = max(5.0, round(cfg.duration * 0.2, 1))


def apply_preset(cfg, values):
    for k, v in values.items():
        setattr(cfg, k, v)


RAMP_PRESETS = {
    "1": dict(levels="1,5,10", duration=45, level_pause=5, think_min=5.0, think_max=15.0, warmup=10.0),
    "2": dict(levels="5,10,20,30", duration=120, level_pause=15, think_min=10.0, think_max=40.0, warmup=20.0),
    "3": dict(levels="5,15,30,50", duration=60, level_pause=10, think_min=0.0, think_max=0.0, warmup=10.0),
}

RATE_PRESETS = {
    "1": dict(rates="0.5,1,2", duration=60, level_pause=5, warmup=10.0),
    "2": dict(rates="0.5,1,2,4,8", duration=120, level_pause=15, warmup=20.0),
}

SOAK_PRESETS = {
    "1": dict(users=10, duration=300, think_min=10.0, think_max=30.0, warmup=30.0),
    "2": dict(users=20, duration=1800, think_min=10.0, think_max=40.0, warmup=60.0),
    "3": dict(users=30, duration=3600, think_min=10.0, think_max=60.0, warmup=120.0),
}


def print_options(options):
    for key, title, desc in options:
        print("  %s%s.%s %-22s: %s" % (C.CYAN, key, C.R, title, desc))


def configure_ramp(cfg):
    section(_("Stepped Load Test Presets"))
    print_options([
        ("1", _("Quick (~2-3 min)"), _("1, 5, 10 users (45s/stage, ideal for quick check)")),
        ("2", _("Standard (~8-10 min)"), _("5, 10, 20, 30 users (120s/stage, realistic human chat)")),
        ("3", _("Stress Test"), _("5, 15, 30, 50 users (60s/stage, 0s think time, GPU limit)")),
        ("4", _("Custom"), _("define users, duration and think time")),
    ])
    choice = ask(_("Select preset"), "1", choices=("1", "2", "3", "4"))
    if choice == "4":
        cfg.levels = ask(_("User stages (e.g., 1,5,10,20)"), cfg.levels, lambda t: (parse_number_list(t, int), t)[1])
        cfg.duration = ask(_("Duration per stage (seconds)"), cfg.duration, int)
        cfg.level_pause = ask(_("Cooldown between stages (seconds)"), cfg.level_pause, int)
        configure_load(cfg)
    else:
        apply_preset(cfg, RAMP_PRESETS[choice])
    clamp_warmup(cfg)
    save_config(cfg)


def configure_rate(cfg):
    section(_("Fixed-Rate Load Test (Open Loop)"))
    print("  " + _("New requests arrive at a fixed rate whether or not earlier ones finished, like real traffic"))
    print("  " + _("from many independent users. Latency here does not hide server slowdowns."))
    print_options([
        ("1", _("Quick"), _("0.5, 1, 2 req/s (60s/stage)")),
        ("2", _("Standard"), _("0.5, 1, 2, 4, 8 req/s (120s/stage)")),
        ("3", _("Custom"), _("define rates and duration")),
    ])
    choice = ask(_("Select preset"), "1", choices=("1", "2", "3"))
    if choice == "3":
        cfg.rates = ask(_("Request rates (req/s, e.g., 0.5,1,2,4)"), cfg.rates,
                        lambda t: (parse_number_list(t, float), t)[1])
        cfg.duration = ask(_("Duration per stage (seconds)"), cfg.duration, int)
        cfg.level_pause = ask(_("Cooldown between stages (seconds)"), cfg.level_pause, int)
        cfg.warmup = ask(_("Initial warmup duration to exclude from metrics (seconds)"),
                         min(cfg.warmup, cfg.duration * 0.3), float)
    else:
        apply_preset(cfg, RATE_PRESETS[choice])
    cfg.arrival = ask(_("Arrival pattern (poisson/constant)"), cfg.arrival, choices=("poisson", "constant"))
    clamp_warmup(cfg)
    save_config(cfg)


def configure_soak(cfg):
    section(_("Stability Test Presets (Long-Running Soak)"))
    print_options([
        ("1", _("Quick Soak"), _("10 users for 5 minutes (early memory leak check)")),
        ("2", _("Standard Soak"), _("20 users for 30 minutes (normal stability verification)")),
        ("3", _("Full Soak"), _("30 users for 1 hour (production endurance test)")),
        ("4", _("Custom"), _("specify users and duration manually")),
    ])
    choice = ask(_("Select preset"), "1", choices=("1", "2", "3", "4"))
    if choice == "4":
        cfg.users = ask(_("Number of concurrent users"), cfg.users, int)
        cfg.duration = ask(_("Test duration (seconds)"), 1800, int)
        configure_load(cfg)
    else:
        apply_preset(cfg, SOAK_PRESETS[choice])
    clamp_warmup(cfg)
    save_config(cfg)


def list_reports(cfg, suffixes=None):
    if not os.path.isdir(cfg.out):
        return []
    names = sorted(os.listdir(cfg.out), reverse=True)
    if suffixes:
        names = [n for n in names if n.endswith(suffixes)]
    return names


def show_output_files(cfg):
    section(_("Benchmark Report Files in '%s'") % cfg.out)
    names = list_reports(cfg)
    if not names:
        print("  " + _("No benchmark reports found yet. Please run a test first."))
        return
    for name in names[:20]:
        path = os.path.join(cfg.out, name)
        print("  %-52s %8.1f KB" % (name, os.path.getsize(path) / 1024.0))
    if len(names) > 20:
        print("  %s%s%s" % (C.DIM, _("... and %d more files") % (len(names) - 20), C.R))
    print("  %s%s%s" % (C.DIM, _("Open the *-report.html files in a browser for charts."), C.R))


def menu_compare(cfg):
    section(_("Compare Two Reports"))
    names = list_reports(cfg, ("-summary.json", "-ringkasan.json"))[:15]
    if len(names) < 2:
        print("  " + _("At least two summary reports are needed. Run a few tests first."))
        return
    for i, name in enumerate(names, 1):
        print("  %s%2d.%s %s" % (C.CYAN, i, C.R, name))
    valid = tuple(range(1, len(names) + 1))
    a = ask(_("Baseline report A (number)"), 2, int, choices=valid)
    b = ask(_("New report B (number)"), 1, int, choices=valid)
    compare_reports(os.path.join(cfg.out, names[a - 1]), os.path.join(cfg.out, names[b - 1]))


def show_menu(cfg):
    print("\n" + C.DIM + "=" * 74 + C.R)
    print(C.ORANGE + C.BOLD + "  (\\·▛▀▀▀▜·/)   " + C.R + C.BOLD + TOOL_NAME + C.R + C.DIM + "  v" + TOOL_VERSION + C.R)
    print(C.ORANGE + C.BOLD + "   ▜ • ‿ • ▛▘   " + C.R + _("LLM Latency, Speed & Concurrency Benchmark"))
    print(C.ORANGE + C.BOLD + "    ▘▘   ▝▝     " + C.R)
    print(C.DIM + "=" * 74 + C.R)
    kv_line(_("Server URL"), cfg.url or _("(not configured)"), 14)
    kv_line(_("AI Model"), cfg.model or _("(not configured)"), 14)
    if getattr(cfg, "key_from_env", False):
        key_label = "%s%s%s" % (C.GREEN, _("From LLM_API_KEY"), C.R)
    elif cfg.key:
        key_label = ("%s%s%s" % (C.GREEN, _("Saved in config"), C.R)) if cfg.save_key else _("Session only (not saved)")
    else:
        key_label = _("Not set (no key)")
    kv_line("API Key", key_label, 14)
    kv_line(_("Prompts"), cfg.prompts or _("Default (%d general queries)") % len(DEFAULT_PROMPTS), 14)
    kv_line(_("SLA Target"), _("TTFT < %.1fs%s | Errors < %.1f%% | Speed >= %.0f tok/s") % (
        cfg.target_ttft, _(" (answer)") if cfg.ttft_basis == "answer" else "", cfg.target_error * 100,
        cfg.target_tps), 14)
    if cfg.metrics_url:
        kv_line(_("Server Metrics"), cfg.metrics_url, 14)
    print(C.DIM + "-" * 74 + C.R)
    tests = [
        ("1", _("Quick 1-User Test"), _("Initial latency & peak single-user speed")),
        ("2", _("Stepped Load Test"), _("Ramp up concurrent users to find the capacity limit")),
        ("3", _("Fixed-Rate Load Test"), _("Open-loop req/s arrivals (realistic traffic)")),
        ("4", _("Stability Soak Test"), _("Sustained load over time (detect leaks/drift)")),
        ("5", _("Long Document Test (RAG)"), _("Queries wrapped with heavy document context")),
        ("6", _("Multi-Turn Chat Test"), _("Conversations whose history grows each turn")),
    ]
    tools = [
        ("c", _("Compare Reports"), _("Side-by-side diff of two test runs")),
        ("f", _("View Output Files"), _("Browse CSV, JSON and HTML reports")),
        ("s", _("Server Config"), _("Endpoint URL, model name, API key")),
        ("t", _("SLA Standards"), _("Latency, throughput and error tolerance")),
        ("p", _("Prompt List"), _("Use a custom query file (.txt)")),
        ("a", _("Advanced Options"), _("System prefix, fixed output, server metrics")),
        ("l", "Language / Bahasa", LANGUAGES.get(LANG, "English")),
        ("0", _("Exit"), _("Quit benchmark application")),
    ]
    for key, title, desc in tests:
        print("   %s%s%s  %-26s %s%s%s" % (C.CYAN, key, C.R, title, C.DIM, desc, C.R))
    print(C.DIM + "  " + "-" * 30 + C.R)
    for key, title, desc in tools:
        print("   %s%s%s  %-26s %s%s%s" % (C.CYAN, key, C.R, title, C.DIM, desc, C.R))
    print(C.DIM + "-" * 74 + C.R)


def print_plan(cfg, mode, workload):
    """Displays a clean benchmark test plan before execution."""
    print("\n" + C.DIM + "=" * 74 + C.R)
    print(C.BOLD + ("LLM Benchmark - " + _("BENCHMARK TEST PLAN")).center(74) + C.R)
    print(C.DIM + "=" * 74 + C.R)
    host = cfg.url.split("://")[-1].split("/")[0]
    if mode == "ramp":
        levels = parse_number_list(cfg.levels, int)
        minutes = math.ceil(len(levels) * (cfg.duration + (cfg.level_pause or 0)) / 60.0)
        scenario = _("Stepped load (%s users) | Est. duration: ~%d min") % (", ".join(map(str, levels)), minutes)
    elif mode == "rate":
        rates = parse_number_list(cfg.rates, float)
        minutes = math.ceil(len(rates) * (cfg.duration + (cfg.level_pause or 0)) / 60.0)
        scenario = _("Fixed rate (%s req/s, %s) | Est. duration: ~%d min") % (
            ", ".join("%g" % r for r in rates), cfg.arrival, minutes)
    elif mode == "baseline":
        scenario = _("Quick baseline (%d sequential queries)") % cfg.requests
    else:
        scenario = _("Sustained %d concurrent users | Est. duration: ~%d min") % (
            cfg.users, math.ceil(cfg.duration / 60.0))
    output = _("max %d tokens") % cfg.max_tokens
    if cfg.min_tokens or cfg.ignore_eos:
        output += " (%s)" % ("ignore_eos" if cfg.ignore_eos else "min_tokens %d" % cfg.min_tokens)
    rows = [
        (_("Model under Test"), "%s (%s)" % (cfg.model or _("(not configured)"), host)),
        (_("Load Scenario"), scenario),
        (_("Prompts"), _("%d query variations (%s) | %s") % (
            len(workload.prompts), prompt_source_label(cfg), workload.describe())),
        (_("Output Length"), output),
        (_("SLA Target"), _("TTFT p95 < %.1fs, speed >= %.0f tok/s, errors < %.1f%%")
         % (cfg.target_ttft, cfg.target_tps, cfg.target_error * 100)),
    ]
    for label, value in rows:
        print("  * %-17s: %s" % (label, value))
    print(C.DIM + "=" * 74 + C.R)


def prepare_run(cfg, mode, interactive=True):
    """Validate settings, show the plan, confirm, and verify connectivity."""
    cfg.url = normalize_url(cfg.url)
    if not cfg.url or not cfg.model:
        if not interactive:
            print("%s%s%s" % (C.RED, _("--url and --model are required."), C.R))
            return None, None
        print("\n  " + _("Server configuration incomplete."))
        configure_server(cfg)
    prompts = load_prompts(cfg)
    if prompts is None:
        return None, None
    try:
        workload = Workload(cfg, prompts)
        if mode == "ramp":
            parse_number_list(cfg.levels, int)
        if mode == "rate":
            parse_number_list(cfg.rates, float)
    except ValueError as e:
        print("%s%s%s" % (C.RED, _("Invalid setting: %s") % e, C.R))
        return None, None
    opener = build_opener(cfg)
    print_plan(cfg, mode, workload)
    if interactive and not ask_yes(_("Start benchmark test now?"), True):
        print("\n  >> " + _("Benchmark cancelled. Returning to main menu."))
        return None, None
    print()
    if not check_connection(cfg, workload, opener, interactive):
        return None, None
    return workload, opener


def run_menu_test(cfg, mode, **kwargs):
    workload, opener = prepare_run(cfg, mode)
    if workload:
        MODES[mode](cfg, workload, opener, **kwargs)


def run_menu(cfg):
    first_run = not os.path.exists(CONFIG_FILE)
    cli_lang = cfg.lang
    for k, v in load_config().items():
        if k in DEFAULTS:
            setattr(cfg, k, v)
    if cli_lang:
        cfg.lang = cli_lang
    cfg.lang = set_language(cfg.lang or os.environ.get("LLMLOAD_LANG") or "en")
    env_key = os.environ.get("LLM_API_KEY", "")
    if env_key and not cfg.key:
        cfg.key, cfg.key_from_env = env_key, True
    cfg.url = normalize_url(cfg.url)

    if first_run and not cli_lang:
        configure_language(cfg)
    if not cfg.model:
        print("\n" + _("Initial setup. Please enter server URL and model name."))
        configure_server(cfg)

    while True:
        show_menu(cfg)
        choice = ask(_("Select menu option"), "1").lower()

        if choice == "0":
            raise Exit()
        elif choice == "1":
            section(_("Quick 1-User Test (Peak Speed Limit)"))
            cfg.requests = ask(_("Number of sequential queries to test"), cfg.requests, int)
            run_menu_test(cfg, "baseline")
        elif choice == "2":
            configure_ramp(cfg)
            run_menu_test(cfg, "ramp")
        elif choice == "3":
            configure_rate(cfg)
            run_menu_test(cfg, "rate")
        elif choice == "4":
            configure_soak(cfg)
            run_menu_test(cfg, "soak")
        elif choice == "5":
            section(_("Long Document Scenario (RAG)"))
            print("  " + _("Queries are wrapped with a long document. Use a range like 500-4000 to mix short and "
                           "long."))
            saved = cfg.pad_words
            cfg.pad_words = ask(_("Document length in words (N or MIN-MAX)"), "2000", range_text)
            cfg.users = ask(_("Number of concurrent users"), 5, int)
            cfg.duration = ask(_("Test duration (seconds)"), 120, int)
            configure_load(cfg)
            run_menu_test(cfg, "soak", mode="rag", title="LONG DOCUMENT (RAG) TEST RESULTS")
            cfg.pad_words = saved
        elif choice == "6":
            section(_("Multi-Turn Chat Test"))
            print("  " + _("Each user keeps a conversation: every answer is added to the history of the next "
                           "question,"))
            print("  " + _("so prompts grow turn by turn (tests KV-cache and prefix caching realistically)."))
            saved = cfg.turns
            cfg.turns = ask(_("Turns per conversation"), max(cfg.turns, 4), int)
            cfg.users = ask(_("Number of concurrent users"), 10, int)
            cfg.duration = ask(_("Test duration (seconds)"), 300, int)
            configure_load(cfg)
            run_menu_test(cfg, "soak", mode="multiturn", title="MULTI-TURN CHAT TEST RESULTS")
            cfg.turns = saved
        elif choice == "c":
            menu_compare(cfg)
        elif choice == "f":
            show_output_files(cfg)
        elif choice == "s":
            configure_server(cfg)
        elif choice == "t":
            configure_targets(cfg)
        elif choice == "p":
            configure_prompts(cfg)
        elif choice == "a":
            configure_advanced(cfg)
        elif choice == "l":
            configure_language(cfg)
            continue
        else:
            print("  %s%s%s" % (C.RED, _("Invalid menu option."), C.R))
            continue

        STOP.clear()
        try:
            input("\n  %s%s%s" % (C.DIM, _("Press Enter to return to menu ..."), C.R))
        except EOFError:
            raise Exit()


# ---------------------------------------------------------------------------
# Command Line Interface
# ---------------------------------------------------------------------------
SUBCOMMANDS = ("menu", "baseline", "ramp", "rate", "soak", "compare", "report")


def parse_args(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in SUBCOMMANDS and argv[0] not in ("-h", "--help", "--version")):
        argv.insert(0, "menu")  # `llm-benchmark` and `llm-benchmark --lang id` open the interactive menu
    p = argparse.ArgumentParser(description="%s: LLM server load and performance testing tool" % TOOL_NAME)
    p.add_argument("--version", action="version", version="%s %s" % (TOOL_NAME, TOOL_VERSION))
    sub = p.add_subparsers(dest="mode", required=True)

    def add_lang(sp):
        sp.add_argument("--lang", choices=tuple(LANGUAGES), default=None,
                        help="Interface and report language: en (English) or id (Bahasa Indonesia)")

    def common(sp, required=True):
        add_lang(sp)
        sp.add_argument("--url", required=required, default=DEFAULTS["url"],
                        help="Endpoint URL, e.g. http://host:4000/v1/chat/completions")
        sp.add_argument("--model", required=required, default=DEFAULTS["model"],
                        help="AI model name matching server gateway")
        sp.add_argument("--key", default=os.environ.get("LLM_API_KEY", ""),
                        help="API key (prefer the LLM_API_KEY environment variable)")
        sp.add_argument("--max-tokens", type=int, default=DEFAULTS["max_tokens"], help="Max tokens per response")
        sp.add_argument("--min-tokens", type=int, default=0,
                        help="vLLM: minimum output tokens (fixes output length for fair comparisons)")
        sp.add_argument("--ignore-eos", action="store_true",
                        help="vLLM: ignore end-of-sequence and always generate max-tokens")
        sp.add_argument("--temperature", type=float, default=DEFAULTS["temperature"], help="Sampling temperature")
        sp.add_argument("--prompts", default=None, help="Path to text file with one query per line")
        sp.add_argument("--pad-words", default="0",
                        help="Wrap queries in a long document: N words or MIN-MAX range (RAG)")
        sp.add_argument("--system-words", type=int, default=0, help="Add a system prompt of N words")
        sp.add_argument("--prefix-mode", choices=("shared", "unique"), default="shared",
                        help="shared = same system prompt (prefix-cache friendly), unique = per conversation")
        sp.add_argument("--turns", type=int, default=1, help="Turns per conversation (history grows each turn)")
        sp.add_argument("--think-min", type=float, default=DEFAULTS["think_min"],
                        help="Min simulated user reading delay (seconds)")
        sp.add_argument("--think-max", type=float, default=DEFAULTS["think_max"],
                        help="Max simulated user reading delay (seconds)")
        sp.add_argument("--stagger", type=float, default=DEFAULTS["stagger"],
                        help="Stagger startup delay between concurrent users (seconds)")
        sp.add_argument("--warmup", type=float, default=DEFAULTS["warmup"],
                        help="Initial warmup duration to discard from metrics (seconds)")
        sp.add_argument("--cooldown", type=float, default=DEFAULTS["cooldown"],
                        help="Requests started in the last N seconds are excluded from metrics")
        sp.add_argument("--timeout", type=float, default=DEFAULTS["timeout"], help="Per-request HTTP timeout (seconds)")
        sp.add_argument("--seed", type=int, default=DEFAULTS["seed"], help="Random seed for reproducible workloads")
        sp.add_argument("--no-usage", dest="usage", action="store_false",
                        help="Disable stream_options token reporting if gateway rejects it (HTTP 400)")
        sp.add_argument("--insecure", action="store_true", help="Disable HTTPS certificate verification")
        sp.add_argument("--metrics-url", default="",
                        help="Prometheus /metrics URL to sample during the test, or 'auto'")
        sp.add_argument("--metrics-interval", type=float, default=DEFAULTS["metrics_interval"],
                        help="Seconds between /metrics samples")
        sp.add_argument("--out", default=DEFAULTS["out"], help="Output directory for reports")
        sp.add_argument("--no-html", dest="html", action="store_false", help="Do not write the HTML report")
        sp.add_argument("--quiet", action="store_true", help="Hide per-request log lines")
        sp.add_argument("--target-ttft", type=float, default=DEFAULTS["target_ttft"],
                        help="SLA threshold: Max acceptable TTFT p95 (seconds)")
        sp.add_argument("--target-error", type=float, default=DEFAULTS["target_error"],
                        help="SLA threshold: Max acceptable error rate fraction (0.01 = 1%%)")
        sp.add_argument("--target-tps", type=float, default=DEFAULTS["target_tps"],
                        help="SLA threshold: Min tokens per second per user")
        sp.add_argument("--ttft-basis", choices=("token", "answer"), default="token",
                        help="TTFT for the SLA: first token of any kind, or first visible answer token")

    m = sub.add_parser("menu", help="Interactive terminal menu (recommended)")
    common(m, required=False)

    b = sub.add_parser("baseline", help="Quick single-user baseline test")
    common(b)
    b.add_argument("--requests", type=int, default=DEFAULTS["requests"], help="Number of sequential queries to test")

    r = sub.add_parser("ramp", help="Stepped concurrency ramp-up test to find server capacity")
    common(r)
    r.add_argument("--levels", default=DEFAULTS["levels"], help="Comma-separated user levels (e.g. 5,10,20,30)")
    r.add_argument("--duration", type=int, default=DEFAULTS["duration"], help="Duration in seconds per stage")
    r.add_argument("--level-pause", "--jeda-level", dest="level_pause", type=int, default=DEFAULTS["level_pause"],
                   help="Cooldown pause between stages in seconds")

    q = sub.add_parser("rate", help="Open-loop fixed arrival rate test (requests per second)")
    common(q)
    q.add_argument("--rates", default=DEFAULTS["rates"], help="Comma-separated request rates (e.g. 0.5,1,2,4)")
    q.add_argument("--duration", type=int, default=120, help="Duration in seconds per stage")
    q.add_argument("--level-pause", dest="level_pause", type=int, default=DEFAULTS["level_pause"],
                   help="Cooldown pause between stages in seconds")
    q.add_argument("--arrival", choices=("poisson", "constant"), default="poisson", help="Arrival process")
    q.add_argument("--max-concurrency", type=int, default=DEFAULTS["max_concurrency"],
                   help="Client-side cap on simultaneous requests")

    s = sub.add_parser("soak", help="Sustained concurrency load test for stability & leak check")
    common(s)
    s.add_argument("--users", type=int, default=DEFAULTS["users"], help="Number of concurrent users")
    s.add_argument("--duration", type=int, default=3600, help="Total test duration in seconds")

    c = sub.add_parser("compare", help="Compare two *-summary.json reports side by side")
    add_lang(c)
    c.add_argument("report_a", help="Baseline report (A)")
    c.add_argument("report_b", help="New report (B)")

    h = sub.add_parser("report", help="Regenerate the HTML report from a *-summary.json file")
    add_lang(h)
    h.add_argument("summary", help="Path to a *-summary.json (or legacy *-ringkasan.json) file")

    cfg = p.parse_args(argv)
    for k, v in DEFAULTS.items():
        if not hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg


def main(argv=None):
    cfg = parse_args(argv)
    if cfg.mode == "menu":
        run_menu(cfg)
        return EXIT_OK
    cfg.lang = set_language(cfg.lang or os.environ.get("LLMLOAD_LANG") or "en")
    if cfg.mode == "compare":
        return compare_reports(cfg.report_a, cfg.report_b)
    if cfg.mode == "report":
        return regenerate_report(cfg.summary)

    workload, opener = prepare_run(cfg, cfg.mode, interactive=False)
    if not workload:
        return EXIT_SETUP
    return MODES[cfg.mode](cfg, workload, opener)


def cli():
    """Console-script entry point (`llm-benchmark`, `python -m llmload`, `python llmload.py`)."""
    try:
        sys.exit(main())
    except (KeyboardInterrupt, Exit):
        print("\n" + _("Done."))
        sys.exit(EXIT_OK)


if __name__ == "__main__":
    cli()
