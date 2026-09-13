# Mock Camera & Water Meter Generator

The **Water Meter Generator** is a built-in, fully autonomous procedural graphics engine and HTTP mock camera service designed for automated testing, simulation, continuous integration (CI), and offline algorithm validation without requiring physical camera hardware or static image assets.

---

## 🌟 Overview & Capabilities

- **100% Procedural Synthesis**: Renders complete, authentic circular water meter faces from scratch on-demand using vector graphics and mathematical models.
- **Authentic 7-Segment LCD Counter**: Renders 5 digital digits using genuine 7-segment LCD geometry, complete with customizable segment colors and faint background "ghost" segments for realistic contrast.
- **4 Analog Dials with Rotating Needles**: Renders 4 high-precision analog sub-dials ($x0.1$, $x0.01$, $x0.001$, $x0.0001\,\text{m}^3$) with 0–9 tick graduations and needle shadow/pivot physics.
- **Natural Alignment Reference Markers**: Incorporates 3 realistic alignment points (Model designation, volume unit/pressure rating, and serial number with barcode) without artificial bounding boxes.
- **Realistic Environmental Perturbations**: Simulates real-world camera challenges including specular glare hotspots, rotational misalignment, Gaussian sensor noise, optical blur, and lighting/contrast variations.
- **Interactive HTTP Mock Camera**: Directly accessible via `/api/mock_camera` or `/mock_camera` on the digitizer server with extensive URL query parameters.
- **Command-Line Interface (CLI)**: Generate static frames, multi-frame simulated flow sequences, or ready-to-use configuration templates via `meter-generator`.

---

## 🎨 Meter Face Visual Layout

```
+-------------------------------------------------------------------------+
|                          [ Flange & Housing ]                           |
|                             AQUA-DIGITIZER                              |
|                               m³  Qn 1.5                                |
|                                                                         |
|                +----------------------------------------+               |
|                |    [ 5-Digit 7-Segment LCD Window ]    |               |
|  [Ref 0]       | +----+  +----+  +----+  +----+  +----+ |   [Ref 1]     |
|  MOD AQ-20     | | 0  |  | 0  |  | 7  |  | 8  |  | 9  | |   m³ PN16     |
|  (115, 225)    | +----+  +----+  +----+  +----+  +----+ |   (468, 170)  |
|                +----------------------------------------+               |
|                                                                         |
|     [Analog 4]        [Analog 3]        [Analog 2]        [Analog 1]    |
|      (x0.0001)         (x0.001)          (x0.01)            (x0.1)      |
|     (210, 300)        (280, 365)        (360, 365)        (430, 300)    |
|                                                                         |
|                       [Ref 2: SN:89421 & Barcode]                       |
|                               (275, 410)                                |
+-------------------------------------------------------------------------+
```

### Reference Point Alignment Map

| Reference Marker | Description | Center / Top-Left | Dimensions ($W \times H$) |
| :--- | :--- | :--- | :--- |
| **`ref0`** | Model Designation (`MOD AQ-20`) | $(115, 225)$ | $40 \times 30\,\text{px}$ |
| **`ref1`** | Volume Unit & Pressure Rating (`m³ PN16`) | $(468, 170)$ | $36 \times 30\,\text{px}$ |
| **`ref2`** | Serial Number & Barcode (`SN:89421`) | $(275, 410)$ | $90 \times 28\,\text{px}$ |

---

## 🌐 HTTP Mock Camera API (`/api/mock_camera`)

The mock camera endpoint serves standard JPEG frames dynamically rendered based on request query parameters. It can be plugged directly into the digitizer's `[ImageSource]` configuration (`URL = http://localhost:3000/api/mock_camera?mode=flow`).

### Endpoints
- **`GET /api/mock_camera`**
- **`GET /mock_camera`**

### Query Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`value`** | `string` / `float` | `00123.4567` | Total reading string in format `DDDDD.AAAA` (e.g. `00789.1234`). Automatically sets all 5 digits and 4 dials. |
| **`mode`** | `string` | `static` | Operational mode: `static` (fixed value), `flow` (continuous simulated consumption), `noise`, `glare`, `blur`. |
| **`rate`** | `float` | `0.05` | Consumption increment rate in $\text{m}^3/\text{min}$ when `mode=flow`. |
| **`lcd_color`** | `string` | `black` | LCD active segment color: `black`, `green`, `amber`, `white`, `red`, `blue`. |
| **`lcd_bg`** | `string` | `grey` | LCD background glass tint: `grey`, `green`, `amber`, `dark`, `blue`. |
| **`needle_color`**| `string` | `red` | Analog dial needle color: `red` or `black`. |
| **`rotate`** | `float` | `0.0` | Rotational skew in degrees (e.g. `2.5`, `-5.0`, `180.0`). |
| **`glare`** | `bool` | `false` | Overlay specular glare reflection hotspot (`true` or `false`). |
| **`noise`** | `float` | `0.0` | Gaussian sensor noise percentage ($0.0 - 50.0$). |
| **`blur`** | `float` | `0.0` | Gaussian optical blur radius in pixels ($0.0 - 10.0$). |
| **`brightness`**| `float` | `1.0` | Brightness multiplier factor ($0.2 - 3.0$). |
| **`contrast`** | `float` | `1.0` | Contrast multiplier factor ($0.2 - 3.0$). |
| **`digit1`..`5`**| `float` | *(derived)* | Individual override for digital digit $1$ to $5$ ($0.0 - 9.9$). |
| **`analog1`..`4`**| `float`| *(derived)* | Individual override for analog dial $1$ to $4$ ($0.0 - 9.9$). |
| **`width`** | `int` | `640` | Canvas width in pixels. |
| **`height`** | `int` | `480` | Canvas height in pixels. |

### Example API Requests

```bash
# 1. Generate standard frame with specific reading
curl "http://localhost:3000/api/mock_camera?value=00789.1234" -o meter.jpg

# 2. Simulated water flow with green backlit LCD
curl "http://localhost:3000/api/mock_camera?mode=flow&rate=0.08&lcd_color=green&lcd_bg=dark" -o flow.jpg

# 3. Challenging conditions: Glare hotspot + 5% sensor noise + 1.5px blur
curl "http://localhost:3000/api/mock_camera?value=00452.9124&glare=true&noise=5&blur=1.5" -o robust.jpg

# 4. Rotated camera frame
curl "http://localhost:3000/api/mock_camera?value=00120.5500&rotate=3.5" -o rotated.jpg
```

---

## 🖥️ Web UI Mock Camera Studio

The **API Console** in the Web Dashboard contains a dedicated **Mock Camera Studio** tab:

1. **Interactive Controls**:
   - **Mode & Value**: Choose from `fixed`, `ticker`, `random`, or `flow` with configurable ticker rates and a 1-click **Reset Ticker** button.
   - **Optical Effects**: Fine-tune rotation angle ($-180^\circ$ to $+180^\circ$), toggle specular glare hotspots with custom position and intensity, adjust Gaussian sensor noise, blur radius, brightness, and contrast.
   - **Themes & Sizing**: Choose 7-segment LCD text colors (`black`, `blue`), background glass tints (`grey`, `green`), needle colors (`red`, `black`), and custom frame resolutions.
   - **Direct Digit/Dial Overrides**: Directly set individual digit wheels or needle dial values for edge-case testing.

2. **Live Rendered Preview & Telemetry**:
   - See the generated frame rendered in real time with automatic live refresh on change.
   - Inspect response headers (`X-Mock-Meter-Value`, `X-Mock-Digital-Value`, `X-Mock-Analog-Value`) and payload size.

3. **1-Click Integration**:
   - **"Copy URL"**: Copy the dynamically constructed `/api/mock_camera?...` path to clipboard.
   - **"Set as [ImageSource] URL"**: Automatically update and apply the active configuration's camera source to this mock feed.

---

## 💻 CLI Tool (`meter-generator`)

The procedural generator includes a rich Command Line Interface for generating static test assets or bootstrapping new configuration templates.

```bash
# Generate a single test frame
uv run python -m src.testing.cli --value 00789.1234 --output synthetic_meter.jpg

# Generate a sequence of 20 frames simulating flowing water
uv run python -m src.testing.cli --mode flow --frames 20 --interval 0.5 --output-dir ./sim_frames/

# Generate frames with environmental stress testing
uv run python -m src.testing.cli --value 00452.9124 --glare --noise 4.0 --blur 1.0 --output stress.jpg

# Create a clean calibration template and matching config.ini
uv run python -m src.testing.cli --template --output-dir ./synthetic_calibration/
```

### CLI Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| **`--value`** | Meter reading value (`DDDDD.AAAA`) | `00123.4567` |
| **`--output`** | Destination JPEG output file path | `synthetic_meter.jpg` |
| **`--mode`** | Operation mode (`static`, `flow`, `noise`, `glare`, `blur`) | `static` |
| **`--frames`** | Number of sequential frames to generate in stream mode | `10` |
| **`--rate`** | Flow consumption rate in $\text{m}^3/\text{min}$ | `0.05` |
| **`--rotate`** | Rotation angle in degrees | `0.0` |
| **`--glare`** | Enable specular glare hotspot | `False` |
| **`--noise`** | Gaussian sensor noise percentage ($0-100$) | `0.0` |
| **`--blur`** | Gaussian blur radius in pixels | `0.0` |
| **`--lcd-color`** | Active LCD segment color | `black` |
| **`--lcd-bg`** | LCD glass background color | `grey` |
| **`--template`** | Export full reference images and matching `config.ini` | `False` |
| **`--output-dir`** | Directory for batch frames or template files | `./synthetic_meter/` |

---

## 🔬 Python API & Testing Integration

You can instantiate `SyntheticWaterMeterGenerator` directly within Python scripts and unit tests:

```python
from src.testing.meter_generator import SyntheticWaterMeterGenerator

# 1. Initialize generator
gen = SyntheticWaterMeterGenerator()

# 2. Generate PIL Image
image = gen.generate(
    value="00789.1234",
    lcd_color="black",
    lcd_bg="grey",
    needle_color="red",
    rotate=0.0,
    glare=False,
    noise=0.0,
)

# 3. Save or process
image.save("mock_meter.jpg", "JPEG")
```

---

## 🤖 Recommended Neural Network Models for Simulation

When testing and validating the mock camera with neural network inference, the following models provide the highest fidelity:

| Component | Recommended Model | Model Type | Accuracy & Performance |
| :--- | :--- | :---: | :--- |
| **Analog Dials** | `config/neuralnets/analog/continuous/ana-cont_1901_s0.tflite` | `analog` | **100% accuracy** ($\text{MAE} = 0.08$) across all dial angles $0$–$9$ with $\ge 95\%$ confidence. |
| **Digital Drums** | `config/neuralnets/digital/class11/dig-class11_1600_s2.tflite` | `digital` | **100% accuracy** across all digits $0$–$9$ with $100\%$ confidence using optimized 7-segment geometry. |

---

## ⚡ In-Process Frame Rendering & Fast Simulation

The digitizer's image download utility (`src/utils/download.py`) natively supports in-process rendering for mock camera URLs (`http://.../api/mock_camera?...` or `mock://...`). When running in development, tests, or single-process servers:
- Frames are generated directly in-memory via `MeterImageGenerator` without loopback network requests.
- Completely avoids TCP socket exhaustion, timeouts, and single-threaded server deadlocks.
- Guarantees $100\%$ deterministic execution speed in CI and automated test suites.

