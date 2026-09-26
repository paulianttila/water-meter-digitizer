"""Configuration models and loader for Setup Wizard meter types and presets.

Allows defining meter archetypes and specific hardware models (e.g. Axioma,
Honeywell, Kamstrup, Diehl, Itron) via an external JSON file with declarative
ROI placement, dynamic format templates, and CNN model recommendations.
"""

from __future__ import annotations

import configparser
import json
import logging
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from data_classes import ImagePosition, MeterConfig

logger = logging.getLogger(__name__)


def _make_positions_row(
    names: list[str],
    img_w: int,
    img_h: int,
    y_frac: float = 0.5,
    box_w_hint: int = 60,
    box_h_hint: int = 80,
) -> list[ImagePosition]:
    """Arranges a list of ROI names in a centered horizontal row."""
    n = len(names)
    if n == 0:
        return []

    gap = 6
    available_w = max(50, img_w - 40)
    box_w = max(24, min(box_w_hint, (available_w // n) - gap))
    box_h = max(30, min(box_h_hint, img_h // 4))
    total_w = n * box_w + (n - 1) * gap
    x0 = max(0, (img_w - total_w) // 2)
    y = max(0, int(img_h * y_frac) - (box_h // 2))

    return [
        ImagePosition(name=nm, x=x0 + i * (box_w + gap), y=y, w=box_w, h=box_h)
        for i, nm in enumerate(names)
    ]


class PresetRoiBox(BaseModel):
    """Explicit bounding box definition for a single ROI."""

    name: str
    x: int
    y: int
    w: int
    h: int
    description: str = ""


class PresetReferenceResolution(BaseModel):
    """Reference resolution against which bounding boxes were calibrated."""

    width: int = 640
    height: int = 480


class PresetAlignmentConfig(BaseModel):
    """Alignment reference points and initial rotation defaults."""

    rotate_angle: float = 0.0
    references: list[PresetRoiBox] = Field(default_factory=list)


class PresetDefaultRois(BaseModel):
    """Default ROI bounding boxes for digital and analog readouts."""

    digital: list[PresetRoiBox] = Field(default_factory=list)
    analog: list[PresetRoiBox] = Field(default_factory=list)


class PresetGlareSuppression(BaseModel):
    """Glare suppression parameters tailored for meter lens/display."""

    enabled: bool = False
    mode: str = "clahe"
    clahe_clip_limit: float = 2.0


class PresetImageAdjustments(BaseModel):
    """Recommended image preprocessing and enhancement settings."""

    enabled: bool = False
    contrast: float = 1.0
    brightness: float = 1.0
    gamma: float = 1.0
    sharpness: float = 1.0
    sharpness_mode: str = "standard"  # "standard", "unsharp_mask", "auto"
    unsharp_amount: float = 1.5
    glare_suppression: PresetGlareSuppression = Field(
        default_factory=PresetGlareSuppression
    )


class PresetLeakDetection(BaseModel):
    """Recommended zero-flow continuous leak monitor settings."""

    recommended_min_flow_threshold: float = 0.001
    warning_hours: int = 24
    alert_hours: int = 48


class PresetCropConfig(BaseModel):
    """Optional dial face crop bounding box."""

    enabled: bool = False
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


class PresetLayoutConfig(BaseModel):
    """Layout hints for placing initial ROI bounding boxes."""

    digital_y_frac: float = 0.45
    secondary_y_frac: float = 0.65
    analog_y_frac: float = 0.70
    box_width: int = 60
    box_height: int = 80
    analog_box_size: int = 70


class PresetCNNConfig(BaseModel):
    """CNN neural network recommendations for digital and analog readouts."""

    digital_category: str = "class100"
    digital_preferred_model: str | None = None
    digital_cnn_type: str = "auto"
    analog_category: str | None = None
    analog_preferred_model: str | None = None
    analog_cnn_type: str = "auto"
    recommendation_reason: str = ""


class PresetMeterConfig(BaseModel):
    """Declarative definition for a virtual meter generated from a preset."""

    name: str
    format_template: str = "{digits}.{decimals}"
    unit: str = "{unit}"
    consistency_enabled: bool = True
    use_previous_value: bool = True
    max_rate_value: float = 0.2
    use_extended_resolution: bool | Literal["auto"] = "auto"
    detect_negative_sign: bool = False


class MeterTypePreset(BaseModel):
    """Hardware meter model or archetype preset configuration."""

    id: str
    category: str = "generic"
    brand: str = ""
    model: str = ""
    label: str
    description: str
    icon: str = "water_drop"
    meter_technology: str = "generic"

    default_int_digits: int = 5
    default_dec_digits: int = 0
    default_analog_count: int = 0
    default_unit: str = "m³"

    has_secondary_group: bool = False
    default_flow_int_digits: int = 3
    default_flow_dec_digits: int = 2

    reference_resolution: PresetReferenceResolution = Field(
        default_factory=PresetReferenceResolution
    )
    image: str | None = None
    template_file_path: Path | None = None
    alignment: PresetAlignmentConfig = Field(default_factory=PresetAlignmentConfig)
    default_rois: PresetDefaultRois = Field(default_factory=PresetDefaultRois)
    image_adjustments: PresetImageAdjustments = Field(
        default_factory=PresetImageAdjustments
    )
    leak_detection: PresetLeakDetection = Field(default_factory=PresetLeakDetection)
    crop: PresetCropConfig = Field(default_factory=PresetCropConfig)

    layout: PresetLayoutConfig = Field(default_factory=PresetLayoutConfig)
    cnn: PresetCNNConfig = Field(default_factory=PresetCNNConfig)
    meters: list[PresetMeterConfig] = Field(default_factory=list)

    @property
    def model_uri(self) -> str:
        return f"model://{self.id}"

    @property
    def has_image(self) -> bool:
        if self.id == "mock_camera":
            return True
        return self.get_image_path() is not None

    def get_image_path(self) -> Path | None:
        if self.template_file_path:
            parent = self.template_file_path.parent
            if self.image:
                p = parent / self.image
                if p.is_file():
                    return p
            for ext in (".png", ".jpg", ".jpeg"):
                p = parent / f"{self.id}{ext}"
                if p.is_file():
                    return p
        return None

    @property
    def digital_category_preference(self) -> str:
        return self.cnn.digital_category

    @property
    def digital_preferred_filename(self) -> str | None:
        return self.cnn.digital_preferred_model

    @property
    def digital_cnn_type(self) -> str:
        return self.cnn.digital_cnn_type

    @property
    def analog_category_preference(self) -> str | None:
        return self.cnn.analog_category

    @property
    def analog_preferred_filename(self) -> str | None:
        return self.cnn.analog_preferred_model

    @property
    def analog_cnn_type(self) -> str:
        return self.cnn.analog_cnn_type

    @property
    def recommendation_reason(self) -> str:
        return self.cnn.recommendation_reason

    def get_digital_roi_names(
        self,
        int_digits: int,
        dec_digits: int,
        flow_int_digits: int = 0,
        flow_dec_digits: int = 0,
    ) -> list[str]:
        if self.id == "custom":
            return []
        names = [f"digit{i + 1}" for i in range(int_digits)]
        if dec_digits > 0:
            names.extend([f"decimal{i + 1}" for i in range(dec_digits)])
        if self.has_secondary_group:
            names.extend([f"flow{i + 1}" for i in range(flow_int_digits)])
            if flow_dec_digits > 0:
                names.extend([f"flow_dec{i + 1}" for i in range(flow_dec_digits)])
        return names

    def get_analog_roi_names(self, analog_count: int) -> list[str]:
        if self.id == "custom" or self.cnn.analog_category is None or analog_count <= 0:
            return []
        return [f"analog{i + 1}" for i in range(analog_count)]

    def _scale_box(self, box: PresetRoiBox, img_w: int, img_h: int) -> ImagePosition:
        """Scales a reference-resolution ROI box proportionally to active image size."""
        ref_w = max(1, self.reference_resolution.width)
        ref_h = max(1, self.reference_resolution.height)
        scale_x = img_w / ref_w
        scale_y = img_h / ref_h

        sx = max(0, round(box.x * scale_x))
        sy = max(0, round(box.y * scale_y))
        sw = max(10, round(box.w * scale_x))
        sh = max(10, round(box.h * scale_y))

        if sx + sw > img_w:
            sw = max(10, img_w - sx)
        if sy + sh > img_h:
            sh = max(10, img_h - sy)

        return ImagePosition(name=box.name, x=sx, y=sy, w=sw, h=sh)

    def get_reference_positions(
        self, img_w: int = 640, img_h: int = 480
    ) -> list[ImagePosition]:
        """Returns scaled alignment reference marker boxes (Ref0, Ref1, Ref2)."""
        if self.id == "custom" or not self.alignment.references:
            return []
        return [self._scale_box(b, img_w, img_h) for b in self.alignment.references[:3]]

    def get_crop_box(self, img_w: int = 640, img_h: int = 480) -> ImagePosition | None:
        """Returns scaled crop box if enabled in preset."""
        if not self.crop.enabled or self.crop.w <= 0 or self.crop.h <= 0:
            return None
        box = PresetRoiBox(
            name="crop",
            x=self.crop.x,
            y=self.crop.y,
            w=self.crop.w,
            h=self.crop.h,
        )
        return self._scale_box(box, img_w, img_h)

    def get_digital_roi_positions(
        self,
        names: list[str],
        img_w: int = 640,
        img_h: int = 480,
        flow_split: int = 0,
    ) -> list[ImagePosition]:
        if not names:
            return []

        # If explicit default ROIs are defined, use them with coordinate scaling
        if self.default_rois.digital:
            pos_map = {b.name: b for b in self.default_rois.digital}

            # If meter has a secondary readout group and flow_split is set, split groups
            if self.has_secondary_group and flow_split > 0 and flow_split < len(names):
                main_names = names[:-flow_split]
                flow_names = names[-flow_split:]
                main_boxes = [
                    b
                    for b in self.default_rois.digital
                    if not b.name.startswith("flow")
                ]
                flow_boxes = [
                    b for b in self.default_rois.digital if b.name.startswith("flow")
                ]

                def _map_group(
                    grp_names: list[str],
                    grp_boxes: list[PresetRoiBox],
                    default_y_frac: float,
                ) -> list[ImagePosition]:
                    grp_res: list[ImagePosition] = []
                    grp_unmapped: list[str] = []
                    for i, nm in enumerate(grp_names):
                        if nm in pos_map:
                            grp_res.append(self._scale_box(pos_map[nm], img_w, img_h))
                        elif i < len(grp_boxes):
                            scaled = self._scale_box(grp_boxes[i], img_w, img_h)
                            grp_res.append(
                                ImagePosition(
                                    name=nm,
                                    x=scaled.x,
                                    y=scaled.y,
                                    w=scaled.w,
                                    h=scaled.h,
                                )
                            )
                        else:
                            grp_unmapped.append(nm)

                    if grp_unmapped and grp_res:
                        last_box = grp_res[-1]
                        gap = 6
                        cur_x = last_box.x + last_box.w + gap
                        for nm in grp_unmapped:
                            grp_res.append(
                                ImagePosition(
                                    name=nm,
                                    x=cur_x,
                                    y=last_box.y,
                                    w=last_box.w,
                                    h=last_box.h,
                                )
                            )
                            cur_x += last_box.w + gap
                    elif grp_unmapped and not grp_res:
                        grp_res = _make_positions_row(
                            grp_unmapped,
                            img_w,
                            img_h,
                            y_frac=default_y_frac,
                            box_w_hint=self.layout.box_width,
                            box_h_hint=self.layout.box_height,
                        )
                    return grp_res

                return _map_group(
                    main_names, main_boxes, self.layout.digital_y_frac
                ) + _map_group(flow_names, flow_boxes, self.layout.secondary_y_frac)

            result: list[ImagePosition] = []
            unmapped_names: list[str] = []

            for i, nm in enumerate(names):
                if nm in pos_map:
                    result.append(self._scale_box(pos_map[nm], img_w, img_h))
                elif i < len(self.default_rois.digital):
                    box = self.default_rois.digital[i]
                    scaled = self._scale_box(box, img_w, img_h)
                    result.append(
                        ImagePosition(
                            name=nm, x=scaled.x, y=scaled.y, w=scaled.w, h=scaled.h
                        )
                    )
                else:
                    unmapped_names.append(nm)

            # Extrapolate any extra digits requested beyond defined boxes
            if unmapped_names and result:
                last_box = result[-1]
                gap = 6
                cur_x = last_box.x + last_box.w + gap
                for nm in unmapped_names:
                    result.append(
                        ImagePosition(
                            name=nm,
                            x=cur_x,
                            y=last_box.y,
                            w=last_box.w,
                            h=last_box.h,
                        )
                    )
                    cur_x += last_box.w + gap

            return result

        # Dynamic row placement fallback
        if self.has_secondary_group and flow_split > 0 and flow_split < len(names):
            main_names = names[:-flow_split]
            flow_names = names[-flow_split:]
            return _make_positions_row(
                main_names,
                img_w,
                img_h,
                y_frac=self.layout.digital_y_frac,
                box_w_hint=self.layout.box_width,
                box_h_hint=self.layout.box_height,
            ) + _make_positions_row(
                flow_names,
                img_w,
                img_h,
                y_frac=self.layout.secondary_y_frac,
                box_w_hint=self.layout.box_width,
                box_h_hint=self.layout.box_height,
            )
        return _make_positions_row(
            names,
            img_w,
            img_h,
            y_frac=self.layout.digital_y_frac,
            box_w_hint=self.layout.box_width,
            box_h_hint=self.layout.box_height,
        )

    def get_analog_roi_positions(
        self, names: list[str], img_w: int = 640, img_h: int = 480
    ) -> list[ImagePosition]:
        if not names:
            return []

        # If explicit default ROIs are defined (e.g. 2x2 grid), use them
        if self.default_rois.analog:
            pos_map = {b.name: b for b in self.default_rois.analog}
            result: list[ImagePosition] = []
            for i, nm in enumerate(names):
                if nm in pos_map:
                    result.append(self._scale_box(pos_map[nm], img_w, img_h))
                elif i < len(self.default_rois.analog):
                    box = self.default_rois.analog[i]
                    scaled = self._scale_box(box, img_w, img_h)
                    result.append(
                        ImagePosition(
                            name=nm, x=scaled.x, y=scaled.y, w=scaled.w, h=scaled.h
                        )
                    )
            if len(result) == len(names):
                return result

        return _make_positions_row(
            names,
            img_w,
            img_h,
            y_frac=self.layout.analog_y_frac,
            box_w_hint=self.layout.analog_box_size,
            box_h_hint=self.layout.analog_box_size,
        )

    def build_meter_configs(
        self,
        digital_names: list[str],
        analog_names: list[str],
        unit: str = "m³",
    ) -> list[MeterConfig]:
        """Dynamically generates virtual MeterConfigs from declarative templates."""
        if self.id == "custom":
            return []

        # If preset specifies declarative meters, resolve template variables
        if self.meters:
            int_names = [
                n
                for n in digital_names
                if not n.startswith("decimal") and not n.startswith("flow")
            ]
            dec_names = [n for n in digital_names if n.startswith("decimal")]
            flow_int_names = [
                n
                for n in digital_names
                if n.startswith("flow") and not n.startswith("flow_dec")
            ]
            flow_dec_names = [n for n in digital_names if n.startswith("flow_dec")]

            digits_str = "".join(f"{{{n}}}" for n in int_names)
            decimals_str = "".join(f"{{{n}}}" for n in dec_names)
            analogs_str = "".join(f"{{{n}}}" for n in analog_names)
            flow_digits_str = "".join(f"{{{n}}}" for n in flow_int_names)
            flow_decimals_str = "".join(f"{{{n}}}" for n in flow_dec_names)

            result: list[MeterConfig] = []
            for pm in self.meters:
                fmt = pm.format_template

                # Resolve template tags cleanly
                fmt = fmt.replace("{digits}", digits_str)
                fmt = fmt.replace("{decimals}", decimals_str)
                fmt = fmt.replace("{analogs}", analogs_str)
                fmt = fmt.replace("{flow_digits}", flow_digits_str)
                fmt = fmt.replace("{flow_decimals}", flow_decimals_str)

                # Clean up dangling dots (e.g. if {decimals} was empty)
                while ".. " in fmt or fmt.endswith(".") or ".}" in fmt:
                    fmt = fmt.replace("..", ".")
                    if fmt.endswith("."):
                        fmt = fmt[:-1]
                if fmt.startswith("."):
                    fmt = fmt[1:]

                # Resolve unit
                m_unit = pm.unit.replace("{unit}", unit)

                # Resolve extended resolution
                if pm.use_extended_resolution == "auto":
                    ext_res = bool(analog_names)
                else:
                    ext_res = bool(pm.use_extended_resolution)

                result.append(
                    MeterConfig(
                        name=pm.name,
                        format=fmt,
                        unit=m_unit,
                        consistency_enabled=pm.consistency_enabled,
                        use_previous_value=pm.use_previous_value,
                        max_rate_value=pm.max_rate_value,
                        use_extended_resolution=ext_res,
                        detect_negative_sign=pm.detect_negative_sign,
                    )
                )
            return result

        return []


class MeterPresetsFile(BaseModel):
    """Root model for meter_types.json."""

    version: int = 1
    presets: list[MeterTypePreset] = Field(default_factory=list)


DEFAULT_BUILTIN_PRESETS: list[MeterTypePreset] = [
    MeterTypePreset(
        id="generic_lcd_cumulative",
        category="generic",
        brand="Generic",
        model="LCD Cumulative",
        label="Generic: LCD - Cumulative",
        description="Digital 7-segment LCD display showing a single cumulative total reading.",
        icon="pin",
        meter_technology="digital_lcd",
        default_int_digits=5,
        default_dec_digits=3,
        default_analog_count=0,
        default_unit="m³",
        layout=PresetLayoutConfig(digital_y_frac=0.45, box_width=60, box_height=80),
        cnn=PresetCNNConfig(
            digital_category="class11",
            digital_preferred_model="dig-class11_1600_s2_q.tflite",
            digital_cnn_type="auto",
            recommendation_reason="class11 discrete models are optimized for 7-segment LCD digits (0-9).",
        ),
        meters=[
            PresetMeterConfig(
                name="total",
                format_template="{digits}.{decimals}",
                unit="{unit}",
                consistency_enabled=True,
                use_previous_value=True,
                max_rate_value=0.2,
            )
        ],
    ),
    MeterTypePreset(
        id="generic_lcd_flow",
        category="generic",
        brand="Generic",
        model="LCD Total + Flow",
        label="Generic: LCD - Total + Flow",
        description="Digital LCD showing cumulative total and instantaneous flow rate registers.",
        icon="speed",
        meter_technology="digital_lcd",
        default_int_digits=5,
        default_dec_digits=3,
        default_analog_count=0,
        has_secondary_group=True,
        default_flow_int_digits=3,
        default_flow_dec_digits=2,
        default_unit="m³",
        layout=PresetLayoutConfig(
            digital_y_frac=0.35, secondary_y_frac=0.65, box_width=55, box_height=75
        ),
        cnn=PresetCNNConfig(
            digital_category="class11",
            digital_preferred_model="dig-class11_1600_s2_q.tflite",
            digital_cnn_type="auto",
            recommendation_reason="class11 discrete models with negative sign detection for reverse flow.",
        ),
        meters=[
            PresetMeterConfig(
                name="total",
                format_template="{digits}.{decimals}",
                unit="{unit}",
                consistency_enabled=True,
                use_previous_value=True,
                max_rate_value=0.2,
            ),
            PresetMeterConfig(
                name="flow",
                format_template="{flow_digits}.{flow_decimals}",
                unit="{unit}/h",
                consistency_enabled=False,
                use_previous_value=False,
                detect_negative_sign=True,
            ),
        ],
    ),
    MeterTypePreset(
        id="generic_mechanical_classic",
        category="generic",
        brand="Generic",
        model="Mechanical 5+4",
        label="Generic: Mechanical (5 Drums + 4 Dials)",
        description="5 rolling odometer drums with 4 rotating needle pointer dials.",
        icon="tune",
        meter_technology="mechanical_dial",
        default_int_digits=5,
        default_dec_digits=0,
        default_analog_count=4,
        default_unit="m³",
        layout=PresetLayoutConfig(
            digital_y_frac=0.40,
            analog_y_frac=0.70,
            box_width=55,
            box_height=75,
            analog_box_size=70,
        ),
        cnn=PresetCNNConfig(
            digital_category="class100",
            digital_preferred_model="dig-class100_0168_s2_q.tflite",
            digital_cnn_type="auto",
            analog_category="continuous",
            analog_preferred_model="ana-cont_1209_s2.tflite",
            analog_cnn_type="auto",
            recommendation_reason="class100 reads rolling counter drums; continuous pointer network reads needle dials.",
        ),
        meters=[
            PresetMeterConfig(
                name="total",
                format_template="{digits}.{analogs}",
                unit="{unit}",
                use_extended_resolution=True,
                consistency_enabled=True,
                use_previous_value=True,
                max_rate_value=0.2,
            )
        ],
    ),
    MeterTypePreset(
        id="generic_mechanical_drums",
        category="generic",
        brand="Generic",
        model="Mechanical Drums Only",
        label="Generic: Mechanical (Drums Only)",
        description="Mechanical meter with roller drums only (no analog dials).",
        icon="counter_5",
        meter_technology="mechanical_drum",
        default_int_digits=5,
        default_dec_digits=0,
        default_analog_count=0,
        default_unit="m³",
        layout=PresetLayoutConfig(digital_y_frac=0.45, box_width=60, box_height=80),
        cnn=PresetCNNConfig(
            digital_category="class100",
            digital_preferred_model="dig-class100_0168_s2_q.tflite",
            digital_cnn_type="auto",
            recommendation_reason="class100 accurately classifies intermediate states of rolling counter drums.",
        ),
        meters=[
            PresetMeterConfig(
                name="total",
                format_template="{digits}",
                unit="{unit}",
                consistency_enabled=True,
                use_previous_value=True,
                max_rate_value=0.2,
            )
        ],
    ),
    MeterTypePreset(
        id="custom",
        category="generic",
        brand="",
        model="",
        label="Custom (Manual)",
        description="Blank canvas for completely custom ROI placement and manual configuration.",
        icon="edit_note",
        meter_technology="custom",
        default_unit="m³",
        cnn=PresetCNNConfig(
            recommendation_reason="Leaves current CNN model selections and ROIs untouched for manual setup."
        ),
    ),
]


CATEGORY_ORDER: dict[str, int] = {
    "smart": 0,
    "european_smart": 0,
    "mechanical": 1,
    "european_mechanical": 1,
    "generic": 2,
}


def sort_meter_presets(presets: list[MeterTypePreset]) -> list[MeterTypePreset]:
    """Sorts presets deterministically: category rank, brand, label, with custom last."""

    def sort_key(p: MeterTypePreset) -> tuple[int, str, str]:
        if p.id == "custom":
            return (99, "zzz", "zzz")
        cat_rank = CATEGORY_ORDER.get(p.category, 50)
        return (cat_rank, p.brand.lower(), p.label.lower())

    return sorted(presets, key=sort_key)


def _safe_getint(
    config: configparser.ConfigParser, section: str, option: str, fallback: int = 0
) -> int:
    try:
        return config.getint(section, option, fallback=fallback)
    except Exception:
        return fallback


def _safe_getfloat(
    config: configparser.ConfigParser, section: str, option: str, fallback: float = 0.0
) -> float:
    try:
        return config.getfloat(section, option, fallback=fallback)
    except Exception:
        return fallback


def _safe_getboolean(
    config: configparser.ConfigParser,
    section: str,
    option: str,
    fallback: bool = False,
) -> bool:
    try:
        return config.getboolean(section, option, fallback=fallback)
    except Exception:
        return fallback


class SafeExtendedInterpolation(configparser.ExtendedInterpolation):
    """ExtendedInterpolation that preserves raw values on missing/invalid keys instead of raising."""

    def before_get(  # type: ignore[override]
        self,
        parser: Any,
        section: str,
        option: str,
        value: str,
        defaults: Any,
    ) -> str:
        try:
            return super().before_get(parser, section, option, value, defaults)
        except (configparser.InterpolationError, configparser.NoOptionError, KeyError):
            return value


def _load_preset_from_ini(path: Path) -> MeterTypePreset | None:
    """Loads a single meter preset from an INI file containing a [Template] section."""
    if not path.is_file():
        return None
    try:
        config_dir = (
            os.environ.get("CONFIG_DIR")
            or (
                str(Path(os.environ["CONFIG_FILE"]).resolve().parent)
                if os.environ.get("CONFIG_FILE")
                else None
            )
            or "/config"
        )
        data_dir = os.environ.get("DATA_DIR", "/data")
        defaults = {
            "ConfigDir": config_dir,
            "DataDir": data_dir,
            "DigitalModelsDir": f"{config_dir}/neuralnets/digital",
            "AnalogModelsDir": f"{config_dir}/neuralnets/analog",
        }
        cp = configparser.ConfigParser(
            defaults=defaults,
            interpolation=SafeExtendedInterpolation(),
            allow_no_value=True,
            inline_comment_prefixes=("#", ";"),
        )
        cp.read_string(path.read_text(encoding="utf-8"))
        if not cp.has_section("Template"):
            return None

        preset_id = cp.get("Template", "Id", fallback=path.stem).strip()
        category = cp.get("Template", "Category", fallback="generic").strip()
        brand = cp.get("Template", "Brand", fallback="").strip()
        model = cp.get("Template", "Model", fallback="").strip()
        label = cp.get("Template", "Label", fallback=preset_id).strip()
        description = cp.get("Template", "Description", fallback="").strip()
        icon = cp.get("Template", "Icon", fallback="water_drop").strip()
        meter_technology = cp.get(
            "Template", "MeterTechnology", fallback="generic"
        ).strip()
        default_int_digits = _safe_getint(
            cp, "Template", "DefaultIntDigits", fallback=5
        )
        default_dec_digits = _safe_getint(
            cp, "Template", "DefaultDecDigits", fallback=0
        )
        default_analog_count = _safe_getint(
            cp, "Template", "DefaultAnalogCount", fallback=0
        )
        has_secondary_group = _safe_getboolean(
            cp, "Template", "HasSecondaryGroup", fallback=False
        )
        default_flow_int_digits = _safe_getint(
            cp, "Template", "DefaultFlowIntDigits", fallback=3
        )
        default_flow_dec_digits = _safe_getint(
            cp, "Template", "DefaultFlowDecDigits", fallback=2
        )
        default_unit = cp.get("Template", "DefaultUnit", fallback="m³").strip()
        ref_w = _safe_getint(cp, "Template", "ReferenceWidth", fallback=640)
        ref_h = _safe_getint(cp, "Template", "ReferenceHeight", fallback=480)
        image = cp.get("Template", "Image", fallback=None)
        if image:
            image = image.strip()

        dig_cat = cp.get(
            "Template", "DigitalCategoryPreference", fallback="class100"
        ).strip()
        dig_model = cp.get("Template", "DigitalPreferredModel", fallback=None)
        if dig_model:
            dig_model = dig_model.strip()
        dig_cnn_type = cp.get("Template", "DigitalCnnType", fallback="auto").strip()

        ana_cat = cp.get("Template", "AnalogCategoryPreference", fallback=None)
        if ana_cat and ana_cat.lower() in ("none", "null", ""):
            ana_cat = None
        elif ana_cat:
            ana_cat = ana_cat.strip()
        ana_model = cp.get("Template", "AnalogPreferredModel", fallback=None)
        if ana_model:
            ana_model = ana_model.strip()
        ana_cnn_type = cp.get("Template", "AnalogCnnType", fallback="auto").strip()
        rec_reason = cp.get("Template", "RecommendationReason", fallback="").strip()

        # Load standard config parameters from the rest of the file
        from configuration import Config

        base_cfg = Config()
        cfg = base_cfg.load_config(cp)

        # Build ROIs and alignments from standard sections
        alignment_refs = [
            PresetRoiBox(
                name=(
                    r.name.capitalize() if r.name.lower().startswith("ref") else r.name
                ),
                x=r.x,
                y=r.y,
                w=r.w,
                h=r.h,
                description=r.file_name,
            )
            for r in cfg.alignment.ref_images
        ]
        alignment = PresetAlignmentConfig(
            rotate_angle=cfg.alignment.rotate_angle,
            references=alignment_refs,
        )

        digital_rois = [
            PresetRoiBox(name=r.name, x=r.x, y=r.y, w=r.w, h=r.h)
            for r in cfg.digital_readout.cut_images
        ]
        analog_rois = [
            PresetRoiBox(name=r.name, x=r.x, y=r.y, w=r.w, h=r.h)
            for r in cfg.analog_readout.cut_images
        ]
        default_rois = PresetDefaultRois(digital=digital_rois, analog=analog_rois)

        image_adjustments = PresetImageAdjustments(
            enabled=cfg.image_processing.enabled,
            contrast=cfg.image_processing.contrast,
            brightness=cfg.image_processing.brightness,
            gamma=cfg.image_processing.gamma,
            sharpness=cfg.image_processing.sharpness,
            sharpness_mode=cfg.image_processing.sharpness_mode,
            unsharp_amount=cfg.image_processing.unsharp_amount,
            glare_suppression=PresetGlareSuppression(
                enabled=cfg.image_processing.glare_suppression.enabled,
                mode=cfg.image_processing.glare_suppression.mode,
                clahe_clip_limit=cfg.image_processing.glare_suppression.clahe_clip_limit,
            ),
        )

        leak_thresh = _safe_getfloat(
            cp,
            "Template",
            "RecommendedMinFlowThreshold",
            fallback=_safe_getfloat(
                cp,
                "ZeroFlowMonitor",
                "FlowThreshold",
                fallback=cfg.zero_flow_monitor.flow_threshold,
            ),
        )
        warning_hrs = _safe_getint(
            cp,
            "Template",
            "WarningHours",
            fallback=(
                int(cfg.zero_flow_monitor.continuous_flow_hours)
                if cfg.zero_flow_monitor.continuous_flow_hours > 0
                else 24
            ),
        )
        alert_hrs = _safe_getint(cp, "Template", "AlertHours", fallback=48)
        leak_detection = PresetLeakDetection(
            recommended_min_flow_threshold=leak_thresh,
            warning_hours=warning_hrs,
            alert_hours=alert_hrs,
        )

        crop = PresetCropConfig(
            enabled=cfg.crop.enabled,
            x=cfg.crop.x,
            y=cfg.crop.y,
            w=cfg.crop.w,
            h=cfg.crop.h,
        )

        meters = []
        for m in cfg.meter_configs:
            meters.append(
                PresetMeterConfig(
                    name=m.name,
                    format_template=m.format,
                    unit=m.unit or "{unit}",
                    consistency_enabled=m.consistency_enabled,
                    use_previous_value=m.use_previous_value,
                    max_rate_value=m.max_rate_value,
                    use_extended_resolution=m.use_extended_resolution,
                    detect_negative_sign=m.detect_negative_sign,
                )
            )

        layout = PresetLayoutConfig(
            digital_y_frac=_safe_getfloat(
                cp, "Template", "DigitalYFrac", fallback=0.45
            ),
            secondary_y_frac=_safe_getfloat(
                cp, "Template", "SecondaryYFrac", fallback=0.65
            ),
            analog_y_frac=_safe_getfloat(cp, "Template", "AnalogYFrac", fallback=0.70),
            box_width=_safe_getint(cp, "Template", "BoxWidth", fallback=60),
            box_height=_safe_getint(cp, "Template", "BoxHeight", fallback=80),
            analog_box_size=_safe_getint(cp, "Template", "AnalogBoxSize", fallback=70),
        )

        if not dig_model and cfg.digital_readout.model_file:
            dig_model = Path(cfg.digital_readout.model_file).name
        if not ana_model and cfg.analog_readout.model_file:
            ana_model = Path(cfg.analog_readout.model_file).name

        cnn = PresetCNNConfig(
            digital_category=dig_cat,
            digital_preferred_model=dig_model,
            digital_cnn_type=dig_cnn_type,
            analog_category=ana_cat,
            analog_preferred_model=ana_model,
            analog_cnn_type=ana_cnn_type,
            recommendation_reason=rec_reason,
        )

        return MeterTypePreset(
            id=preset_id,
            category=category,
            brand=brand,
            model=model,
            label=label,
            description=description,
            icon=icon,
            meter_technology=meter_technology,
            default_int_digits=default_int_digits,
            default_dec_digits=default_dec_digits,
            default_analog_count=default_analog_count,
            has_secondary_group=has_secondary_group,
            default_flow_int_digits=default_flow_int_digits,
            default_flow_dec_digits=default_flow_dec_digits,
            default_unit=default_unit,
            reference_resolution=PresetReferenceResolution(width=ref_w, height=ref_h),
            image=image,
            template_file_path=path,
            alignment=alignment,
            default_rois=default_rois,
            image_adjustments=image_adjustments,
            leak_detection=leak_detection,
            crop=crop,
            layout=layout,
            cnn=cnn,
            meters=meters,
        )
    except Exception as e:
        logger.warning(
            "Failed to load meter preset from INI %s: %s (skipping file)", path, e
        )
        return None


def _load_from_dir(mdir: Path) -> list[MeterTypePreset]:
    """Scans a directory for *.ini and *.json files and loads meter presets."""
    if not mdir.is_dir():
        return []
    presets: list[MeterTypePreset] = []
    seen_ids: set[str] = set()

    # 1. Scan *.ini files first (primary template format)
    ini_files = sorted(mdir.rglob("*.ini"))
    for f in ini_files:
        if f.name.startswith(("_", ".")):
            continue
        preset = _load_preset_from_ini(f)
        if preset and preset.id not in seen_ids:
            presets.append(preset)
            seen_ids.add(preset.id)

    # 2. Scan *.json files (backward-compatibility)
    json_files = sorted(mdir.rglob("*.json"))
    for jf in json_files:
        if jf.name.startswith(("_", ".")):
            continue
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if "presets" in data and isinstance(data["presets"], list):
                    for item in data["presets"]:
                        p = MeterTypePreset.model_validate(item)
                        p.template_file_path = jf
                        if p.id not in seen_ids:
                            presets.append(p)
                            seen_ids.add(p.id)
                elif "id" in data:
                    p = MeterTypePreset.model_validate(data)
                    p.template_file_path = jf
                    if p.id not in seen_ids:
                        presets.append(p)
                        seen_ids.add(p.id)
            elif isinstance(data, list):
                for item in data:
                    p = MeterTypePreset.model_validate(item)
                    p.template_file_path = jf
                    if p.id not in seen_ids:
                        presets.append(p)
                        seen_ids.add(p.id)
        except Exception as e:
            logger.warning(
                "Failed to load meter preset from %s: %s (skipping file)",
                jf,
                e,
            )
    return presets


def _load_from_file(path: Path) -> list[MeterTypePreset]:
    """Loads meter presets from a single INI or JSON file."""
    if not path.is_file():
        return []
    if path.suffix.lower() == ".ini":
        p = _load_preset_from_ini(path)
        return [p] if p else []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            if "presets" in data and isinstance(data["presets"], list):
                result = []
                for item in data["presets"]:
                    p = MeterTypePreset.model_validate(item)
                    p.template_file_path = path
                    result.append(p)
                return result
            elif "id" in data:
                p = MeterTypePreset.model_validate(data)
                p.template_file_path = path
                return [p]
        elif isinstance(data, list):
            result = []
            for item in data:
                p = MeterTypePreset.model_validate(item)
                p.template_file_path = path
                result.append(p)
            return result
    except Exception as e:
        logger.warning(
            "Failed to load meter presets from %s: %s",
            path,
            e,
        )
    return []


_PRESETS_CACHE: dict[str, list[MeterTypePreset]] = {}


def clear_presets_cache() -> None:
    """Clears the cached meter presets in memory."""
    _PRESETS_CACHE.clear()


def reload_meter_presets(
    config_dir: str | Path | None = None,
) -> list[MeterTypePreset]:
    """Force reloads meter presets from disk and returns the updated list."""
    return load_meter_presets(config_dir=config_dir, force_reload=True)


def get_preset_by_id(
    preset_id: str,
    config_dir: str | Path | None = None,
    force_reload: bool = False,
) -> MeterTypePreset | None:
    """Finds a meter preset by its unique ID (case-insensitive)."""
    presets = load_meter_presets(config_dir=config_dir, force_reload=force_reload)
    for p in presets:
        if p.id.lower() == preset_id.lower():
            return p
    return None


def get_available_template_images(
    config_dir: str | Path | None = None,
    force_reload: bool = False,
) -> list[tuple[str, str]]:
    """Returns a list of (url, label) for all presets with available faceplate images."""
    presets = load_meter_presets(config_dir=config_dir, force_reload=force_reload)
    result: list[tuple[str, str]] = []
    for p in presets:
        if p.has_image:
            result.append((p.model_uri, f"{p.model_uri} ({p.label})"))
    return result


def load_meter_presets(
    config_dir: str | Path | None = None,
    force_reload: bool = False,
) -> list[MeterTypePreset]:
    """Loads meter presets from modular directory or configuration files.

    Order of evaluation:
    1. If not force_reload and cached, return cached presets.
    2. If config_dir is provided and exists:
       a. ${config_dir}/meter_types/ (all *.ini and *.json files)
       b. ${config_dir}/meter_types.ini or ${config_dir}/meter_types.json (single file)
       c. Fallback to DEFAULT_BUILTIN_PRESETS if explicit directory had no presets
    3. Default locations:
       a. config/meter_types/ (all *.ini and *.json files, relative or repo root)
       b. config/meter_types.ini or config/meter_types.json (single file, relative or repo root)
    4. DEFAULT_BUILTIN_PRESETS fallback
    """
    cache_key = str(config_dir) if config_dir is not None else ""
    if not force_reload and cache_key in _PRESETS_CACHE:
        return list(_PRESETS_CACHE[cache_key])

    if config_dir:
        cd_path = Path(config_dir)
        if cd_path.exists():
            presets = _load_from_dir(cd_path / "meter_types")
            if presets:
                sorted_p = sort_meter_presets(presets)
                _PRESETS_CACHE[cache_key] = sorted_p
                return list(sorted_p)
            presets = _load_from_file(cd_path / "meter_types.ini")
            if presets:
                sorted_p = sort_meter_presets(presets)
                _PRESETS_CACHE[cache_key] = sorted_p
                return list(sorted_p)
            presets = _load_from_file(cd_path / "meter_types.json")
            if presets:
                sorted_p = sort_meter_presets(presets)
                _PRESETS_CACHE[cache_key] = sorted_p
                return list(sorted_p)
            sorted_p = sort_meter_presets(DEFAULT_BUILTIN_PRESETS)
            _PRESETS_CACHE[cache_key] = sorted_p
            return list(sorted_p)

    # Default locations
    candidate_dirs = [
        Path("config") / "meter_types",
        Path(__file__).resolve().parents[2] / "config" / "meter_types",
    ]
    for default_dir in candidate_dirs:
        presets = _load_from_dir(default_dir)
        if presets:
            sorted_p = sort_meter_presets(presets)
            _PRESETS_CACHE[cache_key] = sorted_p
            return list(sorted_p)

    candidate_files = [
        Path("config") / "meter_types.ini",
        Path(__file__).resolve().parents[2] / "config" / "meter_types.ini",
        Path("config") / "meter_types.json",
        Path(__file__).resolve().parents[2] / "config" / "meter_types.json",
    ]
    for default_file in candidate_files:
        presets = _load_from_file(default_file)
        if presets:
            sorted_p = sort_meter_presets(presets)
            _PRESETS_CACHE[cache_key] = sorted_p
            return list(sorted_p)

    sorted_p = sort_meter_presets(DEFAULT_BUILTIN_PRESETS)
    _PRESETS_CACHE[cache_key] = sorted_p
    return list(sorted_p)
