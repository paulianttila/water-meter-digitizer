"""Wizard configuration manager for collecting and saving setup parameters."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import utils.image as ImageUtils
from callbacks import Callbacks
from configuration import CNNParams, Config
from data_classes import ImagePosition, MeterConfig, RefImage

if TYPE_CHECKING:
    from gui.wizard.steps import (
        AdjustStep,
        DownloadImageStep,
        DrawAnalogRoisStep,
        DrawDigitalRoisStep,
        DrawRefsStep,
        InitialRotateStep,
        MeterStep,
        ServicesStep,
    )

logger = logging.getLogger(__name__)


def resolve_model_path(
    cnn_select: Any,
    models_dir: str,
    placeholder_var: str,
) -> str:
    """Resolve model file path into placeholder variable format without whitespace."""
    if cnn_select is None:
        return ""
    val = getattr(cnn_select, "value", None)
    if not val:
        return ""
    val_str = str(val).strip()
    if val_str.startswith("${"):
        parts = [p.strip() for p in val_str.split("/")]
        return "/".join(parts)
    with contextlib.suppress(Exception):
        p = Path(val_str)
        if models_dir:
            md = Path(models_dir)
            if p.is_relative_to(md):
                rel = p.relative_to(md).as_posix()
                return f"{placeholder_var}/{rel}"
            if p.resolve().is_relative_to(md.resolve()):
                rel = p.resolve().relative_to(md.resolve()).as_posix()
                return f"{placeholder_var}/{rel}"
    parts = [part.strip() for part in val_str.split("/") if part.strip()]
    clean_rel = "/".join(parts)
    return f"{placeholder_var}/{clean_rel}" if clean_rel else ""


class WizardConfigManager:
    """Collects configuration from wizard steps, handles model paths, and saves references."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks

    def gather_config(
        self,
        download_image_step: DownloadImageStep,
        initial_rotate_step: InitialRotateStep,
        draw_refs_step: DrawRefsStep,
        adjust_step: AdjustStep,
        draw_digital_rois_step: DrawDigitalRoisStep,
        draw_analog_rois_step: DrawAnalogRoisStep,
        meters_step: MeterStep,
        services_step: ServicesStep,
    ) -> Config:
        """Gather configuration fields from step widgets into a Config model."""
        config = Config()
        orig_config = self.callbacks.get_config()
        config.log_level = orig_config.log_level
        config.config_dir = orig_config.config_dir
        config.digital_models_dir = orig_config.digital_models_dir
        config.analog_models_dir = orig_config.analog_models_dir
        config.previous_value_file = orig_config.previous_value_file

        config.image_source.url = download_image_step.url.value
        config.image_source.timeout = int(download_image_step.timeout.value or 30)
        config.image_source.min_size = int(download_image_step.minsize.value or 10000)

        config.crop.enabled = adjust_step.crop_enabled.value
        config.crop.x = int(adjust_step.crop_x.value or 0)
        config.crop.y = int(adjust_step.crop_y.value or 0)
        config.crop.w = int(adjust_step.crop_w.value or 0)
        config.crop.h = int(adjust_step.crop_h.value or 0)

        config.resize.enabled = adjust_step.resize_enabled.value
        config.resize.w = int(adjust_step.resize_w.value or 0)
        config.resize.h = int(adjust_step.resize_h.value or 0)

        config.image_processing.enabled = adjust_step.adjust_enabled.value
        config.image_processing.gamma = float(adjust_step.adjust_gamma.value or 1.0)
        config.image_processing.contrast = float(
            adjust_step.adjust_contrast.value or 1.0
        )
        config.image_processing.brightness = float(
            adjust_step.adjust_brightness.value or 1.0
        )
        config.image_processing.sharpness = float(
            adjust_step.adjust_sharpness.value or 1.0
        )
        config.image_processing.color = float(adjust_step.adjust_color.value or 1.0)
        config.image_processing.grayscale = adjust_step.grayscale_enabled.value
        config.image_processing.sharpness_mode = str(
            adjust_step.sharpness_mode.value or "standard"
        )
        config.image_processing.unsharp_radius = float(
            adjust_step.unsharp_radius.value or 1.0
        )
        config.image_processing.unsharp_amount = float(
            adjust_step.unsharp_amount.value or 1.5
        )
        config.image_processing.unsharp_threshold = int(
            adjust_step.unsharp_threshold.value or 3
        )
        config.image_processing.auto_sharpen_cut_images = (
            adjust_step.auto_sharpen_cut_images.value
        )
        config.image_processing.autocontrast.enabled = (
            adjust_step.autocontrast_enabled.value
        )
        config.image_processing.autocontrast.cutoff_low = float(
            adjust_step.autocontrast_cutoff_low.value or 2.0
        )
        config.image_processing.autocontrast.cutoff_high = float(
            adjust_step.autocontrast_cutoff_high.value or 45.0
        )
        config.image_processing.autocontrast_cut_images.enabled = (
            adjust_step.autocontrast_cut_images_enabled.value
        )
        config.image_processing.autocontrast_cut_images.cutoff_low = float(
            adjust_step.autocontrast_cut_images_cutoff_low.value or 2.0
        )
        config.image_processing.autocontrast_cut_images.cutoff_high = float(
            adjust_step.autocontrast_cut_images_cutoff_high.value or 45.0
        )

        # Glare suppression
        config.image_processing.glare_suppression.enabled = (
            adjust_step.glare_enabled.value
        )
        config.image_processing.glare_suppression.mode = str(
            adjust_step.glare_mode.value or "clahe"
        )
        config.image_processing.glare_suppression.inpaint_threshold = int(
            adjust_step.glare_inpaint_threshold.value or 230
        )
        config.image_processing.glare_suppression.inpaint_radius = int(
            adjust_step.glare_inpaint_radius.value or 3
        )
        config.image_processing.glare_suppression.clahe_clip_limit = float(
            adjust_step.glare_clahe_clip_limit.value or 2.0
        )
        config.image_processing.glare_suppression.clahe_grid_size = int(
            adjust_step.glare_clahe_grid_size.value or 8
        )
        config.image_processing.glare_suppression.apply_to_cut_images = (
            adjust_step.glare_apply_to_cut_images.value
        )

        config.alignment.rotate_angle = float(initial_rotate_step.angle or 0.0)
        config.alignment.post_rotate_angle = float(
            adjust_step.rotate_angle.value or 0.0
        )

        for roi in draw_refs_step.rois:
            config_dir = "${ConfigDir}"
            config.alignment.ref_images.append(
                RefImage(
                    name=roi.name,
                    x=roi.x,
                    y=roi.y,
                    w=roi.w,
                    h=roi.h,
                    file_name=f"{config_dir}/ref_{roi.name}_x{roi.x}_y{roi.y}.jpg",
                )
            )

        digital_model_file = resolve_model_path(
            draw_digital_rois_step.cnn_file,
            draw_digital_rois_step.digital_models_dir,
            "${DigitalModelsDir}",
        )
        digital_cut_images = [
            ImagePosition(
                name=roi.name,
                x=roi.x,
                y=roi.y,
                w=roi.w,
                h=roi.h,
            )
            for roi in draw_digital_rois_step.rois
        ]
        digital_model_val = (
            str(draw_digital_rois_step.cnn_type.value or "auto")
            if draw_digital_rois_step.cnn_type is not None
            else "auto"
        )
        detect_neg = (
            bool(draw_digital_rois_step.detect_negative_sign.value)
            if draw_digital_rois_step.detect_negative_sign is not None
            else False
        )
        config.digital_readout = CNNParams(
            enabled=len(digital_cut_images) > 0,
            model=digital_model_val,
            model_file=digital_model_file,
            detect_negative_sign=detect_neg,
            cut_images=digital_cut_images,
        )

        analog_model_file = resolve_model_path(
            draw_analog_rois_step.cnn_file,
            draw_analog_rois_step.analog_models_dir,
            "${AnalogModelsDir}",
        )
        analog_cut_images = [
            ImagePosition(
                name=roi.name,
                x=roi.x,
                y=roi.y,
                w=roi.w,
                h=roi.h,
            )
            for roi in draw_analog_rois_step.rois
        ]
        analog_model_val = (
            str(draw_analog_rois_step.cnn_type.value or "auto")
            if draw_analog_rois_step.cnn_type is not None
            else "auto"
        )
        config.analog_readout = CNNParams(
            enabled=len(analog_cut_images) > 0,
            model=analog_model_val,
            model_file=analog_model_file,
            cut_images=analog_cut_images,
        )

        meters = [
            MeterConfig(
                name=meter.name,
                format=meter.value,
                consistency_enabled=meter.consistency_enabled,
                allow_negative_rates=meter.allow_negative_rates,
                max_rate_value=meter.max_rate_value,
                min_rate_value=getattr(meter, "min_rate_value", 0.0),
                stale_threshold_hours=getattr(meter, "stale_threshold_hours", 0.0),
                use_previous_value=meter.use_previous_value,
                pre_value_from_file_max_age=meter.prevalue_from_file_max_age,
                use_extended_resolution=meter.use_extended_resolution,
                unit=meter.unit,
                detect_negative_sign=meter.detect_negative_sign,
            )
            for meter in meters_step.meter_params
        ]
        config.meter_configs = meters

        # Apply services (Poller, MQTT, History, DataDir, MinConfidence)
        services_step.apply_to_config(config)
        return config

    def save_refs(
        self,
        draw_refs_step: DrawRefsStep,
        initial_rotate_step: InitialRotateStep,
        fallback_image_b64: str = "",
    ) -> None:
        """Save reference marker images to the configuration directory."""
        config_dir = self.callbacks.get_config().config_dir
        ref_source_b64 = (
            draw_refs_step.get_image()
            or initial_rotate_step.get_image()
            or fallback_image_b64
        )
        if not ref_source_b64:
            return
        image = ImageUtils.convert_base64_str_to_image(ref_source_b64)
        for roi in draw_refs_step.rois:
            ref_img = ImageUtils.cut_image(
                image,
                ImagePosition(name=roi.name, x=roi.x, y=roi.y, w=roi.w, h=roi.h),
            )
            ImageUtils.save_image(
                ref_img, f"{config_dir}/ref_{roi.name}_x{roi.x}_y{roi.y}.jpg"
            )

    @staticmethod
    def get_refs_from_config(callbacks: Callbacks) -> str:
        """Generate SVG rect elements from configured reference images."""
        style = "stroke-width:3;stroke:red;fill-opacity:0;stroke-opacity:0.9"
        content = ""
        for ref in callbacks.get_config().alignment.ref_images:
            content += (
                f'<rect x="{ref.x}" y="{ref.y}" width="{ref.w}" '
                f'height="{ref.h}" style="{style}" />'
            )
        return content

    @staticmethod
    def get_digit_names(
        draw_digital_rois_step: DrawDigitalRoisStep,
        draw_analog_rois_step: DrawAnalogRoisStep,
    ) -> list[str]:
        """Collect digital and analog ROI names."""
        rois: list[str] = [roi.name for roi in draw_digital_rois_step.rois]
        rois.extend(roi.name for roi in draw_analog_rois_step.rois)
        return rois
