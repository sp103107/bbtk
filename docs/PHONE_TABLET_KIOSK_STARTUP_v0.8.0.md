# Phone / Tablet Kiosk Startup — v0.8.0

## Correct startup

Run from the repo root:

```bash
python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080
```

The script prints local network URLs such as:

```text
http://192.168.1.25:8080
```

Open that URL on the phone/tablet while it is on the same Wi-Fi.

## Incorrect startup

Do not open:

```text
repo_scaffold/app/static/index.html
```

A raw file preview can display buttons, but the buttons cannot save punches without the backend API.

## Health check

Open:

```text
http://COMPUTER-IP:8080/api/health
```

If health does not load, punches will not record.
