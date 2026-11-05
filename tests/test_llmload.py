"""Unit and integration tests for llmload.py (stdlib unittest, no dependencies).

Run from the project root:
    python -m unittest discover -s tests -v
"""
import ast
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import llmload  # noqa: E402
import llmload_lang  # noqa: E402
import mock_llm  # noqa: E402


def make_cfg(**overrides):
    cfg = llmload.parse_args(["baseline", "--url", "http://127.0.0.1:1/v1/chat/completions", "--model", "m"])
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def rec(status="ok", started=1.0, ttft=0.5, tps=40.0, e2e=2.0, **extra):
    r = {"status": status, "started_s": started, "finished_s": started + e2e, "ttft_s": ttft, "ttfa_s": ttft,
         "e2e_s": e2e, "tok_per_s": tps, "output_tokens": 80, "reasoning_tokens": 0, "token_source": "usage",
         "_gaps": [0.02, 0.03]}
    r.update(extra)
    return r


class FakeResponse:
    def __init__(self, lines):
        self.lines = [ln.encode() if isinstance(ln, str) else ln for ln in lines]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self.lines)


class FakeOpener:
    def __init__(self, lines):
        self.lines = lines
        self.last_body = None

    def open(self, req, timeout=None):
        self.last_body = json.loads(req.data.decode())
        return FakeResponse(self.lines)


def sse(obj):
    return "data: " + json.dumps(obj) + "\n"


class TestStats(unittest.TestCase):
    def test_percentile_nearest_rank(self):
        vals = list(range(1, 101))
        self.assertEqual(llmload.percentile(vals, 50), 50)
        self.assertEqual(llmload.percentile(vals, 95), 95)
        self.assertEqual(llmload.percentile(vals, 99), 99)
        self.assertEqual(llmload.percentile([3, None, 1], 50), 1)
        self.assertIsNone(llmload.percentile([], 50))

    def test_parse_range(self):
        self.assertEqual(llmload.parse_range("2000"), (2000, 2000))
        self.assertEqual(llmload.parse_range("500-4000"), (500, 4000))
        self.assertEqual(llmload.parse_range(0), (0, 0))
        with self.assertRaises(ValueError):
            llmload.parse_range("40-10")

    def test_parse_number_list(self):
        self.assertEqual(llmload.parse_number_list("1, 5,10", int), [1, 5, 10])
        with self.assertRaises(ValueError):
            llmload.parse_number_list("0,5", int)


class TestSummarize(unittest.TestCase):
    def test_window_keeps_slow_requests_that_started_inside(self):
        cfg = make_cfg(warmup=10, cooldown=0)
        records = [rec(started=5), rec(started=20, e2e=80, ttft=9.0), rec(started=30), rec(status="aborted", started=40)]
        s = llmload.summarize(cfg, records, (10, 60), 5, "users")
        self.assertEqual(s["n_total"], 2)  # warmup and aborted requests are excluded
        self.assertEqual(s["ttft_p95"], 9.0)  # the slow request finishing after the window still counts

    def test_error_rate_goodput_and_low_sample(self):
        cfg = make_cfg(target_ttft=1.0, target_tps=15)
        records = [rec(), rec(ttft=2.0), rec(tps=5.0), rec(status="http_429", ttft=None, tps=None)]
        s = llmload.summarize(cfg, records, (0, 10), 4, "users")
        self.assertAlmostEqual(s["error_rate"], 0.25)
        self.assertEqual(s["failure_reasons"], {"http_429": 1})
        self.assertAlmostEqual(s["goodput_req_per_s"], 0.1)
        self.assertTrue(s["low_sample"])

    def test_sla_failures_and_verdict(self):
        cfg = make_cfg(target_ttft=1.0, target_error=0.01, target_tps=15)
        good = {"n_ok": 30, "ttft_p95": 0.5, "error_rate": 0.0, "tok_per_s_avg": 40, "load": 5}
        bad = {"n_ok": 30, "ttft_p95": 4.0, "error_rate": 0.2, "tok_per_s_avg": 5, "load": 10}
        self.assertEqual(llmload.sla_failures(good, cfg), [])
        self.assertEqual({c for c, _ in llmload.sla_failures(bad, cfg)}, {"ttft", "errors", "tps"})
        self.assertEqual(llmload.overall_verdict([good, bad], cfg)[0], "partial")
        self.assertEqual(llmload.overall_verdict([bad], cfg)[0], "failed")

    def test_conclusion_never_claims_zero_errors_when_errors_exist(self):
        cfg = make_cfg(target_error=0.05)
        s = {"n_ok": 30, "n_total": 31, "ttft_p95": 0.5, "error_rate": 1 / 31.0, "tok_per_s_avg": 40, "load": 5,
             "load_unit": "users", "failure_reasons": {"timeout": 1}}
        texts = " ".join(t for _, t in llmload.build_conclusion([s], cfg))
        self.assertIn("3.2%", texts)
        self.assertIn("timeout x1", texts)
        self.assertNotIn("no failed requests", texts)

    def test_timeline_and_drift(self):
        records = [rec(started=float(t), ttft=0.5 + (t > 60) * 2.0) for t in range(0, 90)]
        timeline = llmload.build_timeline(records, (0, 90), bucket=30)
        self.assertEqual([b["n"] for b in timeline], [30, 30, 30])
        self.assertEqual(llmload.analyze_drift(records, (0, 90))["verdict"], "degrading")
        stable = [rec(started=float(t)) for t in range(0, 90)]
        self.assertEqual(llmload.analyze_drift(stable, (0, 90))["verdict"], "stable")


class TestSendRequest(unittest.TestCase):
    def test_reasoning_model_separates_first_token_and_first_answer(self):
        lines = [sse({"choices": [{"delta": {"reasoning_content": "hmm"}}]})] * 3
        lines += [sse({"choices": [{"delta": {"content": "Hi"}}]})] * 4
        lines += [sse({"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 7,
                                                "completion_tokens_details": {"reasoning_tokens": 3}}}),
                  "data: [DONE]\n"]
        r = llmload.send_request(make_cfg(), [{"role": "user", "content": "q"}], FakeOpener(lines))
        self.assertEqual(r["status"], "ok")
        self.assertLessEqual(r["ttft_s"], r["ttfa_s"])
        self.assertEqual(r["reasoning_tokens"], 3)
        self.assertEqual(r["output_tokens"], 7)
        self.assertEqual(r["input_tokens"], 12)
        self.assertEqual(r["token_source"], "usage")
        self.assertEqual(len(r["_gaps"]), 6)

    def test_reasoning_only_is_no_answer(self):
        lines = [sse({"choices": [{"delta": {"reasoning": "x"}}]}), "data: [DONE]\n"]
        r = llmload.send_request(make_cfg(), [{"role": "user", "content": "q"}], FakeOpener(lines))
        self.assertEqual(r["status"], "no_answer")

    def test_stream_error_and_empty(self):
        r = llmload.send_request(make_cfg(), [], FakeOpener([sse({"error": {"message": "boom"}})]))
        self.assertEqual((r["status"], r["error_detail"]), ("stream_error", "boom"))
        r = llmload.send_request(make_cfg(), [], FakeOpener(["data: [DONE]\n"]))
        self.assertEqual(r["status"], "empty_response")

    def test_payload_options(self):
        opener = FakeOpener(["data: [DONE]\n"])
        llmload.send_request(make_cfg(min_tokens=50, ignore_eos=True, usage=False), [], opener)
        self.assertEqual(opener.last_body["min_tokens"], 50)
        self.assertTrue(opener.last_body["ignore_eos"])
        self.assertNotIn("stream_options", opener.last_body)


class TestWorkload(unittest.TestCase):
    def test_multi_turn_history_grows_then_resets(self):
        import random
        w = llmload.Workload(make_cfg(turns=3, pad_words="0"), ["q"])
        conv = w.new_conversation(random.Random(1))
        sizes = []
        for _ in range(4):
            msgs = conv.messages("q")
            sizes.append(len(msgs))
            conv.advance({"status": "ok", "_text": "answer"})
        self.assertEqual(sizes, [1, 3, 5, 1])

    def test_unique_prefix_differs_shared_does_not(self):
        import random
        for mode, expect_same in (("shared", True), ("unique", False)):
            w = llmload.Workload(make_cfg(system_words=20, prefix_mode=mode), ["q"])
            a = w.new_conversation(random.Random(1)).messages("q")[0]["content"]
            b = w.new_conversation(random.Random(2)).messages("q")[0]["content"]
            self.assertEqual(a == b, expect_same)

    def test_document_padding_range(self):
        import random
        w = llmload.Workload(make_cfg(pad_words="100-200"), ["q"])
        lengths = {len(w.wrap_document("q", random.Random(i)).split()) for i in range(20)}
        self.assertGreater(len(lengths), 1)
        self.assertTrue(all(100 < n < 215 for n in lengths))


class TestMetricsParsing(unittest.TestCase):
    def test_prometheus_parse_and_pick(self):
        text = ('# HELP x\nvllm:num_requests_running{model_name="a b"} 3\nvllm:num_requests_running{m="c"} 2\n'
                'vllm:kv_cache_usage_perc 0.42\nllamacpp:requests_deferred 1\n')
        sample = llmload.pick_server_metrics(llmload.parse_prometheus(text))
        self.assertEqual(sample["running"], 5)
        self.assertAlmostEqual(sample["kv_cache_pct"], 42.0)
        self.assertEqual(sample["waiting"], 1)

    def test_resolve_auto(self):
        cfg = make_cfg(url="https://h:8000/v1/chat/completions", metrics_url="auto")
        self.assertEqual(llmload.resolve_metrics_url(cfg), "https://h:8000/metrics")


class TestReports(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_legacy_report_is_readable(self):
        path = os.path.join(self.tmp, "ramp-20260101-000000-ringkasan.json")
        legacy = {"url": "u", "model": "m", "target": {"ttft_p95": 3.0, "error_rate": 0.01,
                                                       "tok_per_detik_per_user": 15.0},
                  "results": [{"users": 5, "total_request": 8, "request_ok": 8, "error_rate": 0.0,
                               "sebab_gagal": {}, "ttft_p95": 2.4, "tok_per_detik_per_user": 90.7}]}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(legacy, fh)
        doc = llmload.load_report(path)
        self.assertEqual(doc["mode"], "ramp")
        self.assertEqual(doc["results"][0]["load"], 5)
        self.assertEqual(doc["results"][0]["tok_per_s_avg"], 90.7)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(llmload.regenerate_report(path), 0)
            self.assertEqual(llmload.compare_reports(path, path), 0)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "ramp-20260101-000000-report.html")))

    def test_html_report_contains_charts_and_escapes(self):
        results = [{"load": n, "load_unit": "users", "n_ok": 30, "n_total": 30, "ttft_p50": 0.3, "ttft_p95": 0.5 * n,
                    "tok_per_s_avg": 40, "tok_per_s_p5": 30, "error_rate": 0.0, "req_per_s": n,
                    "goodput_req_per_s": n, "output_tok_per_s": 100 * n} for n in (1, 5, 10)]
        doc = {"model": "<script>x</script>", "url": "http://h/v1", "mode": "ramp", "results": results,
               "target": {"ttft_p95": 3.0, "error_rate": 0.01, "tok_per_s_per_user": 15}}
        page = llmload.build_html_report(doc)
        self.assertIn("<svg", page)
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("prefers-color-scheme:dark", page)


class TestConfig(unittest.TestCase):
    def test_legacy_config_migration_and_key_handling(self):
        tmp = tempfile.mkdtemp()
        old = llmload.CONFIG_FILE
        try:
            llmload.CONFIG_FILE = os.path.join(tmp, "llmload.conf")
            with open(llmload.CONFIG_FILE, "w", encoding="utf-8") as fh:
                json.dump({"jeda_level": 7, "key": "secret", "pad_words": 0}, fh)
            data = llmload.load_config()
            self.assertEqual(data["level_pause"], 7)
            self.assertTrue(data["save_key"])
            self.assertEqual(data["pad_words"], "0")

            cfg = make_cfg(key="secret", save_key=False)
            llmload.save_config(cfg)
            with open(llmload.CONFIG_FILE, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["key"], "")
        finally:
            llmload.CONFIG_FILE = old
            shutil.rmtree(tmp, ignore_errors=True)


class TestCliAndPrompts(unittest.TestCase):
    def test_no_arguments_opens_the_menu(self):
        self.assertEqual(llmload.parse_args([]).mode, "menu")
        cfg = llmload.parse_args(["--lang", "id"])
        self.assertEqual((cfg.mode, cfg.lang), ("menu", "id"))
        self.assertEqual(llmload.parse_args(["ramp", "--url", "http://h/v1", "--model", "m"]).mode, "ramp")
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            llmload.parse_args(["--version"])

    def test_builtin_prompt_sets(self):
        self.assertEqual(llmload.load_prompts(make_cfg(prompts="builtin:id")), llmload.INDONESIAN_PROMPTS)
        self.assertEqual(llmload.load_prompts(make_cfg(prompts="builtin:EN")), llmload.DEFAULT_PROMPTS)
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertIsNone(llmload.load_prompts(make_cfg(prompts="builtin:xx")))
        self.assertIn("xx", buf.getvalue())
        self.assertEqual(llmload.prompt_source_id(make_cfg(prompts="builtin:id")), "builtin:id")
        self.assertEqual(llmload.prompt_source_id(make_cfg(prompts=os.path.join("a", "b.txt"))), "b.txt")
        self.assertEqual(llmload.prompt_source_id(make_cfg(prompts=None)), "default")

    def test_indonesian_sample_file_matches_builtin_set(self):
        with open(os.path.join(ROOT, "prompts-id.txt"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
        self.assertEqual(lines, llmload.INDONESIAN_PROMPTS)


class TestConfigLocation(unittest.TestCase):
    ENV_KEYS = ("LLMLOAD_CONFIG", "APPDATA", "XDG_CONFIG_HOME", "HOME", "USERPROFILE")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved_env = {k: os.environ.get(k) for k in self.ENV_KEYS}
        self.saved_file = llmload.__file__
        os.environ.pop("LLMLOAD_CONFIG", None)
        for k in ("APPDATA", "XDG_CONFIG_HOME", "HOME", "USERPROFILE"):
            os.environ[k] = os.path.join(self.tmp, "home")

    def tearDown(self):
        llmload.__file__ = self.saved_file
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def module_dir(self, *files):
        path = tempfile.mkdtemp(dir=self.tmp)
        for name in files:
            open(os.path.join(path, name), "w").close()
        llmload.__file__ = os.path.join(path, "llmload.py")
        return path

    def test_environment_override_wins(self):
        os.environ["LLMLOAD_CONFIG"] = os.path.join(self.tmp, "custom.conf")
        self.module_dir("pyproject.toml")
        self.assertEqual(llmload.default_config_path(), os.path.join(self.tmp, "custom.conf"))

    def test_source_checkout_and_existing_file_stay_beside_the_script(self):
        path = self.module_dir("pyproject.toml")
        self.assertEqual(llmload.default_config_path(), os.path.join(path, "llmload.conf"))
        path = self.module_dir("llmload.conf")
        self.assertEqual(llmload.default_config_path(), os.path.join(path, "llmload.conf"))

    def test_installed_package_uses_the_user_config_directory(self):
        self.module_dir()  # looks like site-packages: no pyproject.toml, no llmload.conf
        result = llmload.default_config_path()
        self.assertTrue(result.startswith(os.path.join(self.tmp, "home")), result)
        self.assertTrue(result.endswith(os.path.join("llm-benchmark", "llmload.conf")), result)

    def test_save_config_creates_missing_directory(self):
        old = llmload.CONFIG_FILE
        try:
            llmload.CONFIG_FILE = os.path.join(self.tmp, "new", "dir", "llmload.conf")
            llmload.save_config(make_cfg(key="k", save_key=False))
            with open(llmload.CONFIG_FILE, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["key"], "")
        finally:
            llmload.CONFIG_FILE = old


class TestPackaging(unittest.TestCase):
    def read(self, name):
        with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
            return fh.read()

    def test_console_scripts_point_to_callables(self):
        text = self.read("pyproject.toml")
        self.assertIn('llm-benchmark = "llmload:cli"', text)
        self.assertIn('llm-benchmark-mock = "mock_llm:cli"', text)
        self.assertTrue(callable(llmload.cli) and callable(mock_llm.cli))

    def test_version_is_a_static_literal_setuptools_can_read(self):
        with open(os.path.join(ROOT, "llmload.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        values = [n.value.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                  and any(getattr(t, "id", "") == "TOOL_VERSION" for t in n.targets)]
        self.assertEqual(values, [llmload.TOOL_VERSION])
        self.assertRegex(values[0], r"^\d+\.\d+\.\d+$")

    def test_all_modules_are_listed_for_the_wheel(self):
        text = self.read("pyproject.toml")
        for module in ("llmload", "llmload_lang", "mock_llm"):
            self.assertIn('"%s"' % module, text)


class TestTranslations(unittest.TestCase):
    PLACEHOLDER = re.compile(r"%[-+ #0]*\*?\d*(?:\.\d+)?[sdifgxr%]")

    @classmethod
    def source_keys(cls):
        with open(os.path.join(ROOT, "llmload.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        keys = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_"
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                keys.add(node.args[0].value)
        keys.update(h for _, h in llmload.ERROR_HINTS)
        keys.update(llmload.CONNECTION_HINTS.values())
        keys.update(llmload.SOAK_LABELS.values())
        keys.update(label for _, label, _, _ in llmload.COMPARE_METRICS)
        keys.update(llmload.DRIFT_LABELS.values())
        return keys

    def test_every_ui_string_has_indonesian_translation(self):
        missing = sorted(self.source_keys() - set(llmload_lang.ID))
        self.assertEqual(missing, [], "untranslated strings: %s" % missing)

    def test_no_stale_translations(self):
        titles = {"QUICK BASELINE TEST RESULTS (1 USER)", "STEPPED LOAD TEST RESULTS", "FIXED-RATE LOAD TEST RESULTS",
                  "STABILITY TEST RESULTS", "LONG DOCUMENT (RAG) TEST RESULTS", "MULTI-TURN CHAT TEST RESULTS",
                  "Please verify URL, API key and model name."}
        stale = sorted(set(llmload_lang.ID) - self.source_keys() - titles)
        self.assertEqual(stale, [], "translations without a source string: %s" % stale)

    def test_placeholders_match(self):
        for src, dst in llmload_lang.ID.items():
            self.assertEqual(self.PLACEHOLDER.findall(src), self.PLACEHOLDER.findall(dst), src)

    def test_switching_language(self):
        try:
            llmload.set_language("id")
            self.assertEqual(llmload.fmt_load(5), "5 pengguna")
            self.assertIn("lang=\"id\"", llmload.build_html_report({"results": []}))
            llmload.set_language("xx")
            self.assertEqual(llmload.LANG, "en")
        finally:
            llmload.set_language("en")


class TestAgainstMockServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = mock_llm.make_server(0, reasoning=5, throttle_after=50, max_active=50)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def cfg(self, **kw):
        base = dict(url="http://127.0.0.1:%d/v1/chat/completions" % self.port, warmup=0.0, cooldown=0.0,
                    stagger=0.2, think_min=0.0, think_max=0.1, quiet=True, max_tokens=60,
                    metrics_url="auto", metrics_interval=1.0)
        base.update(kw)
        return make_cfg(**base)

    def test_closed_loop_with_metrics(self):
        cfg = self.cfg()
        w = llmload.Workload(cfg, list(llmload.DEFAULT_PROMPTS))
        with contextlib.redirect_stdout(io.StringIO()):
            s, records = llmload.run_closed_loop(cfg, w, llmload.build_opener(cfg), 3, 3, "t")
        self.assertGreater(s["n_ok"], 3)
        self.assertEqual(s["error_rate"], 0.0)
        self.assertEqual(s["reasoning_share"], 1.0)
        self.assertIsNotNone(s["itl_ms_p95"])
        self.assertIn("running", s["server_metrics"]["metrics"])

    def test_open_loop(self):
        cfg = self.cfg(arrival="constant", max_concurrency=16)
        w = llmload.Workload(cfg, list(llmload.DEFAULT_PROMPTS))
        with contextlib.redirect_stdout(io.StringIO()):
            s, records = llmload.run_open_loop(cfg, w, llmload.build_opener(cfg), 4.0, 3, "t")
        self.assertGreaterEqual(s["n_total"], 10)
        self.assertEqual(s["load_unit"], "req/s")
        self.assertTrue(all("queue_wait_s" in r for r in records))

    def test_headless_baseline_writes_reports_and_exit_code(self):
        out = tempfile.mkdtemp()
        try:
            argv = ["baseline", "--url", "http://127.0.0.1:%d/v1" % self.port, "--model", "mock",
                    "--requests", "2", "--out", out, "--lang", "id"]
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                code = llmload.main(argv)
            self.assertEqual(code, 0)
            self.assertIn("LULUS", buf.getvalue())
            files = sorted(os.listdir(out))
            self.assertEqual(len(files), 3)
            self.assertTrue(any(f.endswith("-report.html") for f in files))
            argv[-1] = "en"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(llmload.main(argv + ["--target-ttft", "0.0001"]), llmload.EXIT_SLA_FAILED)
        finally:
            llmload.set_language("en")
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
