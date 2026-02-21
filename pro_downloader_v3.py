import os
import requests
import concurrent.futures
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
try:
    from tqdm import tqdm
    USE_TQDM = True
except ImportError:
    USE_TQDM = False

# ============================================================
# KONFIGURASI - Ubah sesuai kebutuhan kamu
# ============================================================
LIST_FILE    = "urls.txt"   # File input berisi daftar URL
OUT_DIR      = "hasil_download"  # Folder output
MAX_THREADS  = 10           # Jumlah download bersamaan
TIMEOUT      = 15           # Batas waktu per request (detik)
MAX_RETRIES  = 3            # Jumlah percobaan ulang jika gagal
LOG_SUKSES   = "sukses.log"
LOG_GAGAL    = "gagal.log"
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session

def smart_filename(url: str, index: int) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace(':', '_')
    raw    = os.path.basename(parsed.path.rstrip("/"))

    # Hilangkan query string dari nama file
    raw = raw.split("?")[0]

    if not raw or raw in ("", "/"):
        return f"file_{index}"
    if raw == ".env":
        return f"{domain}.env"
    if raw == ".txt":
        return f"{domain}.txt"
    return raw

def download_file(task: dict) -> dict:
    url     = task["url"]
    index   = task["index"]
    session = task["session"]

    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
        response.raise_for_status()

        filename = smart_filename(url, index)
        filepath = os.path.join(OUT_DIR, filename)

        # Hindari overwrite: tambah suffix jika nama sudah ada
        counter = 1
        base, ext = os.path.splitext(filepath)
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}{ext}"
            counter += 1

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        size_kb = os.path.getsize(filepath) / 1024
        return {
            "status": "sukses",
            "url": url,
            "file": filepath,
            "size": f"{size_kb:.1f} KB",
        }

    except requests.exceptions.HTTPError as e:
        return {"status": "gagal", "url": url, "error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "gagal", "url": url, "error": "Tidak bisa konek ke server"}
    except requests.exceptions.Timeout:
        return {"status": "gagal", "url": url, "error": f"Timeout setelah {TIMEOUT}s"}
    except Exception as e:
        return {"status": "gagal", "url": url, "error": str(e)}

def main():
    print("=" * 60)
    print("  PRO DOWNLOADER v3 - Python Multi-Thread")
    print("=" * 60)

    if not os.path.exists(LIST_FILE):
        print(f"[ERROR] File '{LIST_FILE}' tidak ditemukan!")
        print(f"        Buat file '{LIST_FILE}' berisi daftar URL (1 per baris).")
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    # Baca dan filter URL
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    urls = [
        line.strip()
        for line in raw_lines
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        print("[ERROR] File urls.txt kosong atau semua baris dikomentari (#).")
        return

    print(f"[INFO]  Total URL     : {len(urls)}")
    print(f"[INFO]  Thread        : {MAX_THREADS}")
    print(f"[INFO]  Output folder : {OUT_DIR}")
    print(f"[INFO]  Max retry     : {MAX_RETRIES}x")
    print("-" * 60)

    session = build_session()
    tasks = [{"url": u, "index": i + 1, "session": session} for i, u in enumerate(urls)]

    sukses_list = []
    gagal_list  = []

    iterator = tasks
    if USE_TQDM:
        iterator = tqdm(
            concurrent.futures.as_completed(
                [concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS).submit(download_file, t) for t in tasks]
            ),
            total=len(tasks),
            desc="Downloading",
            unit="file",
            ncols=70,
        )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(download_file, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result["status"] == "sukses":
                print(f"  [OK] {result['url']}")
                print(f"       -> {result['file']} ({result['size']})")
                sukses_list.append(result["url"])
            else:
                print(f"  [XX] {result['url']}")
                print(f"       -> Error: {result['error']}")
                gagal_list.append(f"{result['url']} | {result['error']}")

    # Tulis log
    with open(LOG_SUKSES, "w", encoding="utf-8") as f:
        f.write("\n".join(sukses_list))

    with open(LOG_GAGAL, "w", encoding="utf-8") as f:
        f.write("\n".join(gagal_list))

    print()
    print("=" * 60)
    print(f"  SELESAI!")
    print(f"  Berhasil : {len(sukses_list)} file")
    print(f"  Gagal    : {len(gagal_list)} URL")
    print(f"  Output   : folder '{OUT_DIR}'")
    print(f"  Log OK   : {LOG_SUKSES}")
    print(f"  Log FAIL : {LOG_GAGAL}")
    print("=" * 60)


if __name__ == "__main__":
    main()