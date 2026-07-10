# Mehrstufig: die Bau-Stufe darf ins Netz und bringt Werkzeug mit, das Endabbild nicht.
# Wer im laufenden Container Code nachladen kann, hat gewonnen — also bleiben pip, git
# und Compiler draußen. Ein venv bringt sein eigenes pip mit; das wird eigens entfernt.
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Die Auth-Bibliothek ist auf einen Tag gepinnt. Kein `main`, kein `latest`:
# derselbe Build muss morgen dasselbe ergeben. Der Pin steht auch in pyproject.toml;
# ein Hygiene-Test hält beide zusammen.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir \
      "fastapi==0.115.*" "uvicorn[standard]==0.32.*" "jinja2==3.1.*" \
      "tinysesam[oidc] @ git+https://github.com/Ollornog/TinySesam.git@v0.13.1"

# Das venv trägt ein eigenes pip — im Endabbild hätte es nichts verloren.
RUN pip uninstall -y pip setuptools wheel 2>/dev/null || true \
 && find /opt/venv -name "pip*" -maxdepth 3 -exec rm -rf {} + 2>/dev/null || true


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Das System-pip des Basisabbilds fliegt ebenfalls raus.
RUN find / -maxdepth 6 -name "pip" -path "*/site-packages/*" -prune -exec rm -rf {} + 2>/dev/null || true; \
    rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12

COPY --from=build /opt/venv /opt/venv

WORKDIR /app
# links.default.json, icons_seed und bg_seed sind nur die Erstbefüllung; die aktive
# Fassung liegt unter /data (Volume) und wird vom Bearbeiten-Modus geschrieben.
COPY main.py mockups.py links.default.json ./
COPY icons_seed ./icons_seed
COPY bg_seed ./bg_seed
COPY templates ./templates
COPY static ./static

VOLUME ["/data"]
USER 1000:1000
EXPOSE 8000

# /healthz ist unauthentifiziert und antwortet über HTTP von innen — ein Check, der
# einen Redirect zurückbekäme, prüfte nichts.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).status == 200 else 1)"

# Kein --proxy-headers: die echte Client-IP ermittelt TinySesam selbst aus X-Forwarded-For,
# aber nur wenn der direkte Peer in trusted_proxies steht (sonst wäre die IP fälschbar).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
