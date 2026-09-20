### MQTT Topics & Telemetry Schema

Real-time digitization telemetry is published to the configured topic prefix:

| Topic Suffix | Payload Type | Description | Example |
|:---|:---|:---|:---|
| `<prefix>/value` | Float string | Processed & validated meter reading | `00442.0134` |
| `<prefix>/raw` | String | Raw uncorrected digit readout | `00442.0134` |
| `<prefix>/status` | String | Processing status and outcome | `Success` |
| `<prefix>/leak_detected` | Boolean string | Zero-flow continuous leak flag | `false` |
| `<prefix>/rate` | Float string | Computed flow rate per time delta | `0.0025` |
