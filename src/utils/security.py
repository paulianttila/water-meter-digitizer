import os
from urllib.parse import unquote, urlparse


def extract_file_path_from_uri(uri: str) -> str:
    """Extract and unquote a clean local file path from a file:// URI or raw path."""
    if not uri:
        return ""
    if uri.startswith("file://"):
        parsed = urlparse(uri)
        # Handle 'file:///path/to/file' vs 'file://localhost/path/to/file'
        path = parsed.path
        if parsed.netloc and parsed.netloc != "localhost":
            path = f"//{parsed.netloc}{path}"
        return unquote(path)
    return uri


def is_safe_path(
    target_path: str,
    allowed_directories: list[str] | tuple[str, ...] | None,
) -> bool:
    """
    Verify that target_path strictly resolves within one of the allowed directories.

    Resolves symlinks, relative traversal paths (../), and path separator boundaries.
    """
    if not target_path:
        return False

    if not allowed_directories:
        # If no restrictions are configured, allow access
        return True

    try:
        clean_path = extract_file_path_from_uri(target_path)
        canonical_target = os.path.realpath(os.path.abspath(clean_path))

        for allowed_dir in allowed_directories:
            if not allowed_dir:
                continue
            canonical_allowed = os.path.realpath(os.path.abspath(allowed_dir))
            # Check if canonical_target is inside canonical_allowed
            try:
                common = os.path.commonpath([canonical_target, canonical_allowed])
                if common == canonical_allowed:
                    return True
            except ValueError:
                # Different drives on Windows, etc.
                continue

        return False
    except Exception:
        return False
