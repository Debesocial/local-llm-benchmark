# LLM Benchmark 🚀

[English](./README.md) · **Bahasa Indonesia**

> **Alat uji beban dan benchmark konkurensi yang ringan dan tanpa dependensi untuk inference engine LLM dan API yang kompatibel dengan OpenAI.**

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(Pure%20Stdlib)-orange.svg)](#fitur-utama)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#mulai-cepat)

```text
==========================================================================
  (\·▛▀▀▀▜·/)   LLM Benchmark  v2.0.0
   ▜ • ‿ • ▛▘   Benchmark Latensi, Kecepatan & Konkurensi LLM
    ▘▘   ▝▝
==========================================================================
```

---

## Daftar Isi
- [Mengapa LLM Benchmark?](#mengapa-llm-benchmark)
- [Fitur Utama](#fitur-utama)
- [Provider & Inference Engine yang Didukung](#provider--inference-engine-yang-didukung)
- [Mulai Cepat](#mulai-cepat)
- [Skenario Pengujian](#skenario-pengujian)
- [Metrik & Evaluasi SLA](#metrik--evaluasi-sla)
- [Model Reasoning](#model-reasoning-deepseek-r1-qwen3-qwq-gpt-oss)
- [Metrik Sisi Server](#metrik-sisi-server-vllm-llamacpp-sglang-tgi)
- [Laporan: CSV, JSON, HTML, Compare](#laporan-csv-json-html-compare)
- [Bahasa (English / Bahasa Indonesia)](#bahasa-english--bahasa-indonesia)
- [API Key & Keamanan](#api-key--keamanan)
- [Uji Lokal Gratis (Mock LLM Server)](#uji-lokal-gratis-mock-llm-server)
- [Menjalankan Tes](#menjalankan-tes)
- [Struktur Proyek](#struktur-proyek)
- [Upgrade dari v1](#upgrade-dari-v1)
- [Kontribusi](#kontribusi)
- [Lisensi](#lisensi)

---

## Mengapa LLM Benchmark?

Benchmark LLM butuh pendekatan yang berbeda dari stress test web server biasa. Di aplikasi web standar, request singkat dan tidak streaming. Pada LLM:
* **Time-to-First-Token (TTFT)** menentukan apakah pengguna merasa sistem responsif atau lambat.
* **Kecepatan generate token (token/detik per pengguna)** menentukan kelancaran jawaban yang mengalir.
* **Kejenuhan memori GPU (KV-cache)** bisa memicu penurunan performa mendadak atau crash OOM saat pengguna bertambah.
* **Beban berjam-jam** bisa memunculkan memory leak atau antrean yang menumpuk di inference server.

**LLM Benchmark** menyimulasikan pola chat manusia sungguhan (think time, mulai bergiliran, percakapan yang makin panjang) serta trafik open-loop dengan laju request tetap, lalu mengubah hasil pengukuran menjadi keputusan SLA yang jelas untuk tim engineering dan produk.

---

## Fitur Utama

* ⚡ **Tanpa dependensi eksternal:** 100% Python Standard Library. **Tidak perlu `pip install`.**
* 🌐 **Kompatibel dengan API OpenAI:** berjalan di server atau gateway apa pun yang menyediakan `/v1/chat/completions` dengan streaming SSE.
* 🧠 **Beban kerja realistis:** pengguna virtual closed-loop dengan think time, **laju request tetap open-loop** (Poisson atau konstan), **percakapan multi-turn** dengan riwayat yang bertambah, dokumen RAG panjang dengan **panjang campuran**, serta **system prefix** shared vs unique untuk mengukur prefix caching.
* 🧩 **Paham model reasoning:** memisahkan token pertama apa pun (berpikir) dari **token jawaban pertama yang terlihat**.
* 📏 **Profil latensi lengkap:** TTFT, waktu ke jawaban pertama, latensi end-to-end, **TPOT**, **inter-token latency (ITL)**, token input/output, kecepatan prefill, dan **goodput**.
* 🚦 **Ambang SLA bawaan** per tahap beban: TTFT p95 (bawaan `< 3.0 dtk`), kecepatan per pengguna (bawaan `>= 15 tok/s`), dan tingkat error (bawaan `< 1.0%`).
* 📈 **Linimasa soak & deteksi drift:** metrik per jendela waktu dan penilaian otomatis stabil/menurun.
* 🖥️ **Pengambilan metrik server:** mengambil sampel Prometheus `/metrics` (request berjalan/antre, pemakaian KV-cache, preemption) selama tiap tahap.
* 📊 **Laporan:** CSV per request, ringkasan JSON dengan persentil, **laporan HTML dengan grafik** dalam satu file (mode terang & gelap), dan perintah **compare** untuk membandingkan sebelum/sesudah.
* 🛑 **Penghentian aman:** Ctrl+C berhenti dengan rapi dan tetap menyimpan hasil parsial.
* 🤖 **Siap CI/CD:** subcommand headless dan **exit code** yang bermakna.
* 🌏 **Antarmuka dwibahasa:** English dan Bahasa Indonesia, di terminal maupun laporan HTML.

---

## Provider & Inference Engine yang Didukung

| Platform / Provider | Contoh URL Endpoint | Keterangan |
| :--- | :--- | :--- |
| **vLLM** | `http://localhost:8000/v1/chat/completions` | Inference engine GPU lokal berthroughput tinggi |
| **Ollama** | `http://localhost:11434/v1/chat/completions` | Model open-source lokal (Llama 3, Mistral, Qwen, dll.) |
| **llama.cpp server** | `http://localhost:8080/v1/chat/completions` | Inference CPU/GPU ringan (`llama-server`) |
| **SGLang** | `http://localhost:30000/v1/chat/completions` | Serving berthroughput tinggi dengan RadixAttention |
| **LiteLLM Gateway** | `http://localhost:4000/v1/chat/completions` | Proxy multi-provider, router, dan load balancer |
| **Mistral AI** | `https://api.mistral.ai/v1/chat/completions` | API cloud resmi Mistral |
| **OpenAI** | `https://api.openai.com/v1/chat/completions` | GPT-4o, GPT-4o-mini, dan model kompatibel |
| **DeepSeek** | `https://api.deepseek.com/v1/chat/completions` | API DeepSeek-V3 dan DeepSeek-R1 |
| **Groq** | `https://api.groq.com/openai/v1/chat/completions` | Inference engine LPU yang sangat cepat |
| **LM Studio** | `http://localhost:1234/v1/chat/completions` | Aplikasi desktop model lokal |
| **LocalAI / TGI** | `http://localhost:8080/v1/chat/completions` | Hugging Face Text Generation Inference / LocalAI |

> [!TIP]
> URL dasar yang berakhiran `/v1` otomatis dilengkapi menjadi `/v1/chat/completions`.

---

## Mulai Cepat

**Kebutuhan:** Python 3.9 atau lebih baru di Windows 10/11, Linux, atau macOS.

### Pasang sebagai perintah (disarankan)

```bash
pip install .            # dari folder proyek (atau: pipx install .  /  pip install git+<url-repo-kamu>)
llm-benchmark            # membuka menu interaktif
llm-benchmark ramp --url http://localhost:8000/v1 --model qwen-30b --levels 5,10,20
llm-benchmark-mock       # mock server lokal untuk mencoba
```

`pip install -e .` untuk instalasi mode pengembangan. `pip uninstall llm-benchmark` untuk menghapus. Paket ini tanpa dependensi dan tidak dipublikasikan ke PyPI; pasang dari salinan lokal atau URL Git. Launcher di bawah tetap bisa dipakai tanpa instalasi apa pun.

Setelah dipasang, pengaturan disimpan per pengguna, bukan di sebelah program:

| OS | File pengaturan |
| :--- | :--- |
| Windows | `%APPDATA%\llm-benchmark\llmload.conf` |
| Linux | `~/.config/llm-benchmark/llmload.conf` (mengikuti `XDG_CONFIG_HOME`) |
| macOS | `~/Library/Application Support/llm-benchmark/llmload.conf` |

Isi `LLMLOAD_CONFIG=/path/ke/file.conf` untuk memakai lokasi lain. Salinan source (atau `llmload.conf` yang sudah ada di sebelah `llmload.py`) tetap memakai file itu, jadi pengaturan lama tidak berubah. Laporan ditulis ke `./hasil` di folder tempat perintah dijalankan (ubah dengan `--out`).

### Windows
* Klik dua kali [`run.bat`](./run.bat), atau jalankan `run.bat` / `.\run.ps1` / `python llmload.py menu --lang id`.

> [!TIP]
> Di Windows, pastikan Python dipasang dengan opsi **"Add python.exe to PATH"** dicentang.

### Linux & macOS
```bash
chmod +x run.sh
./run.sh --lang id      # atau: python3 llmload.py menu --lang id
```

### CLI Headless (Otomasi & CI/CD)

```bash
# Baseline satu pengguna
python llmload.py baseline --url http://localhost:8000/v1 --model qwen-30b --requests 10 --lang id

# Pengguna bersamaan bertahap (closed loop) - mencari kapasitas
python llmload.py ramp --url http://localhost:8000/v1 --model qwen-30b --levels 5,10,20,30 --duration 120

# Laju request tetap (open loop) - trafik realistis yang tidak ikut melambat
python llmload.py rate --url http://localhost:8000/v1 --model qwen-30b --rates 0.5,1,2,4 --duration 120

# Uji stabilitas jangka panjang dengan metrik server
python llmload.py soak --url http://localhost:8000/v1 --model qwen-30b --users 20 --duration 1800 --metrics-url auto

# RAG: dokumen 500-4000 kata, percakapan 4 giliran, prompt bahasa Indonesia
python llmload.py soak --url ... --model ... --users 10 --duration 600 --pad-words 500-4000 --turns 4 \
    --prompts builtin:id --lang id
```

Berikan API key lewat environment variable `LLM_API_KEY`. Cara ini lebih aman daripada `--key`, yang akan tersimpan di riwayat shell.

**Exit code:**

| Kode | Arti |
| :--- | :--- |
| `0` | Semua tahap memenuhi SLA |
| `1` | Error pengaturan atau koneksi (URL salah, autentikasi gagal, file tidak ada) |
| `2` | Pengujian berjalan tetapi minimal satu tahap gagal SLA |
| `130` | Dihentikan dengan Ctrl+C (hasil parsial sudah disimpan) |

Jalankan `python llmload.py <subcommand> --help` untuk melihat semua opsi.

---

## Skenario Pengujian

| Menu | Subcommand | Skenario | Pertanyaan yang dijawab |
| :---: | :--- | :--- | :--- |
| 1 | `baseline` | **Uji Cepat 1 Pengguna** | Latensi dan kecepatan terbaik tanpa antrean |
| 2 | `ramp` | **Uji Beban Bertahap** (closed loop) | Berapa banyak pengguna chat bersamaan yang masih memenuhi SLA? Berhenti di tahap pertama yang gagal. |
| 3 | `rate` | **Uji Laju Tetap** (open loop) | Laju kedatangan (req/s) berapa yang sanggup dilayani server? Request baru tetap datang meski server melambat, jadi kelebihan beban tidak tersembunyi. |
| 4 | `soak` | **Uji Stabilitas (Soak)** | Apakah latensi bergeser selama 30-60 menit (memory leak, tekanan KV-cache, antrean menumpuk)? |
| 5 | `soak --pad-words` | **Uji Dokumen Panjang (RAG)** | Seberapa besar pengaruh prompt panjang terhadap prefill dan TTFT? Gunakan rentang seperti `500-4000` untuk mencampur panjang. |
| 6 | `soak --turns` | **Uji Chat Multi-Turn** | Tiap jawaban ditambahkan ke pertanyaan berikutnya, sehingga prompt makin panjang seperti chat sungguhan. |

**Opsi beban kerja** (flag CLI, atau menu `a` = Opsi Lanjutan):

| Opsi | Kegunaan |
| :--- | :--- |
| `--system-words N` + `--prefix-mode shared\|unique` | Menambahkan system prompt. Bandingkan `shared` (ramah cache) dengan `unique` (mematahkan cache) untuk mengukur manfaat prefix caching. |
| `--min-tokens N`, `--ignore-eos` | Khusus vLLM: mengunci panjang output agar hasil antar-model atau antar-konfigurasi bisa dibandingkan. |
| `--think-min/--think-max` | Simulasi waktu baca di antara pertanyaan pengguna (`0 0` = stress agresif). |
| `--warmup`, `--cooldown` | Detik di awal dan akhir tiap tahap yang tidak dihitung. |
| `--arrival poisson\|constant`, `--max-concurrency` | Pola kedatangan dan batas konkurensi klien untuk uji `rate`. |

Request yang gagal dicoba lagi setelah minimal 1 detik, sehingga server yang langsung membalas HTTP 429 tidak dibanjiri hot loop.

---

## Metrik & Evaluasi SLA

| Metrik | Bahasa Sederhana | Catatan |
| :--- | :--- | :--- |
| **TTFT (p50/p95/p99)** | Waktu tunggu sampai token pertama | Metrik utama responsivitas. Target `< 2-3 dtk`. |
| **Token jawaban pertama (TTFA)** | Waktu tunggu sampai jawaban yang terlihat mulai muncul | Berbeda dari TTFT hanya untuk model reasoning. |
| **E2E (p50/p95/p99)** | Total waktu respons | Dari request dikirim sampai stream selesai. |
| **Kecepatan per pengguna (tok/s)** | Seberapa cepat jawaban mengalir | `1 / TPOT`. Orang membaca sekitar 4 kata/detik (≈ 5-6 tok/s); `>= 15 tok/s` terasa lancar. |
| **TPOT / ITL** | Waktu per token output / jeda antar potongan stream | ITL p95/p99 menunjukkan tersendat-sendat saat GPU jenuh. |
| **Throughput** | Token output/detik dan request/detik seluruh server | |
| **Goodput** | Request/detik yang masing-masing memenuhi SLA | Throughput yang benar-benar dirasakan baik oleh pengguna. |
| **Tingkat error** | Persentase request gagal | HTTP 429/5xx, timeout, error koneksi, jawaban kosong atau hanya reasoning. |
| **Kecepatan prefill** | Token input/detik sebelum token pertama | Butuh `usage.prompt_tokens` dari server. |

**Cara sebuah tahap dinilai**

* Hanya request yang **dimulai** di dalam jendela pengukuran yang dihitung (setelah warmup, sebelum cooldown). Request lambat yang selesai setelah tahap berakhir **tetap dihitung**, sehingga latensi ekor tidak terlihat lebih bagus dari kenyataan.
* Persentil memakai metode nearest-rank. Tahap dengan **kurang dari 20 request sukses** diberi tanda, karena p95/p99-nya praktis sama dengan nilai maksimum.
* Kesimpulan disusun dari data yang terukur: beban tertinggi yang lulus, beban pertama yang gagal beserta alasannya, tingkat error dan penyebab kegagalan yang sebenarnya, serta rekomendasi untuk bottleneck TTFT, kecepatan, atau error.

### Contoh Ringkasan Evaluasi (angka ilustrasi)

```text
==============================================================================
                    LLM Benchmark - HASIL UJI BEBAN BERTAHAP
==============================================================================
  Server AI      : http://localhost:8000/v1/chat/completions
  Model AI       : qwen-30b
  Target SLA     : TTFT p95 < 3.0s | kecepatan >= 15 tok/s/user | error < 1.0%
  Status Akhir   : LULUS BERSYARAT (batas kapasitas ditemukan)
------------------------------------------------------------------------------
  Beban           n  TTFT95  E2E95   Kecepatan  ITL95   Error  Goodput   SLA
  5 pengguna     48  0.42s   6.1s    68 tok/s   19ms    0.0%   0.40/s    LULUS
  10 pengguna    97  0.61s   7.4s    55 tok/s   24ms    0.0%   0.81/s    LULUS
                     server: berjalan maks 10 | antre maks 0 | KV-cache maks 41%
  20 pengguna   188  3.84s   14.9s   29 tok/s   61ms    1.6%   1.12/s    GAGAL
                     server: berjalan maks 16 | antre maks 5 | KV-cache maks 98%
------------------------------------------------------------------------------
  KESIMPULAN & WAWASAN PENGALAMAN PENGGUNA:
  [!] SLA bertahan hingga 10 pengguna dan gagal pada 20 pengguna: TTFT p95 3.84s > 3.0s; error 1.6% > 1.0%.
   -  Keandalan pada 10 pengguna: tidak ada request gagal (97/97 sukses).
   -  Token pertama p95 pada 10 pengguna: 0.61s (terasa instan).
   -  Kecepatan streaming pada 10 pengguna: ~55 tok/s (~41 kata/detik), 10.3x kecepatan membaca dalam hati (~4 kata/detik).
  ->  Waktu token pertama adalah bottleneck: request mengantre atau prefill lambat. ...
  ->  Timeout: server kelebihan beban atau --timeout terlalu kecil untuk jawaban panjang.
==============================================================================
```

---

## Model Reasoning (DeepSeek-R1, Qwen3, QwQ, gpt-oss)

Model reasoning mengirim proses "berpikir" lewat `delta.reasoning_content` (atau `delta.reasoning`) sebelum jawaban. Alat ini mengukur keduanya:

* **TTFT**: token pertama apa pun. Pakai ini jika UI kamu menampilkan proses berpikir.
* **TTFA**: token pertama dari jawaban yang terlihat. Gunakan `--ttft-basis answer` (atau menu `t`) agar SLA diukur dari sini.

Respons yang hanya berisi reasoning (model kehabisan `max_tokens` saat berpikir) dilaporkan sebagai kegagalan `no_answer`.

---

## Metrik Sisi Server (vLLM, llama.cpp, SGLang, TGI)

Dengan `--metrics-url http://host:8000/metrics` (atau `--metrics-url auto`, yang memakai host API), alat ini mengambil sampel endpoint Prometheus server selama tiap tahap dan melaporkan:

* request yang **berjalan** dan **antre**,
* **pemakaian KV-cache** dalam persen,
* **preemption** (vLLM).

Dengan begitu terlihat *mengapa* latensi naik, misalnya antrean membesar begitu KV-cache mencapai 100%. Untuk llama.cpp, jalankan `llama-server` dengan opsi `--metrics`.

---

## Laporan: CSV, JSON, HTML, Compare

Setiap pengujian menulis tiga file ke `./hasil/` (ubah dengan `--out`):

| File | Isi |
| :--- | :--- |
| `*-requests.csv` | Satu baris per request: `stage, load, user, turn, started_s, finished_s, status, error_detail, ttft_s, ttfa_s, e2e_s, queue_wait_s, input_tokens, output_tokens, reasoning_tokens, token_source, tok_per_s, tpot_ms, itl_p50_ms, itl_p95_ms, itl_max_ms, prompt_chars` |
| `*-summary.json` | Parameter uji, target SLA, persentil per tahap, status akhir, linimasa soak, analisis drift, dan metrik server. Siap diimpor ke Grafana, Datadog, atau ELK. |
| `*-report.html` | Satu halaman mandiri berisi kartu ringkasan, kesimpulan, grafik (TTFT terhadap beban, kecepatan, throughput vs goodput, linimasa soak, antrean server, KV-cache), dan tabel lengkap. Bisa dibuka offline, mode terang dan gelap. |

Pengujian yang dihentikan disimpan dengan akhiran `-partial`.

```bash
# Bandingkan sebelum/sesudah per level beban (mis. setelah upgrade vLLM atau ganti kuantisasi)
python llmload.py compare hasil/ramp-20261101-100000-summary.json hasil/ramp-20261104-100000-summary.json --lang id

# Buat ulang laporan HTML (juga bisa untuk file v1 *-ringkasan.json)
python llmload.py report hasil/soak-20261104-100000-summary.json --lang id
```

Keduanya juga tersedia di menu (`c` = Bandingkan Laporan, `f` = Lihat File Hasil).

---

## Bahasa (English / Bahasa Indonesia)

Antarmuka terminal, kesimpulan, dan laporan HTML tersedia dalam bahasa Inggris dan Bahasa Indonesia.

* Interaktif: tekan `l` di menu. Pilihan bahasa juga ditanyakan saat pertama kali dijalankan.
* CLI: `--lang en` atau `--lang id` di subcommand mana pun.
* Environment: `LLMLOAD_LANG=id`.

Bahasa hanya mengubah antarmuka; prompt yang dikirim ke model tetap sama. Untuk benchmark percakapan berbahasa Indonesia (tokenisasinya berbeda dari bahasa Inggris), gunakan set bahasa Indonesia bawaan (`--prompts builtin:id`; [`prompts-id.txt`](./prompts-id.txt) berisi pertanyaan yang sama sebagai template yang bisa diedit):

```bash
llm-benchmark ramp --url ... --model ... --prompts builtin:id --lang id
```

---

## API Key & Keamanan

* **Disarankan:** isi `LLM_API_KEY` di environment. Dengan cara ini key tidak pernah ditulis ke disk.
* Di menu, kamu memilih apakah key disimpan di `llmload.conf`. Key disimpan sebagai **teks biasa** (izin file `600` di Linux/macOS).
* `llmload.conf` dan `hasil/` sudah masuk [`.gitignore`](./.gitignore); bagikan [`llmload.conf.example`](./llmload.conf.example) sebagai gantinya.
* Laporan tidak pernah berisi API key.

> [!WARNING]
> Jika file config yang berisi key pernah di-commit atau dibagikan, segera ganti (rotate) key tersebut di provider.

---

## Uji Lokal Gratis (Mock LLM Server)

Uji semua fitur, skrip, atau pipeline CI tanpa kredit API maupun GPU:

```bash
python mock_llm.py 8899                  # Windows: mock_llm.bat   Linux/macOS: ./mock_llm.sh
python mock_llm.py 8899 --reasoning 50   # simulasi model reasoning (50 token berpikir lebih dulu)
```

Mock menyediakan `http://127.0.0.1:8899/v1/chat/completions` (streaming SSE, jeda prefill, melambat saat konkurensi tinggi, HTTP 429 di atas 25 request aktif, pelaporan token) dan `http://127.0.0.1:8899/metrics` (gauge gaya vLLM). Opsi: `--throttle-after`, `--max-active`.

---

## Menjalankan Tes

```bash
python -m unittest discover -s tests -v
```

Rangkaian tes mencakup perhitungan metrik, jendela pengukuran, parsing SSE (termasuk stream reasoning), beban kerja, pembacaan laporan (v1 dan v2), pembuatan HTML, kelengkapan terjemahan, dan pengujian end-to-end terhadap mock server.

---

## Struktur Proyek

```text
├── llmload.py            # Aplikasi utama (generator beban, mesin metrik, laporan, CLI interaktif)
├── llmload_lang.py       # Terjemahan antarmuka (Bahasa Indonesia)
├── mock_llm.py           # Mock server streaming SSE lokal dengan /metrics
├── run.bat / run.ps1     # Launcher Windows (Command Prompt / PowerShell)
├── run.sh                # Launcher Linux & macOS
├── mock_llm.bat / .sh    # Launcher mock server
├── pyproject.toml        # Pengemasan: pip install . membuat perintah `llm-benchmark`
├── MANIFEST.in           # File tambahan di source distribution
├── prompts-id.txt        # Set prompt bahasa Indonesia (sama dengan `--prompts builtin:id`, template yang bisa diedit)
├── llmload.conf.example  # Contoh pengaturan (salin ke llmload.conf, atau biarkan menu membuatnya)
├── tests/                # Rangkaian tes unittest
├── hasil/                # Folder hasil (laporan CSV, JSON, HTML)
├── LICENSE               # Lisensi MIT
├── README.md             # Dokumentasi (English)
└── README.id.md          # Dokumentasi (Bahasa Indonesia)
```

---

## Upgrade dari v1

* File `llmload.conf` lama dimigrasikan otomatis (`jeda_level` → `level_pause`; key yang sudah tersimpan tetap tersimpan sampai kamu mengubahnya).
* Nama file hasil sekarang `*-requests.csv` dan `*-summary.json` dengan nama kolom bahasa Inggris. File lama `*-ringkasan.json` tetap bisa dipakai dengan `compare` dan `report`.
* Huruf menu berubah: pengaturan pindah ke huruf (`s` server, `t` SLA, `p` prompt, `a` lanjutan, `l` bahasa); pengujian ada di `1`-`6`.
* Metrik lebih ketat: request dihitung pada jendela tempat request dimulai, dan kesimpulan mencerminkan tingkat error yang sebenarnya. Nilai p95 bisa sedikit lebih tinggi (lebih jujur) dibanding v1.

---

## Kontribusi

Kontribusi sangat disambut! Baik melaporkan bug, mengusulkan skenario baru, maupun mengoptimalkan performa:
1. Fork repository ini.
2. Buat branch fitur (`git checkout -b feature/fitur-keren`).
3. Jalankan tes (`python -m unittest discover -s tests`). String UI baru perlu ditambahkan ke `llmload_lang.py`; rangkaian tes akan memeriksanya.
4. Commit perubahan dan buka **Pull Request**.

---

## Lisensi

Proyek ini memakai **Lisensi MIT** yang permisif. Lihat file [LICENSE](./LICENSE) untuk detailnya.

---

*Dibuat dengan sepenuh hati oleh **biiproject** untuk komunitas AI engineering terbuka.*
