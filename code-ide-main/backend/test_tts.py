import sys
sys.path.append(".")
from app.services.speech_service import text_to_speech_base64

b64 = text_to_speech_base64("Hello, this is a test.")
if b64:
    print(f"Success. Base64 length: {len(b64)}")
else:
    print("Failed to generate audio.")
