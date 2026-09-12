"""CLI utility for water meter picture generation and calibration template creation."""

import argparse
import logging

from testing.meter_generator import MeterImageGenerator

logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entrypoint for meter-generator."""
    parser = argparse.ArgumentParser(
        description="Procedural Water Meter Image Generator for testing and calibration."
    )
    parser.add_argument(
        "--value",
        type=str,
        default="00452.91241",
        help="Meter reading value string (e.g. 00789.1234)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="meter_mock.jpg",
        help="Output image file path",
    )
    parser.add_argument(
        "--rotate",
        type=float,
        default=0.0,
        help="Rotation angle in degrees",
    )
    parser.add_argument(
        "--glare",
        action="store_true",
        help="Inject specular glare hotspot",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.0,
        help="Gaussian noise percentage (0-50)",
    )
    parser.add_argument(
        "--blur",
        type=float,
        default=0.0,
        help="Gaussian blur radius (0-10)",
    )
    parser.add_argument(
        "--lcd-color",
        type=str,
        default="black",
        help="LCD digit color (black, dark, amber, blue)",
    )
    parser.add_argument(
        "--lcd-bg",
        type=str,
        default="grey",
        help="LCD background color (grey, green, amber, dark, blue)",
    )
    parser.add_argument(
        "--needle-color",
        type=str,
        default="red",
        help="Analog dial needle color (red, black)",
    )
    parser.add_argument(
        "--synthetic-template",
        action="store_true",
        help="Generate synthetic template and companion config file",
    )

    args = parser.parse_args()

    generator = MeterImageGenerator()

    if args.synthetic_template:
        img, cfg = MeterImageGenerator.create_synthetic_template()
        img.save(args.output)
        ini_path = args.output.rsplit(".", 1)[0] + ".ini"
        cfg.save_to_file(ini_path)
        logger.info(
            f"Generated synthetic template to {args.output} and config to {ini_path}"
        )
        return

    img = generator.generate(
        value=args.value,
        rotate=args.rotate,
        glare=args.glare,
        noise=args.noise,
        blur=args.blur,
        lcd_color=args.lcd_color,
        lcd_bg=args.lcd_bg,
        needle_color=args.needle_color,
    )
    img.save(args.output)
    logger.info(f"Generated meter image for value {args.value} to {args.output}")


if __name__ == "__main__":
    main()
