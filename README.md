# Local LLM Benchmark 🚀

**English** · [Bahasa Indonesia](./README.id.md)

> **A lightweight, zero-dependency load testing and concurrency benchmarking tool for LLM inference engines and OpenAI-compatible APIs.**

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(Pure%20Stdlib)-orange.svg)](#key-features)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#quickstart)

```text
==========================================================================
  (\·▛▀▀▀▜·/)   LLM Benchmark  v2.0.0
   ▜ • ‿ • ▛▘   LLM Latency, Speed & Concurrency Benchmark
    ▘▘   ▝▝
==========================================================================
```

---

## Table of Contents
- [Why LLM Benchmark?](#why-llm-benchmark)
- [Key Features](#key-features)
- [Supported Providers & Inference Engines](#supported-providers--inference-engines)
- [Quickstart](#quickstart)
- [Benchmark Test Scenarios](#benchmark-test-scenarios)
- [Metrics & SLA Evaluation](#metrics--sla-evaluation)
- [Reasoning Models](#reasoning-models-deepseek-r1-qwen3-qwq-gpt-oss)
- [Server-Side Metrics](#server-side-metrics-vllm-llamacpp-sglang-tgi)
- [Reports: CSV, JSON, HTML, Compare](#reports-csv-json-html-compare)
- [Language (English / Bahasa Indonesia)](#language-english--bahasa-indonesia)
- [API Keys & Security](#api-keys--security)
- [Free Local Testing (Mock LLM Server)](#free-local-testing-mock-llm-server)
- [Running the Tests](#running-the-tests)
- [Project Structure](#project-structure)
- [Upgrading from v1](#upgrading-from-v1)
- [Contributing](#contributing)
- [License](#license)

---

## Why LLM Benchmark?

Benchmarking Large Language Models (LLMs) requires a fundamentally different approach than traditional web server stress testing. In standard web applications, requests are brief and non-streaming. With LLMs:
* **Time-to-First-Token (TTFT)** determines whether users perceive the system as responsive or laggy.
* **Token Generation Throughput (Tokens/s/User)** governs the readability and smoothness of the answer stream.
* **GPU Memory (KV-Cache) Saturation** can cause sudden degradation or out-of-memory (OOM) crashes as concurrent users increase.
* **Extended Multi-Hour Workloads** can reveal subtle memory leaks or queue congestion in inference servers.

**LLM Benchmark** simulates real human chat patterns (think time, staggered starts, growing conversations) as well as open-loop traffic at a fixed request rate, and turns the measurements into clear SLA verdicts for engineering and product teams.

---

## Key Features

* ⚡ **Zero External Dependencies:** 100% Python Standard Library. **No `pip install` required.**
* 🌐 **Universal OpenAI API Compatibility:** Works with any server or gateway exposing `/v1/chat/completions` with SSE streaming.
* 🧠 **Realistic Workloads:** closed-loop virtual users with think time, **open-loop fixed request rates** (Poisson or constant), **multi-turn conversations** with growing history, long RAG documents with **mixed lengths**, and shared vs unique **system prefixes** to measure prefix caching.
* 🧩 **Reasoning-Model Aware:** separates the first token of any kind (thinking) from the **first visible answer token**.
* 📏 **Complete Latency Profile:** TTFT, time to first answer, end-to-end latency, **TPOT**, **inter-token latency (ITL)**, input/output tokens, prefill speed, and **goodput**.
* 🚦 **Built-in SLA Thresholds** per load stage: TTFT p95 (default `< 3.0s`), speed per user (default `>= 15 tok/s`), and error rate (default `< 1.0%`).
* 📈 **Soak Timeline & Drift Detection:** per-window metrics and an automatic stable/degrading verdict.
* 🖥️ **Server Metrics Scraping:** samples Prometheus `/metrics` (running/waiting requests, KV-cache usage, preemptions) during each stage.
* 📊 **Reports:** per-request CSV, JSON summary with percentiles, a self-contained **HTML report with charts** (light & dark), and a **compare** command for before/after runs.
* 🛑 **Safe Interruption:** Ctrl+C stops gracefully and still saves partial results.
* 🤖 **CI/CD Ready:** headless subcommands and meaningful **exit codes**.
* 🌏 **Bilingual Interface:** English and Bahasa Indonesia, in the terminal and in the HTML report.

---

## Supported Providers & Inference Engines

| Platform / Provider | Sample Endpoint URL | Description |
| :--- | :--- | :--- |
| **vLLM** | `http://localhost:8000/v1/chat/completions` | High-throughput local GPU inference engine |
| **Ollama** | `http://localhost:11434/v1/chat/completions` | Local open-source models (Llama 3, Mistral, Qwen, etc.) |
| **llama.cpp server** | `http://localhost:8080/v1/chat/completions` | Lightweight CPU/GPU inference (`llama-server`) |
| **SGLang** | `http://localhost:30000/v1/chat/completions` | High-throughput serving with RadixAttention |
| **LiteLLM Gateway** | `http://localhost:4000/v1/chat/completions` | Multi-provider proxy, router, and load balancer |
| **Mistral AI** | `https://api.mistral.ai/v1/chat/completions` | Official Mistral Cloud API |
| **OpenAI** | `https://api.openai.com/v1/chat/completions` | GPT-4o, GPT-4o-mini, and compatible models |
| **DeepSeek** | `https://api.deepseek.com/v1/chat/completions` | DeepSeek-V3 and DeepSeek-R1 APIs |
| **Groq** | `https://api.groq.com/openai/v1/chat/completions` | Ultra-fast LPU inference engine |
| **LM Studio** | `http://localhost:1234/v1/chat/completions` | Local model desktop application |
| **LocalAI / TGI** | `http://localhost:8080/v1/chat/completions` | Hugging Face Text Generation Inference / LocalAI |

> [!TIP]
> A base URL ending in `/v1` is completed to `/v1/chat/completions` automatically.

---

## Quickstart

**Requirements:** Python 3.9 or newer on Windows 10/11, Linux, or macOS.

### Install as a command (recommended)

```bash
pip install .            # from the project folder (or: pipx install .  /  pip install git+<your-repo-url>)
llm-benchmark            # opens the interactive menu
llm-benchmark ramp --url http://localhost:8000/v1 --model qwen-30b --levels 5,10,20
llm-benchmark-mock       # local mock server for trying things out
```

`pip install -e .` gives a development install. `pip uninstall llm-benchmark` removes it. The package has no dependencies and is not published to PyPI; install it from a local copy or a Git URL. The launchers below keep working without installing anything.

When installed, settings are stored per user instead of beside the program:

| OS | Settings file |
| :--- | :--- |
| Windows | `%APPDATA%\llm-benchmark\llmload.conf` |
| Linux | `~/.config/llm-benchmark/llmload.conf` (honors `XDG_CONFIG_HOME`) |
| macOS | `~/Library/Application Support/llm-benchmark/llmload.conf` |

Set `LLMLOAD_CONFIG=/path/to/file.conf` to use another location. A source checkout (or an existing `llmload.conf` beside `llmload.py`) keeps using that file, so existing setups are unchanged. Reports are written to `./hasil` in the folder you run the command from (change with `--out`).

### Windows
* Double-click [`run.bat`](./run.bat), or run `run.bat` / `.\run.ps1` / `python llmload.py menu`.

> [!TIP]
> On Windows, ensure Python was installed with **"Add python.exe to PATH"** checked.

### Linux & macOS
```bash
chmod +x run.sh
./run.sh            # or: python3 llmload.py menu
```

### Headless CLI (Automation & CI/CD)

```bash
# Single-user baseline
python llmload.py baseline --url http://localhost:8000/v1 --model qwen-30b --requests 10

# Stepped concurrent users (closed loop) - capacity discovery
python llmload.py ramp --url http://localhost:8000/v1 --model qwen-30b --levels 5,10,20,30 --duration 120

# Fixed request rates (open loop) - realistic traffic that does not back off
python llmload.py rate --url http://localhost:8000/v1 --model qwen-30b --rates 0.5,1,2,4 --duration 120

# Long-running stability soak with server metrics
python llmload.py soak --url http://localhost:8000/v1 --model qwen-30b --users 20 --duration 1800 --metrics-url auto

# RAG: documents of 500-4000 words, 4-turn conversations, Indonesian output
python llmload.py soak --url ... --model ... --users 10 --duration 600 --pad-words 500-4000 --turns 4 --lang id
```

Pass the API key through the `LLM_API_KEY` environment variable (preferred over `--key`, which ends up in shell history).

**Exit codes:**

| Code | Meaning |
| :--- | :--- |
| `0` | All stages met the SLA |
| `1` | Setup or connection error (bad URL, auth failure, missing file) |
| `2` | The test ran but at least one stage failed the SLA |
| `130` | Interrupted with Ctrl+C (partial results were saved) |

Run `python llmload.py <subcommand> --help` for every option.

---

## Benchmark Test Scenarios

| Menu | Subcommand | Scenario | What it answers |
| :---: | :--- | :--- | :--- |
| 1 | `baseline` | **Quick 1-User Test** | Best-case latency and speed with no queueing |
| 2 | `ramp` | **Stepped Load Test** (closed loop) | How many concurrent chat users fit within the SLA? Stops at the first failing stage. |
| 3 | `rate` | **Fixed-Rate Load Test** (open loop) | Which arrival rate (req/s) can the server sustain? New requests arrive even when the server slows down, so overload is not hidden. |
| 4 | `soak` | **Stability Soak Test** | Does latency drift over 30-60 minutes (memory leaks, KV-cache pressure, queue buildup)? |
| 5 | `soak --pad-words` | **Long Document Test (RAG)** | How do long prompts affect prefill and TTFT? Use a range like `500-4000` to mix lengths. |
| 6 | `soak --turns` | **Multi-Turn Chat Test** | Each answer is appended to the next question, so prompts grow like a real chat. |

**Workload options** (CLI flags, or menu `a` = Advanced Options):

| Option | Purpose |
| :--- | :--- |
| `--system-words N` + `--prefix-mode shared\|unique` | Adds a system prompt. Compare `shared` (cache-friendly) with `unique` (cache-defeating) to measure the benefit of prefix caching. |
| `--min-tokens N`, `--ignore-eos` | vLLM only: fixes the output length so runs across models or configs are comparable. |
| `--think-min/--think-max` | Simulated reading time between a user's questions (`0 0` = aggressive stress). |
| `--warmup`, `--cooldown` | Seconds excluded at the start and end of each stage. |
| `--arrival poisson\|constant`, `--max-concurrency` | Arrival process and client-side cap for the `rate` test. |

Failed requests are retried after at least 1 second, so a server answering HTTP 429 instantly is not hammered by a hot loop.

---

## Metrics & SLA Evaluation

| Metric | Plain English | Notes |
| :--- | :--- | :--- |
| **TTFT (p50/p95/p99)** | Wait until the first token | The main responsiveness metric. Target `< 2-3 s`. |
| **First answer token (TTFA)** | Wait until the visible answer starts | Differs from TTFT only for reasoning models. |
| **E2E (p50/p95/p99)** | Total response time | From sending the request to the end of the stream. |
| **Speed per user (tok/s)** | How fast the answer streams | `1 / TPOT`. People read about 4 words/s (≈ 5-6 tok/s); `>= 15 tok/s` feels fluid. |
| **TPOT / ITL** | Time per output token / gap between streamed chunks | ITL p95/p99 exposes stutter when the GPU is saturated. |
| **Throughput** | Output tokens/s and requests/s for the whole server | |
| **Goodput** | Requests/s that met the SLA individually | Throughput that users actually experience as good. |
| **Error rate** | Share of failed requests | HTTP 429/5xx, timeouts, connection errors, empty or reasoning-only answers. |
| **Prefill speed** | Input tokens/s before the first token | Needs `usage.prompt_tokens` from the server. |

**How a stage is evaluated**

* Only requests that **started** inside the measurement window count (after warmup, before cooldown). Slow requests that finish after the stage ends are **kept**, so tail latency is not flattered.
* Percentiles use the nearest-rank method. A stage with **fewer than 20 successful requests** is flagged, because its p95/p99 is effectively the maximum.
* The conclusion is generated from the measured data: the highest passing load, the first failing load with its reasons, the real error rate and failure causes, and targeted recommendations for TTFT, speed, or error bottlenecks.

### Sample Evaluation Summary (illustrative numbers)

```text
==============================================================================
                    LLM Benchmark - STEPPED LOAD TEST RESULTS
==============================================================================
  AI Server      : http://localhost:8000/v1/chat/completions
  AI Model       : qwen-30b
  SLA Target     : TTFT p95 < 3.0s | speed >= 15 tok/s/user | errors < 1.0%
  Overall Status : CONDITIONAL PASS (capacity limit found)
------------------------------------------------------------------------------
  Load            n  TTFT95  E2E95   Speed      ITL95   Err    Goodput   SLA
  5 users        48  0.42s   6.1s    68 tok/s   19ms    0.0%   0.40/s    PASS
  10 users       97  0.61s   7.4s    55 tok/s   24ms    0.0%   0.81/s    PASS
                     server: running max 10 | waiting max 0 | KV-cache max 41%
  20 users      188  3.84s   14.9s   29 tok/s   61ms    1.6%   1.12/s    FAIL
                     server: running max 16 | waiting max 5 | KV-cache max 98%
------------------------------------------------------------------------------
  CONCLUSION & USER EXPERIENCE INSIGHTS:
  [!] SLA held up to 10 users and broke at 20 users: TTFT p95 3.84s > 3.0s; errors 1.6% > 1.0%.
   -  Reliability at 10 users: no failed requests (97/97 succeeded).
   -  First token p95 at 10 users: 0.61s (feels instant).
   -  Streaming speed at 10 users: ~55 tok/s (~41 words/s), 10.3x typical silent reading speed (~4 words/s).
  ->  Time to first token is the bottleneck: requests queue or prefill is slow. ...
  ->  Timeouts: the server is overloaded or --timeout is too low for long generations.
==============================================================================
```

---

## Reasoning Models (DeepSeek-R1, Qwen3, QwQ, gpt-oss)

Reasoning models stream their "thinking" in `delta.reasoning_content` (or `delta.reasoning`) before the answer. The tool measures both:

* **TTFT**: first token of any kind. Use this when your UI shows the thinking.
* **TTFA**: first token of the visible answer. Use `--ttft-basis answer` (or menu `t`) to apply the SLA to it.

Responses that contain only reasoning (the model used up `max_tokens` while thinking) are reported as `no_answer` failures.

---

## Server-Side Metrics (vLLM, llama.cpp, SGLang, TGI)

With `--metrics-url http://host:8000/metrics` (or `--metrics-url auto`, which uses the API's host), the tool samples the server's Prometheus endpoint during each stage and reports:

* requests **running** and **waiting** (queue),
* **KV-cache usage** in percent,
* **preemptions** (vLLM).

This lets you see *why* latency rose, e.g. the queue grew once KV-cache reached 100%. For llama.cpp, start `llama-server` with `--metrics`.

---

## Reports: CSV, JSON, HTML, Compare

Every run writes three files to `./hasil/` (change with `--out`):

| File | Contents |
| :--- | :--- |
| `*-requests.csv` | One row per request: `stage, load, user, turn, started_s, finished_s, status, error_detail, ttft_s, ttfa_s, e2e_s, queue_wait_s, input_tokens, output_tokens, reasoning_tokens, token_source, tok_per_s, tpot_ms, itl_p50_ms, itl_p95_ms, itl_max_ms, prompt_chars` |
| `*-summary.json` | Test parameters, SLA targets, per-stage percentiles, overall verdict, soak timeline, drift analysis, and server metrics. Ready for Grafana, Datadog, or ELK. |
| `*-report.html` | A single self-contained page with summary tiles, the conclusion, charts (TTFT vs load, speed, throughput vs goodput, soak timeline, server queue, KV-cache), and full tables. Works offline, in light and dark mode. |

Interrupted runs are saved with a `-partial` suffix.

```bash
# Before/after comparison per load level (e.g. after a vLLM upgrade or a quantization change)
python llmload.py compare hasil/ramp-20261101-100000-summary.json hasil/ramp-20261104-100000-summary.json

# Rebuild the HTML report (also works for v1 *-ringkasan.json files)
python llmload.py report hasil/soak-20261104-100000-summary.json --lang id
```

Both are also available in the menu (`c` = Compare Reports, `f` = View Output Files).

---

## Language (English / Bahasa Indonesia)

The terminal interface, conclusions, and HTML report are available in English and Bahasa Indonesia.

* Interactive: press `l` in the menu. You are also asked on first launch.
* CLI: `--lang en` or `--lang id` on any subcommand.
* Environment: `LLMLOAD_LANG=id`.

The language only changes the interface; the prompts sent to the model stay the same. To benchmark Indonesian conversations (tokenization differs from English), use the built-in Indonesian set (`--prompts builtin:id`; [`prompts-id.txt`](./prompts-id.txt) holds the same questions as an editable template):

```bash
llm-benchmark ramp --url ... --model ... --prompts builtin:id --lang id
```

---

## API Keys & Security

* **Preferred:** set `LLM_API_KEY` in the environment. The key is then never written to disk.
* In the menu you choose whether the key is stored in `llmload.conf`. It is saved as **plain text** (file permission `600` on Linux/macOS).
* `llmload.conf` and `hasil/` are listed in [`.gitignore`](./.gitignore); share [`llmload.conf.example`](./llmload.conf.example) instead.
* Reports never contain the API key.

> [!WARNING]
> If a config file containing a key was ever committed or shared, rotate that key at the provider.

---

## Free Local Testing (Mock LLM Server)

Test every feature, script, or CI pipeline without API credits or GPUs:

```bash
python mock_llm.py 8899                  # Windows: mock_llm.bat   Linux/macOS: ./mock_llm.sh
python mock_llm.py 8899 --reasoning 50   # simulate a reasoning model (50 thinking tokens first)
```

The mock serves `http://127.0.0.1:8899/v1/chat/completions` (SSE streaming, prefill delay, slowdown under concurrency, HTTP 429 above 25 active requests, token usage) and `http://127.0.0.1:8899/metrics` (vLLM-style gauges). Options: `--throttle-after`, `--max-active`.

---

## Running the Tests

```bash
python -m unittest discover -s tests -v
```

The suite covers metric math, the measurement window, SSE parsing (including reasoning streams), workloads, report loading (v1 and v2), HTML generation, translation coverage, and end-to-end runs against the mock server.

---

## Project Structure

```text
├── llmload.py            # Main application (load generators, metrics engine, reports, interactive CLI)
├── llmload_lang.py       # Interface translations (Bahasa Indonesia)
├── mock_llm.py           # Local SSE streaming mock server with /metrics
├── run.bat / run.ps1     # Launchers for Windows (Command Prompt / PowerShell)
├── run.sh                # Launcher for Linux & macOS
├── mock_llm.bat / .sh    # Mock server launchers
├── pyproject.toml        # Packaging: pip install . creates the `llm-benchmark` command
├── MANIFEST.in           # Extra files included in the source distribution
├── prompts-id.txt        # Indonesian prompt set (same as `--prompts builtin:id`, editable template)
├── llmload.conf.example  # Example settings (copy to llmload.conf, or let the menu create it)
├── tests/                # unittest suite
├── hasil/                # Output directory (CSV, JSON, HTML reports)
├── LICENSE               # MIT License
├── README.md             # Documentation (English)
└── README.id.md          # Documentation (Bahasa Indonesia)
```

---

## Upgrading from v1

* Existing `llmload.conf` files are migrated automatically (`jeda_level` → `level_pause`; a key that was already stored stays stored until you change it).
* Output files are now named `*-requests.csv` and `*-summary.json` with English column names. Old `*-ringkasan.json` files can still be used with `compare` and `report`.
* Menu letters changed: settings moved to letters (`s` server, `t` SLA, `p` prompts, `a` advanced, `l` language); tests are `1`-`6`.
* Metrics are stricter: requests are attributed to the window in which they started, and the conclusion reflects the real error rate. Expect slightly higher (more honest) p95 values than v1.

---

## Contributing

Contributions are warmly welcome! Whether you are reporting a bug, proposing a new scenario, or optimizing performance:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome-feature`).
3. Run the tests (`python -m unittest discover -s tests`). New UI strings need an entry in `llmload_lang.py`; the test suite checks this.
4. Commit your changes and open a **Pull Request**.

---

## License

This project is licensed under the permissive **MIT License**. See the [LICENSE](./LICENSE) file for details.

---

*Crafted with care by **biiproject** for the open AI engineering community.*
