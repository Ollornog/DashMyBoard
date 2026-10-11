#!/usr/bin/env bash
# Startprobe des Abbilds (PO 2026-10-11: Updates mergen selbst, wenn ein Test sie abnimmt).
#
# Ein Abbild, das baut, kann trotzdem nicht starten: ein Basis-Abbild mit anderer Python-Fassung,
# eine Abhängigkeit, die erst beim Import bricht. Der Bau allein nimmt deshalb weder das
# Basis-Abbild (Dependabot `docker`) noch app/requirements.txt (Dependabot `uv`) ab. Diese Probe
# startet das Abbild so, wie es ausgeliefert wird — als Nutzer 1000, mit leerem /data, ohne Netz
# nach draußen — und verlangt den eigenen HEALTHCHECK `healthy` und `/healthz` mit 200.
#
# Aufruf: scripts/_abbild_probe.sh [abbild]   (ohne Argument wird ./app gebaut)
set -euo pipefail

abbild="${1:-}"
name="dashmyboard-probe-$$"
gebaut=""
if [ -z "$abbild" ]; then
  abbild="dashmyboard:probe-$$"
  gebaut="$abbild"
  docker build -q -t "$abbild" ./app >/dev/null
fi

aufraeumen() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  [ -z "$gebaut" ] || docker image rm "$gebaut" >/dev/null 2>&1 || true
}
trap aufraeumen EXIT

# Nur Werte, die das Starten braucht. Kein Anbieter ist erreichbar (--network none): Die App darf
# beim Start nicht nach draußen müssen — täte sie es, wäre das ein Befund.
docker run -d --name "$name" --network none --tmpfs /data:uid=1000,gid=1000 \
  -e BASE_URL=http://localhost:8000 \
  -e OIDC_ISSUER=https://id.example.com \
  -e OIDC_CLIENT_ID=startprobe \
  -e OIDC_CLIENT_SECRET=nur-fuer-die-startprobe \
  "$abbild" >/dev/null

# Frist: start-period 10 s + Intervall 30 s → höchstens 60 s.
for _ in $(seq 1 60); do
  zustand="$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || echo weg)"
  case "$zustand" in
    healthy) break ;;
    unhealthy|weg) echo "Abbild ist $zustand"; docker logs "$name" 2>&1 | tail -30; exit 1 ;;
  esac
  [ "$(docker inspect -f '{{.State.Running}}' "$name")" = "true" ] \
    || { echo "Container läuft nicht mehr"; docker logs "$name" 2>&1 | tail -30; exit 1; }
  sleep 1
done
[ "$zustand" = "healthy" ] || { echo "nach 60 s nicht healthy ($zustand)"; docker logs "$name" 2>&1 | tail -30; exit 1; }

# /healthz von innen (ohne Netz gibt es kein Außen) — dieselbe Prüfung wie der HEALTHCHECK,
# aber hier mit sichtbarer Antwort.
antwort="$(docker exec "$name" python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3); print(r.status, r.read().decode().strip())")"
echo "/healthz: $antwort"
[ "${antwort%% *}" = "200" ] || exit 1
echo "Startprobe bestanden: $abbild ist healthy, läuft als $(docker exec "$name" id -u):$(docker exec "$name" id -g)."
