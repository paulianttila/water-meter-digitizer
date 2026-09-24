"""TLS Pre-Shared Key (PSK) context configuration for MQTT connections."""

import ctypes
import ctypes.util
import logging
import ssl
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PSK_CIPHERS = (
    "PSK-AES128-CBC-SHA256:PSK-AES256-CBC-SHA:PSK-3DES-EDE-CBC-SHA:PSK"
)


class _PySSLContext(ctypes.Structure):
    _fields_ = [
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.c_void_p),
        ("ctx", ctypes.c_void_p),
    ]


@lru_cache(maxsize=1)
def _get_libssl() -> ctypes.CDLL | None:
    """Dynamically locate and load the OpenSSL library exposing SSL_CTX symbols."""
    # 1. Check current process symbols (works when OpenSSL is statically linked or already loaded)
    try:
        proc_lib = ctypes.CDLL(None)
        if hasattr(proc_lib, "SSL_CTX_set_psk_client_callback"):
            return proc_lib
    except (OSError, AttributeError) as err:
        logger.debug("Process symbol lookup for libssl skipped: %s", err)

    # 2. Check Python's _ssl C-extension file if available
    _ssl_file = getattr(getattr(ssl, "_ssl", None), "__file__", None)
    if _ssl_file:
        try:
            lib = ctypes.CDLL(_ssl_file)
            if hasattr(lib, "SSL_CTX_set_psk_client_callback"):
                return lib
        except (OSError, AttributeError) as err:
            logger.debug("Python _ssl module file lookup failed: %s", err)

    # 3. Locate via system dynamic linker utility
    lib_name = ctypes.util.find_library("ssl")
    if lib_name:
        try:
            lib = ctypes.CDLL(lib_name)
            if hasattr(lib, "SSL_CTX_set_psk_client_callback"):
                return lib
        except (OSError, AttributeError) as err:
            logger.debug("System find_library('ssl') lookup failed: %s", err)

    # 4. Check common sonames / dll names across Linux, macOS, and Windows
    candidate_names = [
        "libssl.so.3",
        "libssl.so.1.1",
        "libssl.so",
        "libssl.dylib",
        "libssl.3.dylib",
        "libssl-3-x64.dll",
        "libssl-1_1-x64.dll",
        "libssl.dll",
    ]
    for name in candidate_names:
        try:
            lib = ctypes.CDLL(name)
            if hasattr(lib, "SSL_CTX_set_psk_client_callback"):
                return lib
        except (OSError, AttributeError) as err:
            logger.debug("Candidate library %s lookup failed: %s", name, err)

    return None


def configure_tls_psk(
    context: ssl.SSLContext,
    identity: str,
    psk: str,
    ciphers: str = "",
) -> ssl.SSLContext:
    """Configure an SSLContext for TLS-PSK client authentication.

    Supports both Python 3.13+ native `set_psk_client_callback` and Python 3.11/3.12
    OpenSSL C-API binding via Python's native `_ssl` module.

    Args:
        context: The `ssl.SSLContext` instance to configure.
        identity: The client PSK identity string.
        psk: The pre-shared key (hex string or UTF-8 string).
        ciphers: Optional cipher suite specification. Defaults to standard PSK ciphers.

    Returns:
        The configured `ssl.SSLContext`.
    """
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    chosen_ciphers = ciphers.strip() if ciphers.strip() else DEFAULT_PSK_CIPHERS

    try:
        context.set_ciphers(chosen_ciphers)
    except ssl.SSLError as e:
        logger.warning(
            "Failed to set PSK cipher suites '%s': %s. Falling back to default ciphers.",
            chosen_ciphers,
            e,
        )

    # Determine key bytes
    psk_clean = psk.strip()
    try:
        psk_bytes = bytes.fromhex(psk_clean)
    except ValueError:
        psk_bytes = psk_clean.encode("utf-8")

    identity_bytes = identity.encode("utf-8")

    # 1. Native Python 3.13+ API
    native_cb_setter = getattr(context, "set_psk_client_callback", None)
    if callable(native_cb_setter):

        def _native_psk_cb(hint: str | None) -> tuple[str, bytes]:
            return identity, psk_bytes

        native_cb_setter(_native_psk_cb)
        return context

    # 2. Python 3.11 / 3.12 OpenSSL C-API binding via ctypes
    try:
        lib = _get_libssl()
        if lib and hasattr(lib, "SSL_CTX_set_psk_client_callback"):
            psk_client_cb_type = ctypes.CFUNCTYPE(
                ctypes.c_uint,
                ctypes.c_void_p,  # SSL *ssl
                ctypes.c_char_p,  # const char *hint
                ctypes.c_void_p,  # char *identity
                ctypes.c_uint,  # unsigned int max_identity_len
                ctypes.c_void_p,  # unsigned char *psk
                ctypes.c_uint,  # unsigned int max_psk_len
            )

            def _c_psk_callback(
                ssl_ptr: Any,
                hint: Any,
                id_ptr: int,
                max_id_len: int,
                psk_ptr: int,
                max_psk_len: int,
            ) -> int:
                if len(identity_bytes) + 1 > max_id_len:
                    return 0
                ctypes.memmove(id_ptr, identity_bytes, len(identity_bytes))
                ctypes.memset(id_ptr + len(identity_bytes), 0, 1)

                if len(psk_bytes) > max_psk_len:
                    return 0
                ctypes.memmove(psk_ptr, psk_bytes, len(psk_bytes))
                return len(psk_bytes)

            c_cb = psk_client_cb_type(_c_psk_callback)
            pyssl = _PySSLContext.from_address(id(context))
            lib.SSL_CTX_set_psk_client_callback.argtypes = [
                ctypes.c_void_p,
                psk_client_cb_type,
            ]
            lib.SSL_CTX_set_psk_client_callback.restype = None
            lib.SSL_CTX_set_psk_client_callback(pyssl.ctx, c_cb)

            # Pin callback reference to context to prevent garbage collection
            context._psk_callback_ref = c_cb  # type: ignore[attr-defined]
            logger.info(
                "Configured TLS-PSK client callback for identity '%s'", identity
            )
            return context
    except Exception as err:
        logger.error("Failed to register OpenSSL PSK client callback: %s", err)
        raise RuntimeError(f"Unable to configure TLS-PSK callback: {err}") from err

    raise NotImplementedError(
        "TLS Pre-Shared Key (PSK) is not supported in this runtime environment."
    )
