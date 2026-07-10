FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# git wird nur zum Installieren von TinySesam (Git-Quelle) gebraucht und danach entfernt.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && pip install --no-cache-dir \
      "fastapi==0.115.*" "uvicorn[standard]==0.32.*" "jinja2==3.1.*" \
      "tinysesam[oidc] @ git+https://github.com/Ollornog/TinySesam.git@v0.11.0" \
 && apt-get purge -y git && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# links.default.json, icons_seed und bg_seed sind nur die Erstbefüllung; die aktive
# Fassung liegt unter /data (Volume) und wird vom Bearbeiten-Modus geschrieben.
COPY main.py mockups.py links.default.json ./
COPY icons_seed ./icons_seed
COPY bg_seed ./bg_seed
COPY templates ./templates
COPY static ./static

USER 1000:1000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).status == 200 else 1)"

# Kein --proxy-headers: die echte Client-IP ermittelt TinySesam selbst aus X-Forwarded-For,
# aber nur wenn der direkte Peer in trusted_proxies steht (sonst wäre die IP fälschbar).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
