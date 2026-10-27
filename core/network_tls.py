"""Verified TLS with a bundled CA store for frozen Windows deployments."""
import os
import ssl
import sys
import certifi


def verified_tls_context():
    custom_file = os.environ.get("SSL_CERT_FILE")
    custom_dir = os.environ.get("SSL_CERT_DIR")
    # Supplying an actual CA bundle avoids failures in Windows' default store
    # enumeration. Hostname and certificate verification remain mandatory.
    context = ssl.create_default_context(cafile=custom_file or certifi.where(), capath=custom_dir)
    if sys.platform == "win32" and not custom_file and not custom_dir:
        try:
            context.load_default_certs()
        except OSError:
            # System roots are supplementary; the bundled public roots loaded
            # above are already available. Never fall back to CERT_NONE.
            pass
    return context
