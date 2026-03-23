import os
import base64
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

def get_speech_config():
    import azure.cognitiveservices.speech as speechsdk
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not speech_region:
        return None

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=speech_region
    )
    speech_config.speech_synthesis_voice_name = "en-US-ChristopherNeural"
    return speech_config


def text_to_speech_base64(text: str):
    import azure.cognitiveservices.speech as speechsdk
    speech_config = get_speech_config()
    
    if not speech_config:
        print("Azure Speech disabled: missing credentials.")
        return None

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:

        audio_base64 = base64.b64encode(
            result.audio_data
        ).decode("utf-8")

        return audio_base64

    return None


def speech_to_text():

    audio_config = speechsdk.audio.AudioConfig(
        use_default_microphone=True
    )

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text

    return None