"""
Jarvis V2 — Screen Capture (macOS)
Takes screenshots and describes them via Claude Vision.
"""

import base64
import io
import subprocess

# Try macOS screenshot command first, fallback to PIL
def capture_screen() -> bytes:
    """Capture the entire screen, return PNG bytes."""
    try:
        # Use macOS screenshot command
        result = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-t", "png", "/tmp/jarvis_capture.png"],
            capture_output=True,
            check=True
        )
        with open("/tmp/jarvis_capture.png", "rb") as f:
            return f.read()
    except Exception:
        # Fallback to PIL (if available)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            raise RuntimeError("Screenshot capture failed. Install PIL or use macOS native.")


async def describe_screen(anthropic_client) -> str:
    """Capture screen and describe it using Claude Vision."""
    png_bytes = capture_screen()
    b64 = base64.b64encode(png_bytes).decode("utf-8")

    response = await anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                },
                {
                    "type": "text",
                    "text": "Beschreibe kurz auf Deutsch was auf diesem Bildschirm zu sehen ist. Maximal 2-3 Saetze. Nenne die wichtigsten offenen Programme und Inhalte.",
                },
            ],
        }],
    )
    return response.content[0].text
