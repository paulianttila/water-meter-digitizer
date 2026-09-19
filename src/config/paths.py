"""Configuration path manipulation and variable expansion utilities."""

import os


def format_config_path(
    path: str,
    config_dir: str = "",
    data_dir: str = "",
    digital_models_dir: str = "",
    analog_models_dir: str = "",
) -> str:
    """Relativize a path to use ${ConfigDir}, ${DataDir}, ${DigitalModelsDir}, or ${AnalogModelsDir}."""
    if not path or not isinstance(path, str):
        return path

    if path.startswith("sqlite:///"):
        sub_path = path[len("sqlite:///") :]
        rel = format_config_path(
            sub_path,
            config_dir=config_dir,
            data_dir=data_dir,
            digital_models_dir=digital_models_dir,
            analog_models_dir=analog_models_dir,
        )
        return f"sqlite:///{rel}"

    if path.startswith("file://"):
        sub_path = path[len("file://") :]
        rel = format_config_path(
            sub_path,
            config_dir=config_dir,
            data_dir=data_dir,
            digital_models_dir=digital_models_dir,
            analog_models_dir=analog_models_dir,
        )
        return f"file://{rel}"

    if path.startswith("${"):
        return path

    norm_path = os.path.normpath(path)

    candidates: list[tuple[str, str]] = []
    if digital_models_dir:
        candidates.append((os.path.normpath(digital_models_dir), "DigitalModelsDir"))
    if analog_models_dir:
        candidates.append((os.path.normpath(analog_models_dir), "AnalogModelsDir"))
    if data_dir:
        candidates.append((os.path.normpath(data_dir), "DataDir"))
    if config_dir:
        candidates.append((os.path.normpath(config_dir), "ConfigDir"))

    for base, var_name in candidates:
        if not base or base == ".":
            continue
        if norm_path == base:
            return f"${{{var_name}}}"
        if norm_path.startswith(base + os.sep) or norm_path.startswith(base + "/"):
            rel_part = norm_path[len(base) :].lstrip("/\\").replace("\\", "/")
            return f"${{{var_name}}}/{rel_part}"

    return path
