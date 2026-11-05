"""Interface translations for llmload.py.

Keys are the English source strings used in llmload.py (via _("...")); values keep the same
%-format placeholders in the same order. Missing keys fall back to English automatically.
Run `python -m unittest discover tests` to verify coverage and placeholder consistency.
"""

ID = {
    # --- Results header & table ---------------------------------------------------------------
    "AI Server": "Server AI",
    "AI Model": "Model AI",
    "SLA Target": "Target SLA",
    "Overall Status": "Status Akhir",
    "Note": "Catatan",
    "TTFT p95 < %.1fs%s | speed >= %.0f tok/s/user | errors < %.1f%%":
        "TTFT p95 < %.1fs%s | kecepatan >= %.0f tok/s/user | error < %.1f%%",
    " (first answer token)": " (token jawaban pertama)",
    "PASSED": "LULUS",
    "CONDITIONAL PASS (capacity limit found)": "LULUS BERSYARAT (batas kapasitas ditemukan)",
    "FAILED": "GAGAL",
    "PASS": "LULUS",
    "FAIL": "GAGAL",
    "run was interrupted; results below are partial": "pengujian dihentikan; hasil di bawah bersifat parsial",
    "Load": "Beban",
    "Speed": "Kecepatan",
    "Err": "Error",
    "reasoning in %.0f%% of answers, avg %.0f tok, first-answer p95 %s":
        "reasoning di %.0f%% jawaban, rata-rata %.0f tok, jawaban-pertama p95 %s",
    "* fewer than %d successful requests: percentiles are indicative only":
        "* kurang dari %d request sukses: persentil hanya bersifat indikatif",
    "CONCLUSION & USER EXPERIENCE INSIGHTS:": "KESIMPULAN & WAWASAN PENGALAMAN PENGGUNA:",
    "%d user": "%d pengguna",
    "%d users": "%d pengguna",
    "QUICK BASELINE TEST RESULTS (1 USER)": "HASIL UJI BASELINE CEPAT (1 PENGGUNA)",
    "STEPPED LOAD TEST RESULTS": "HASIL UJI BEBAN BERTAHAP",
    "FIXED-RATE LOAD TEST RESULTS": "HASIL UJI LAJU TETAP",
    "STABILITY TEST RESULTS": "HASIL UJI STABILITAS",
    "LONG DOCUMENT (RAG) TEST RESULTS": "HASIL UJI DOKUMEN PANJANG (RAG)",
    "MULTI-TURN CHAT TEST RESULTS": "HASIL UJI CHAT MULTI-TURN",

    # --- SLA failure reasons ----------------------------------------------------------------
    "First-answer p95": "Jawaban-pertama p95",
    "no successful requests": "tidak ada request yang sukses",
    "errors %.1f%% > %.1f%%": "error %.1f%% > %.1f%%",
    "speed %.1f tok/s < %.0f tok/s": "kecepatan %.1f tok/s < %.0f tok/s",

    # --- Conclusion -------------------------------------------------------------------------
    "No results were collected.": "Tidak ada hasil yang terkumpul.",
    "All %d stages met the SLA. Highest load tested: %s.":
        "Seluruh %d tahap memenuhi SLA. Beban tertinggi yang diuji: %s.",
    "The capacity limit was not reached; add higher load levels to find it.":
        "Batas kapasitas belum tercapai; tambahkan level beban yang lebih tinggi untuk menemukannya.",
    "The test met the SLA at %s.": "Pengujian memenuhi SLA pada %s.",
    "Run a stepped or fixed-rate load test to find the capacity limit.":
        "Jalankan uji beban bertahap atau laju tetap untuk menemukan batas kapasitas.",
    "SLA held up to %s and broke at %s: %s.": "SLA bertahan hingga %s dan gagal pada %s: %s.",
    "SLA already failed at %s: %s.": "SLA sudah gagal pada %s: %s.",
    "Reliability at %s: no failed requests (%d/%d succeeded).":
        "Keandalan pada %s: tidak ada request gagal (%d/%d sukses).",
    "Reliability at %s: %.1f%% of requests failed (%s).": "Keandalan pada %s: %.1f%% request gagal (%s).",
    "feels instant": "terasa instan",
    "acceptable": "masih wajar",
    "a noticeable wait": "jeda terasa",
    "a long wait; users may give up": "menunggu lama; pengguna bisa menyerah",
    "First answer token p95 at %s: %.2fs (%s).": "Token jawaban pertama p95 pada %s: %.2fs (%s).",
    "First token p95 at %s: %.2fs (%s).": "Token pertama p95 pada %s: %.2fs (%s).",
    "Streaming speed at %s: ~%.0f tok/s (~%.0f words/s), %.1fx typical silent reading speed (~%.0f words/s).":
        "Kecepatan streaming pada %s: ~%.0f tok/s (~%.0f kata/detik), %.1fx kecepatan membaca dalam hati "
        "(~%.0f kata/detik).",
    "Text streams slower than people read; users will be waiting on the stream.":
        "Teks mengalir lebih lambat dari kecepatan membaca; pengguna akan menunggu stream.",
    "The model streams reasoning before answering (%.0f%% of responses, avg %.0f reasoning tokens). "
    "First answer token p95: %s.":
        "Model mengirim reasoning sebelum menjawab (%.0f%% respons, rata-rata %.0f token reasoning). "
        "Token jawaban pertama p95: %s.",
    "Use --ttft-basis answer to apply the SLA to the visible answer instead.":
        "Gunakan --ttft-basis answer agar SLA diukur pada jawaban yang terlihat.",
    "Time to first token is the bottleneck: requests queue or prefill is slow. Add replicas or GPUs, cap "
    "concurrent sequences per instance, enable prefix caching / chunked prefill, or shorten prompts.":
        "Waktu token pertama adalah bottleneck: request mengantre atau prefill lambat. Tambah replika atau GPU, "
        "batasi sequence bersamaan per instance, aktifkan prefix caching / chunked prefill, atau persingkat prompt.",
    "Per-user generation speed collapsed: decode is saturated. Lower the batch size per GPU, use a smaller or "
    "quantized model, enable speculative decoding, or scale out.":
        "Kecepatan generate per pengguna anjlok: decode sudah jenuh. Turunkan batch size per GPU, pakai model yang "
        "lebih kecil atau terkuantisasi, aktifkan speculative decoding, atau tambah server.",
    "Fewer than %d successful requests at %s: p95/p99 are not statistically reliable. Run longer stages or "
    "reduce think time.":
        "Kurang dari %d request sukses pada %s: p95/p99 belum andal secara statistik. Perpanjang durasi tahap atau "
        "kurangi think time.",
    "The client concurrency cap delayed dispatch (queue wait p95 %.2fs); raise --max-concurrency so latency "
    "reflects the server only.":
        "Batas konkurensi klien menunda pengiriman (antrean p95 %.2fs); naikkan --max-concurrency agar latensi "
        "hanya mencerminkan server.",
    "The server did not report token usage; token counts are estimated from stream chunks.":
        "Server tidak melaporkan pemakaian token; jumlah token diperkirakan dari potongan stream.",

    # --- Error hints ------------------------------------------------------------------------
    "HTTP 429: the server or gateway is rate limiting; raise provider limits or lower the load.":
        "HTTP 429: server atau gateway membatasi laju request; naikkan limit provider atau turunkan beban.",
    "HTTP 5xx: the backend or gateway failed under load; check server logs for OOM or crashes.":
        "HTTP 5xx: backend atau gateway gagal saat dibebani; periksa log server untuk OOM atau crash.",
    "HTTP 4xx: the request was rejected; verify model name, API key and request parameters.":
        "HTTP 4xx: request ditolak; periksa nama model, API key, dan parameter request.",
    "Timeouts: the server is overloaded or --timeout is too low for long generations.":
        "Timeout: server kelebihan beban atau --timeout terlalu kecil untuk jawaban panjang.",
    "Connection errors: the server refused, dropped or reset connections (crash/restart?).":
        "Error koneksi: server menolak, memutus, atau me-reset koneksi (crash/restart?).",
    "Protocol errors: the stream was cut off mid-response.": "Error protokol: stream terputus di tengah jawaban.",
    "No answer: the model spent all max_tokens on reasoning; raise --max-tokens.":
        "Tanpa jawaban: model menghabiskan seluruh max_tokens untuk reasoning; naikkan --max-tokens.",
    "Stream errors: the server reported an error inside the SSE stream.":
        "Error stream: server melaporkan error di dalam stream SSE.",
    "Client overflow: requests piled up faster than the server completed them.":
        "Antrean klien penuh: request menumpuk lebih cepat daripada yang bisa diselesaikan server.",

    # --- Server metrics -----------------------------------------------------------------------
    "running max %.0f": "berjalan maks %.0f",
    "waiting max %.0f": "antre maks %.0f",
    "KV-cache max %.0f%%": "KV-cache maks %.0f%%",
    "preemptions +%.0f": "preemption +%.0f",

    # --- Timeline / drift ---------------------------------------------------------------------
    "Timeline (post-warmup):": "Linimasa (setelah warmup):",
    "Window": "Jendela",
    "Stability: not enough requests in the first/last third to judge drift.":
        "Stabilitas: request di sepertiga awal/akhir belum cukup untuk menilai pergeseran.",
    "Stability: %s - TTFT p95 %s -> %s, speed %s -> %s tok/s (first vs last third)":
        "Stabilitas: %s - TTFT p95 %s -> %s, kecepatan %s -> %s tok/s (sepertiga awal vs akhir)",
    "Latency grew or speed dropped over time: suspect KV-cache pressure, memory leaks or a growing queue.":
        "Latensi naik atau kecepatan turun seiring waktu: curigai tekanan KV-cache, memory leak, atau antrean yang "
        "terus bertambah.",
    "stable": "stabil",
    "degrading": "menurun",
    "insufficient data": "data kurang",

    # --- Progress & live output ---------------------------------------------------------------
    "remaining %.0fs": "sisa %.0fs",
    "draining %d in-flight": "menunggu %d request berjalan",
    "answered: %d (failed: %s) | in-flight: %d | %s": "terjawab: %d (gagal: %s) | berjalan: %d | %s",
    "Interrupted - stopping virtual users and keeping partial results...":
        "Dihentikan - menghentikan pengguna virtual dan menyimpan hasil parsial...",
    "%s | %d concurrent users | %ds (warmup %ds)": "%s | %d pengguna bersamaan | %ds (warmup %ds)",
    "%s | %g req/s (%s arrivals) | %ds (warmup %ds)": "%s | %g req/s (kedatangan %s) | %ds (warmup %ds)",
    "Stage %d/%d (%s)": "Tahap %d/%d (%s)",
    "%s completed: %d requests | TTFT p95 %s | speed %s tok/s | errors %s":
        "%s selesai: %d request | TTFT p95 %s | kecepatan %s tok/s | error %s",
    "Stage exceeded SLA limits (%s). Stopping test early.": "Tahap melampaui batas SLA (%s). Pengujian dihentikan lebih awal.",
    "Cooling down for %ds before next stage...": "Jeda %ds sebelum tahap berikutnya...",
    "Starting Quick Baseline Test (1 user - %d sequential queries)...":
        "Memulai Uji Baseline Cepat (1 pengguna - %d pertanyaan berurutan)...",
    "Query": "Pertanyaan",
    "Reasoning": "Berpikir",
    "Streaming": "Streaming",
    "[Thinking] waiting for the first token... (%.1fs)": "[Berpikir] menunggu token pertama... (%.1fs)",
    "[Reasoning] model is thinking: %d tokens (%.1fs)": "[Reasoning] model sedang berpikir: %d token (%.1fs)",
    "[Streaming] receiving answer: %d tokens (%.1fs)": "[Streaming] menerima jawaban: %d token (%.1fs)",
    "answer after %s, %d reasoning tok": "jawaban setelah %s, %d tok reasoning",
    "Completed in %.1fs (TTFT: %s | %d tokens | %s tok/s%s)": "Selesai dalam %.1fs (TTFT: %s | %d token | %s tok/s%s)",
    "status=%s after %.1fs": "status=%s setelah %.1fs",
    "Interrupted - keeping %d completed queries.": "Dihentikan - menyimpan %d pertanyaan yang sudah selesai.",

    # --- Reports & compare --------------------------------------------------------------------
    "Generated report files:": "File laporan yang dibuat:",
    "HTML report written: %s": "Laporan HTML ditulis: %s",
    "Could not read report: %s": "Laporan tidak dapat dibaca: %s",
    "REPORT COMPARISON": "PERBANDINGAN LAPORAN",
    "No common load levels between the two reports; nothing to compare side by side.":
        "Kedua laporan tidak punya level beban yang sama; tidak ada yang bisa dibandingkan berdampingan.",
    "better": "lebih baik",
    "worse": "lebih buruk",
    "same": "sama",
    "~same": "~sama",
    "TTFT p50": "TTFT p50",
    "TTFT p95": "TTFT p95",
    "E2E p95": "E2E p95",
    "ITL p95": "ITL p95",
    "Speed/user": "Kecepatan/user",
    "Throughput": "Throughput",
    "Requests/s": "Request/detik",
    "Goodput/s": "Goodput/detik",
    "Error rate": "Tingkat error",

    # --- HTML report --------------------------------------------------------------------------
    "LLM Benchmark Report": "Laporan Benchmark LLM",
    "LLM benchmark report": "Laporan benchmark LLM",
    "%s test": "uji %s",
    "Interrupted (partial)": "Dihentikan (parsial)",
    "SLA passed": "SLA terpenuhi",
    "Capacity limit found": "Batas kapasitas ditemukan",
    "SLA failed": "SLA gagal",
    "First answer token": "Token jawaban pertama",
    "Time to first token": "Waktu token pertama",
    "Max load within SLA": "Beban maks dalam SLA",
    "None": "Tidak ada",
    "highest tested level that passed": "level tertinggi yang lulus",
    "first stage already failed": "tahap pertama sudah gagal",
    "at %s": "pada %s",
    "Speed per user": "Kecepatan per pengguna",
    "target at least %.0f tok/s": "target minimal %.0f tok/s",
    "target below %.1f%%": "target di bawah %.1f%%",
    "Conclusion": "Kesimpulan",
    "Charts": "Grafik",
    "concurrent users": "pengguna bersamaan",
    "requests per second": "request per detik",
    "%s vs load": "%s terhadap beban",
    "Seconds, by %s": "Detik, berdasarkan %s",
    "Generation speed per user": "Kecepatan generate per pengguna",
    "Tokens per second, by %s": "Token per detik, berdasarkan %s",
    "average": "rata-rata",
    "slowest 5%": "5% paling lambat",
    "Server output throughput": "Throughput output server",
    "Output tokens per second, all users combined": "Token output per detik, seluruh pengguna digabung",
    "output tok/s": "tok/s output",
    "Throughput vs goodput": "Throughput vs goodput",
    "Requests per second; goodput counts only requests that met the SLA":
        "Request per detik; goodput hanya menghitung request yang memenuhi SLA",
    "completed": "selesai",
    "within SLA": "dalam SLA",
    "%s over time": "%s sepanjang waktu",
    "Seconds, per time window after warmup": "Detik, per jendela waktu setelah warmup",
    "Generation speed over time": "Kecepatan generate sepanjang waktu",
    "Average tokens per second per user": "Rata-rata token per detik per pengguna",
    "speed": "kecepatan",
    "Server queue": "Antrean server",
    "Requests running and waiting (from /metrics)": "Request berjalan dan antre (dari /metrics)",
    "running": "berjalan",
    "waiting": "antre",
    "KV-cache usage": "Pemakaian KV-cache",
    "Percent of KV-cache in use (from /metrics)": "Persentase KV-cache terpakai (dari /metrics)",
    "Latency per query": "Latensi per pertanyaan",
    "Seconds, sequential single-user queries": "Detik, pertanyaan berurutan satu pengguna",
    "first token": "token pertama",
    "full response": "respons lengkap",
    "Results per stage": "Hasil per tahap",
    "Requests": "Request",
    "Answer p95": "Jawaban p95",
    "Speed avg": "Kecepatan rata-rata",
    "Speed p5": "Kecepatan p5",
    "Output tok/s": "Tok/s output",
    "Errors": "Error",
    "Pass": "Lulus",
    "Fail": "Gagal",
    "Server": "Server",
    "Timeline": "Linimasa",
    "Stability verdict: %s. TTFT p95 %s -> %s, speed %s -> %s tok/s (first vs last third of the window).":
        "Penilaian stabilitas: %s. TTFT p95 %s -> %s, kecepatan %s -> %s tok/s (sepertiga awal vs akhir jendela).",
    "Server URL": "URL Server",
    "Model": "Model",
    "%s p95 < %.1fs, speed >= %.0f tok/s/user, errors < %.1f%%":
        "%s p95 < %.1fs, kecepatan >= %.0f tok/s/user, error < %.1f%%",
    "environment": "lingkungan",
    "Test configuration": "Konfigurasi pengujian",
    "Generated by %s %s. Percentiles use the nearest-rank method; requests are attributed to the window in which "
    "they started.":
        "Dibuat oleh %s %s. Persentil memakai metode nearest-rank; request dihitung pada jendela tempat request "
        "dimulai.",

    # --- Connection check ---------------------------------------------------------------------
    "Invalid URL format: it must start with http:// or https://":
        "Format URL tidak valid: harus diawali http:// atau https://",
    "Example: %s": "Contoh: %s",
    "Fix the URL via the Server Config menu (s).": "Perbaiki URL lewat menu Konfigurasi Server (s).",
    "Checking connection to %s ...": "Memeriksa koneksi ke %s ...",
    "server rejected stream_options; token usage reporting disabled for this run":
        "server menolak stream_options; pelaporan pemakaian token dimatikan untuk pengujian ini",
    "Connected.": "Terhubung.",
    "First token %.2fs": "Token pertama %.2fs",
    "first answer token %s (model streams reasoning: %d tokens)":
        "token jawaban pertama %s (model mengirim reasoning: %d token)",
    "%d tokens generated": "%d token dihasilkan",
    "estimated from stream chunks": "diperkirakan dari potongan stream",
    "Server metrics: %s (%s)": "Metrik server: %s (%s)",
    "Server metrics: %s responded but no known vLLM/llama.cpp/SGLang/TGI gauges were found.":
        "Metrik server: %s merespons tetapi tidak ada gauge vLLM/llama.cpp/SGLang/TGI yang dikenali.",
    "Server metrics unavailable at %s (%s); continuing without them.":
        "Metrik server tidak tersedia di %s (%s); pengujian dilanjutkan tanpa metrik.",
    "Endpoint URL not found. Ensure the path ends with '/chat/completions'.":
        "URL endpoint tidak ditemukan. Pastikan path diakhiri '/chat/completions'.",
    "Authentication error: API key invalid or missing.": "Error autentikasi: API key tidak valid atau kosong.",
    "Forbidden: API key lacks access, or quota is exhausted.": "Ditolak: API key tidak punya akses, atau kuota habis.",
    "Request rejected. Check the model name; vLLM-only options (--min-tokens, --ignore-eos) are refused by other "
    "servers.":
        "Request ditolak. Periksa nama model; opsi khusus vLLM (--min-tokens, --ignore-eos) ditolak oleh server lain.",
    "Invalid URL format.": "Format URL tidak valid.",
    "The model only produced reasoning tokens before max_tokens ran out; raise max_tokens.":
        "Model hanya menghasilkan token reasoning sebelum max_tokens habis; naikkan max_tokens.",
    "No response before --timeout; the server may be loading the model or overloaded.":
        "Tidak ada respons sebelum --timeout; server mungkin sedang memuat model atau kelebihan beban.",
    "Could not connect. Is the server running and reachable from this machine?":
        "Tidak dapat terhubung. Apakah server berjalan dan bisa dijangkau dari mesin ini?",
    "Please verify URL, API key and model name.": "Periksa kembali URL, API key, dan nama model.",

    # --- Menu ---------------------------------------------------------------------------------
    "LLM Latency, Speed & Concurrency Benchmark": "Benchmark Latensi, Kecepatan & Konkurensi LLM",
    "(not configured)": "(belum diatur)",
    "From LLM_API_KEY": "Dari LLM_API_KEY",
    "Saved in config": "Tersimpan di config",
    "Session only (not saved)": "Hanya sesi ini (tidak disimpan)",
    "Not set (no key)": "Belum diatur (tanpa key)",
    "Prompts": "Prompt",
    "Default (%d general queries)": "Bawaan (%d pertanyaan umum)",
    "TTFT < %.1fs%s | Errors < %.1f%% | Speed >= %.0f tok/s": "TTFT < %.1fs%s | Error < %.1f%% | Kecepatan >= %.0f tok/s",
    " (answer)": " (jawaban)",
    "Server Metrics": "Metrik Server",
    "Quick 1-User Test": "Uji Cepat 1 Pengguna",
    "Initial latency & peak single-user speed": "Latensi awal & kecepatan puncak 1 pengguna",
    "Stepped Load Test": "Uji Beban Bertahap",
    "Ramp up concurrent users to find the capacity limit": "Naikkan pengguna bertahap untuk cari batas kapasitas",
    "Fixed-Rate Load Test": "Uji Laju Tetap",
    "Open-loop req/s arrivals (realistic traffic)": "Kedatangan req/s open-loop (trafik realistis)",
    "Stability Soak Test": "Uji Stabilitas (Soak)",
    "Sustained load over time (detect leaks/drift)": "Beban konstan jangka panjang (deteksi leak/drift)",
    "Long Document Test (RAG)": "Uji Dokumen Panjang (RAG)",
    "Queries wrapped with heavy document context": "Pertanyaan dibungkus konteks dokumen panjang",
    "Multi-Turn Chat Test": "Uji Chat Multi-Turn",
    "Conversations whose history grows each turn": "Percakapan dengan riwayat yang terus bertambah",
    "Compare Reports": "Bandingkan Laporan",
    "Side-by-side diff of two test runs": "Bandingkan dua hasil pengujian berdampingan",
    "View Output Files": "Lihat File Hasil",
    "Browse CSV, JSON and HTML reports": "Telusuri laporan CSV, JSON, dan HTML",
    "Server Config": "Konfigurasi Server",
    "Endpoint URL, model name, API key": "URL endpoint, nama model, API key",
    "SLA Standards": "Standar SLA",
    "Latency, throughput and error tolerance": "Toleransi latensi, throughput, dan error",
    "Prompt List": "Daftar Prompt",
    "Use a custom query file (.txt)": "Pakai file pertanyaan sendiri (.txt)",
    "Advanced Options": "Opsi Lanjutan",
    "System prefix, fixed output, server metrics": "Prefix sistem, output tetap, metrik server",
    "Exit": "Keluar",
    "Quit benchmark application": "Tutup aplikasi benchmark",
    "Select menu option": "Pilih menu",
    "Invalid menu option.": "Pilihan menu tidak valid.",
    "Press Enter to return to menu ...": "Tekan Enter untuk kembali ke menu ...",
    "Initial setup. Please enter server URL and model name.": "Pengaturan awal. Masukkan URL server dan nama model.",
    "Done.": "Selesai.",
    "Language set to English.": "Bahasa diatur ke Bahasa Indonesia.",

    # --- Test plan ----------------------------------------------------------------------------
    "BENCHMARK TEST PLAN": "RENCANA PENGUJIAN BENCHMARK",
    "Model under Test": "Model yang Diuji",
    "Load Scenario": "Skenario Beban",
    "Output Length": "Panjang Output",
    "Stepped load (%s users) | Est. duration: ~%d min": "Beban bertahap (%s pengguna) | Estimasi durasi: ~%d menit",
    "Fixed rate (%s req/s, %s) | Est. duration: ~%d min": "Laju tetap (%s req/s, %s) | Estimasi durasi: ~%d menit",
    "Quick baseline (%d sequential queries)": "Baseline cepat (%d pertanyaan berurutan)",
    "Sustained %d concurrent users | Est. duration: ~%d min": "%d pengguna bersamaan konstan | Estimasi durasi: ~%d menit",
    "max %d tokens": "maks %d token",
    "%d query variations (%s) | %s": "%d variasi pertanyaan (%s) | %s",
    "custom file": "file sendiri",
    "built-in set": "set bawaan",
    "curated defaults": "bawaan terkurasi",
    "Unknown built-in prompt set: %s (available: %s)": "Set prompt bawaan tidak dikenal: %s (tersedia: %s)",
    "TTFT p95 < %.1fs, speed >= %.0f tok/s, errors < %.1f%%": "TTFT p95 < %.1fs, kecepatan >= %.0f tok/s, error < %.1f%%",
    "document %s words": "dokumen %s kata",
    "system prompt %d words (%s prefix)": "system prompt %d kata (prefix %s)",
    "%d-turn conversations": "percakapan %d giliran",
    "single-turn chat": "chat satu giliran",
    "--url and --model are required.": "--url dan --model wajib diisi.",
    "Server configuration incomplete.": "Konfigurasi server belum lengkap.",
    "Invalid setting: %s": "Pengaturan tidak valid: %s",
    "Start benchmark test now?": "Mulai pengujian benchmark sekarang?",
    "Benchmark cancelled. Returning to main menu.": "Benchmark dibatalkan. Kembali ke menu utama.",

    # --- Input helpers ------------------------------------------------------------------------
    "required": "wajib diisi",
    "invalid value": "nilai tidak valid",
    "choose one of: %s": "pilih salah satu: %s",
    "please enter y or n": "masukkan y atau n",
    "configuration could not be saved: %s": "konfigurasi tidak dapat disimpan: %s",

    # --- Server config ------------------------------------------------------------------------
    "AI Server Configuration": "Konfigurasi Server AI",
    "Server endpoint URL (e.g., http://localhost:4000/v1/chat/completions)":
        "URL endpoint server (mis. http://localhost:4000/v1/chat/completions)",
    "URL automatically updated to: %s": "URL otomatis diubah menjadi: %s",
    "URL must start with http:// or https://": "URL harus diawali http:// atau https://",
    "AI model name (e.g., qwen-30b, llama3, mistral-small-latest)":
        "Nama model AI (mis. qwen-30b, llama3, mistral-small-latest)",
    "API key is taken from the LLM_API_KEY environment variable.":
        "API key diambil dari environment variable LLM_API_KEY.",
    "API Key (Enter = keep current key):": "API Key (Enter = pakai key yang ada):",
    "API Key (Enter = none):": "API Key (Enter = tanpa key):",
    "Store the API key in llmload.conf? It is saved as plain text (n = keep it for this session only)":
        "Simpan API key di llmload.conf? Key disimpan sebagai teks biasa (n = hanya untuk sesi ini)",
    "Max generation length (tokens)": "Panjang maksimum jawaban (token)",
    "Skip HTTPS certificate verification?": "Lewati verifikasi sertifikat HTTPS?",
    "Request server token usage reporting?": "Minta server melaporkan pemakaian token?",
    "Server configuration saved to %s": "Konfigurasi server disimpan ke %s",

    # --- SLA config ---------------------------------------------------------------------------
    "Performance SLA Standards (Passing Criteria)": "Standar SLA Performa (Kriteria Lulus)",
    "These thresholds determine whether a load stage is PASSED or FAILED.":
        "Ambang batas ini menentukan apakah sebuah tahap beban LULUS atau GAGAL.",
    "Max first token wait time / TTFT p95 (seconds)": "Maks waktu tunggu token pertama / TTFT p95 (detik)",
    "Max acceptable error rate (%)": "Maks tingkat error yang dapat diterima (%)",
    "Min generation speed per user (tokens/second)": "Min kecepatan generate per pengguna (token/detik)",
    "For reasoning models: 'token' = any first token (incl. thinking), 'answer' = first visible answer token.":
        "Untuk model reasoning: 'token' = token pertama apa pun (termasuk berpikir), 'answer' = token jawaban "
        "pertama yang terlihat.",
    "TTFT basis (token/answer)": "Dasar TTFT (token/answer)",
    "SLA passing standards updated.": "Standar kelulusan SLA diperbarui.",

    # --- Prompts & advanced -------------------------------------------------------------------
    "Custom Prompts Setup": "Pengaturan Prompt Sendiri",
    "Provide a .txt file with one query per line, or press Enter for the default queries.":
        "Masukkan file .txt berisi satu pertanyaan per baris, atau tekan Enter untuk pertanyaan bawaan.",
    "Indonesian sample set: %s": "Contoh set bahasa Indonesia: %s",
    "Path to .txt prompt file (Enter = use default queries)": "Path file prompt .txt (Enter = pakai pertanyaan bawaan)",
    "Prompt list updated.": "Daftar prompt diperbarui.",
    "Prompts file is empty: %s": "File prompt kosong: %s",
    "Failed to open prompts file: %s": "Gagal membuka file prompt: %s",
    "Advanced Workload Options": "Opsi Beban Kerja Lanjutan",
    "System prompt words > 0 adds a fixed system prompt; 'unique' gives each conversation its own":
        "Jumlah kata system prompt > 0 menambahkan system prompt tetap; 'unique' memberi tiap percakapan",
    "prefix so server prefix caching cannot help (compare both to measure the cache benefit).":
        "prefix sendiri agar prefix caching server tidak membantu (bandingkan keduanya untuk mengukur manfaat cache).",
    "System prompt length (words, 0 = none)": "Panjang system prompt (kata, 0 = tidak ada)",
    "Prefix mode (shared/unique)": "Mode prefix (shared/unique)",
    "Fixed output length (vLLM only): min_tokens / ignore_eos make runs comparable across models.":
        "Panjang output tetap (khusus vLLM): min_tokens / ignore_eos membuat hasil antar-model bisa dibandingkan.",
    "Min output tokens (0 = off)": "Min token output (0 = mati)",
    "Ignore end-of-sequence (always generate max_tokens)?": "Abaikan end-of-sequence (selalu generate max_tokens)?",
    "Prometheus metrics URL, e.g. http://host:8000/metrics, 'auto' (same host as the API), or empty.":
        "URL metrik Prometheus, mis. http://host:8000/metrics, 'auto' (host yang sama dengan API), atau kosong.",
    "Server metrics URL": "URL metrik server",
    "Write an HTML report after each test?": "Buat laporan HTML setiap selesai pengujian?",
    "Hide the per-request log lines during load tests?": "Sembunyikan log per request saat uji beban?",
    "Advanced options saved.": "Opsi lanjutan disimpan.",

    # --- Load & presets -----------------------------------------------------------------------
    "Simulate User Reading Time (Think Time):": "Simulasi Waktu Baca Pengguna (Think Time):",
    "(Enter 0 and 0 for continuous aggressive stress testing)": "(Isi 0 dan 0 untuk stress test agresif tanpa jeda)",
    "Min reading delay / think time (seconds)": "Min jeda baca / think time (detik)",
    "Max reading delay / think time (seconds)": "Maks jeda baca / think time (detik)",
    "Initial warmup duration to exclude from metrics (seconds)": "Durasi warmup awal yang tidak dihitung (detik)",
    "Stepped Load Test Presets": "Preset Uji Beban Bertahap",
    "Quick (~2-3 min)": "Cepat (~2-3 menit)",
    "1, 5, 10 users (45s/stage, ideal for quick check)": "1, 5, 10 pengguna (45 dtk/tahap, cocok untuk cek cepat)",
    "Standard (~8-10 min)": "Standar (~8-10 menit)",
    "5, 10, 20, 30 users (120s/stage, realistic human chat)":
        "5, 10, 20, 30 pengguna (120 dtk/tahap, chat manusia realistis)",
    "Stress Test": "Stress Test",
    "5, 15, 30, 50 users (60s/stage, 0s think time, GPU limit)":
        "5, 15, 30, 50 pengguna (60 dtk/tahap, think time 0, batas GPU)",
    "Custom": "Kustom",
    "define users, duration and think time": "tentukan pengguna, durasi, dan think time",
    "Select preset": "Pilih preset",
    "User stages (e.g., 1,5,10,20)": "Tahapan pengguna (mis. 1,5,10,20)",
    "Duration per stage (seconds)": "Durasi per tahap (detik)",
    "Cooldown between stages (seconds)": "Jeda antar tahap (detik)",
    "Fixed-Rate Load Test (Open Loop)": "Uji Laju Tetap (Open Loop)",
    "New requests arrive at a fixed rate whether or not earlier ones finished, like real traffic":
        "Request baru datang dengan laju tetap meski request sebelumnya belum selesai, seperti trafik nyata",
    "from many independent users. Latency here does not hide server slowdowns.":
        "dari banyak pengguna independen. Latensi di sini tidak menutupi perlambatan server.",
    "Quick": "Cepat",
    "0.5, 1, 2 req/s (60s/stage)": "0.5, 1, 2 req/s (60 dtk/tahap)",
    "Standard": "Standar",
    "0.5, 1, 2, 4, 8 req/s (120s/stage)": "0.5, 1, 2, 4, 8 req/s (120 dtk/tahap)",
    "define rates and duration": "tentukan laju dan durasi",
    "Request rates (req/s, e.g., 0.5,1,2,4)": "Laju request (req/s, mis. 0.5,1,2,4)",
    "Arrival pattern (poisson/constant)": "Pola kedatangan (poisson/constant)",
    "Stability Test Presets (Long-Running Soak)": "Preset Uji Stabilitas (Soak Jangka Panjang)",
    "Quick Soak": "Soak Cepat",
    "10 users for 5 minutes (early memory leak check)": "10 pengguna selama 5 menit (cek awal memory leak)",
    "Standard Soak": "Soak Standar",
    "20 users for 30 minutes (normal stability verification)": "20 pengguna selama 30 menit (verifikasi stabilitas normal)",
    "Full Soak": "Soak Penuh",
    "30 users for 1 hour (production endurance test)": "30 pengguna selama 1 jam (uji ketahanan produksi)",
    "specify users and duration manually": "tentukan pengguna dan durasi secara manual",
    "Number of concurrent users": "Jumlah pengguna bersamaan",
    "Test duration (seconds)": "Durasi pengujian (detik)",

    # --- Files & compare menu -----------------------------------------------------------------
    "Benchmark Report Files in '%s'": "File Laporan Benchmark di '%s'",
    "No benchmark reports found yet. Please run a test first.":
        "Belum ada laporan benchmark. Jalankan pengujian terlebih dahulu.",
    "... and %d more files": "... dan %d file lainnya",
    "Open the *-report.html files in a browser for charts.": "Buka file *-report.html di browser untuk melihat grafik.",
    "Compare Two Reports": "Bandingkan Dua Laporan",
    "At least two summary reports are needed. Run a few tests first.":
        "Minimal dibutuhkan dua laporan ringkasan. Jalankan beberapa pengujian dulu.",
    "Baseline report A (number)": "Laporan acuan A (nomor)",
    "New report B (number)": "Laporan baru B (nomor)",

    # --- Test menus ---------------------------------------------------------------------------
    "Quick 1-User Test (Peak Speed Limit)": "Uji Cepat 1 Pengguna (Kecepatan Puncak)",
    "Number of sequential queries to test": "Jumlah pertanyaan berurutan yang diuji",
    "Long Document Scenario (RAG)": "Skenario Dokumen Panjang (RAG)",
    "Queries are wrapped with a long document. Use a range like 500-4000 to mix short and long.":
        "Pertanyaan dibungkus dokumen panjang. Gunakan rentang seperti 500-4000 untuk mencampur pendek dan panjang.",
    "Document length in words (N or MIN-MAX)": "Panjang dokumen dalam kata (N atau MIN-MAKS)",
    "Each user keeps a conversation: every answer is added to the history of the next question,":
        "Setiap pengguna mempertahankan percakapan: tiap jawaban ditambahkan ke riwayat pertanyaan berikutnya,",
    "so prompts grow turn by turn (tests KV-cache and prefix caching realistically).":
        "sehingga prompt makin panjang tiap giliran (menguji KV-cache dan prefix caching secara realistis).",
    "Turns per conversation": "Giliran per percakapan",
}

TRANSLATIONS = {"id": ID}
