"""TLS Pre-Shared Key (PSK) context configuration for MQTT connections."""

import ctypes
import logging
import ssl
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
        lib = ctypes.CDLL(ssl._ssl.__file__)  # type: ignore[attr-defined]
        if hasattr(lib, "SSL_CTX_set_psk_client_callback"):
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
