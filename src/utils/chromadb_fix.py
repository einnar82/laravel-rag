"""Fix for ChromaDB telemetry Posthog errors.

This module patches the Posthog client to prevent capture() argument errors
that occur with ChromaDB 0.4.22 and Posthog 6.x.
"""

import os
import sys
from unittest.mock import MagicMock


def disable_chromadb_telemetry():
    """Disable ChromaDB telemetry and patch Posthog to prevent errors."""
    # Set environment variables to disable telemetry
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["POSTHOG_DISABLED"] = "1"

    try:
        # Try to patch posthog before it's imported by chromadb
        import posthog

        # Create a mock capture method that accepts any arguments
        def mock_capture(*args, **kwargs):
            pass

        # Replace the capture method
        if hasattr(posthog, 'capture'):
            posthog.capture = mock_capture

        # Also patch the Posthog class if it exists
        if hasattr(posthog, 'Posthog'):
            posthog.Posthog.capture = mock_capture

    except ImportError:
        # Posthog not installed, nothing to patch
        pass
    except Exception:
        # Any other error, silently continue
        pass


# Apply the fix immediately when this module is imported
disable_chromadb_telemetry()
