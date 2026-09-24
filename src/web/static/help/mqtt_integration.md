### MQTT Topics & Telemetry Schema

Real-time digitization telemetry and status are published to the configured topic prefix (default: `watermeter/`):

| Topic Suffix | Payload Type | Description | Example |
|:---|:---|:---|:---|
| `<prefix>/status` | String (`online`/`offline`) | Last Will & Testament (LWT) availability status | `online` |
| `<prefix>/<meter>/value` | Float string | Processed & validated numerical reading | `00442.0134` |
| `<prefix>/<meter>/confidence` | Float string (%) | Neural recognition confidence score | `98.4` |
| `<prefix>/<meter>/attributes` | JSON object | Home Assistant state attributes & metadata | `{"value": "00442.0134", ...}` |
| `<prefix>/<meter>/json` | JSON object | Meter-specific reading, rate, and status | `{"name": "total", "value": "00442.0134"}` |
| `<prefix>/readout/json` | JSON object | Full-system readout telemetry with all digits/meters | `{"valid": true, "meters": [...]}` |
| `<prefix>/error` | String | Last processing error message (empty if healthy) | `""` |
| `<prefix>/processing_time` | Float string (sec) | Vision pipeline execution time | `1.42` |
| `<prefix>/leak/alert` | String (`OFF`/`ON`) | Zero-flow continuous leak binary alert | `OFF` |
| `<prefix>/leak/state` | String | Zero-flow monitor status (`OK`, `LEAK_DETECTED`) | `OK` |
| `<prefix>/leak/duration` | Float string (min) | Continuous water flow duration | `0.0` |
| `<prefix>/leak/status` | JSON object | Detailed continuous leak tracking diagnostics | `{"state": "OK", "leak": false}` |

### Connection & Security Modes

The MQTT client supports production-grade security options configured under `[MQTT]`:

- **Plaintext / TLS**: Standard port 1883 or encrypted port 8883 (`TLS = True`).
- **Custom CA Certificate**: Set `TLS_CACert = /path/to/ca.crt` for self-hosted or private certificate authorities.
- **Insecure / Lab Mode**: Set `TLS_Insecure = True` to bypass verification for self-signed certificates or IP-only brokers.
- **Mutual TLS (mTLS)**: Configure client authentication with `TLS_CertFile` and `TLS_KeyFile`.
- **Pre-Shared Key (TLS-PSK)**: Lightweight symmetric encryption using `TLS_PSK_Identity` and `TLS_PSK` (or `TLS_PSK_File`).
- **Docker Secrets & 12-Factor Env**: Pass credentials securely via environment variables (e.g., `METER_MQTT__PASSWORD`, `METER_MQTT__TLS_PSK`) or Docker secret mount files (`Password_File`, `TLS_PSK_File`).
- **QoS & Protocol**: Configurable delivery guarantee (`QoS = 0 | 1 | 2`) and protocol version (`3.1.1` or `5.0`).

