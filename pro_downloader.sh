#!/usr/bin/env bash
set -e

LIST_FILE="urls.txt"
OUT_DIR="hasil_download"
THREADS=10 # Jumlah download pararel

mkdir -p "$OUT_DIR"
> sukses.log
> gagal.log

echo "🚀 Memulai download pararel ($THREADS thread)..."

# Ekspor variabel agar bisa dibaca xargs
export OUT_DIR

# Fungsi untuk memproses 1 URL
download_url() {
    url="$1"
    # Lewati baris kosong atau komentar
    [[ -z ""+"${url// }" ]] && exit 0
    [[ "$url" =~ ^# ]] && exit 0

    # Ekstrak domain dari URL menggunakan awk
domain=$(echo "$url" | awk -F/ '{print $3}')
base=$(basename "${url%%\?*}")

    # Smart Naming: kalau namanya .env, ubah jadi domain.env
    if [[ "$base" == ".env" || -z "$base" ]]; then
        base="${domain}.env"
    fi

    out_file="$OUT_DIR/$base"
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # curl secara silent (-s), follow redirect (-L), output ke file (-o)
    if curl -s -L -A "$user_agent" --max-time 15 --fail -o "$out_file" "$url"; then
        echo "✅ [SUKSES] $url -> $out_file"
        echo "$url" >> sukses.log
    else
        echo "❌ [GAGAL] $url"
        echo "$url" >> gagal.log
    fi
}
export -f download_url

# Baca file, hapus baris kosong, kirim ke xargs untuk diproses pararel
grep -v '^#' "$LIST_FILE" | grep -v '^[[:space:]]*$' | xargs -n 1 -P "$THREADS" -I {} bash -c 'download_url "{}"'

echo "🎉 Selesai! Cek folder $OUT_DIR, sukses.log, dan gagal.log."