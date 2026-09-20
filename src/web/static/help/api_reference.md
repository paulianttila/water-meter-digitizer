### Primary REST API Endpoints

Integrate with home automation systems, scripts, and external services via REST:

| Method & Endpoint | Description | Sample Output / Payload |
|:---|:---|:---|
| `POST /readout` | Trigger immediate image acquisition and digitization pipeline | `{"value": "00442.0134", "status": "Success"}` |
| `GET /meter` | Retrieve current meter readout and neural confidence breakdown | `{"main": "00442.0134", "confidence": 98.4}` |
| `POST /poller/trigger` | Force immediate background poller cycle execution | `{"status": "triggered"}` |
| `POST /leak/reset` | Acknowledge and reset zero-flow leak state | `{"enabled": true, "state": "OK"}` |
| `GET /healthcheck` | Lightweight system diagnostics probe for Docker & orchestrators | `{"status": "healthy"}` |
| `GET /health` | Comprehensive diagnostics (memory, uptime, models, camera status) | `{"status": "healthy", "memory": {...}}` |
