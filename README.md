# Starling Bank Prometheus Exporter

A lightweight Python exporter that polls the Starling Bank API for your main account balance and Spaces (savings & spending), and exposes them as Prometheus metrics.

## Features

- `starling_main_account_balance{currency="…"}`
- `starling_space_balance{space_name="…",currency="…"}`
- Configurable polling interval and port via environment variables
- Dockerized, ready for Kubernetes or any container platform
- GitHub Actions for linting, smoke tests, and Docker image CI/CD

---

## Getting Started

### Prerequisites

- Python 3.8+ or Docker
- A [Starling Bank Personal Access Token](https://developer.starlingbank.com/) with the scopes:
  - `balance:read`
  - `space:read`
  - `account:read`
  - `account-list:read`

### Configuration

| Variable               | Default | Description                               |
|------------------------|---------|-------------------------------------------|
| `STARLING_API_TOKEN`   | —       | Your Starling PAT (required)              |
| `POLL_PERIOD_SECONDS`  | `30`    | How often to poll the API (in seconds)    |
| `EXPORTER_PORT`        | `8000`  | HTTP port for Prometheus to scrape        |

### Running Locally

```bash
export STARLING_API_TOKEN="your_token_here"
export POLL_PERIOD_SECONDS=30
export EXPORTER_PORT=8000

# Install dependencies
pip install prometheus_client requests

# Run exporter
python exporter.py
```

Then point Prometheus at `http://localhost:8000/metrics`.

### Docker

```bash
docker build -t starling-exporter:latest .
docker run -d   -e STARLING_API_TOKEN="${STARLING_API_TOKEN}"   -p 8000:8000   starling-exporter:latest
```

### GitHub Actions CI

On each push to `main`, CI will:

1. Lint your Python
2. Smoke-test the exporter
3. Build & push the Docker image to your registry

Make sure you’ve added these repo secrets:

- `REGISTRY` (e.g. `docker.io/youruser`)
- `IMAGE_NAME` (e.g. `starling-exporter`)
- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`

---

## Metrics

- **starling_main_account_balance** (gauge)
- **starling_space_balance** (gauge)

Example scrape output:

```
starling_main_account_balance{currency="GBP"}  123.45
starling_space_balance{space_name="Car",currency="GBP"} 67.89
```

---

## License

MIT © 2025 Matthew Macdonald-Wallace

