import io
import os
import shutil
import subprocess
from typing import Optional

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from agents.http_clients import create_retry_session


load_dotenv()

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
SAMPLE_RATE = 16000
DEFAULT_AUDIO_PATH = "input.wav"
_HTTP_SESSION = create_retry_session()


def _get_api_key() -> str:
    api_key = os.getenv("GNANI_API_KEY")

    if not api_key:
        raise ValueError("Please set the GNANI_API_KEY environment variable.")

    return api_key


def require_api_key() -> None:
    """Raise a clear error when the speech service key is not configured."""
    _get_api_key()


def record_audio(path: str = DEFAULT_AUDIO_PATH) -> Optional[str]:
    chunks = []

    def callback(indata, _frames, _time, _status):
        chunks.append(indata.copy())

    print("Listening... speak now, press Enter when you are done.")

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback
    ):
        input()

    if not chunks:
        return None

    sf.write(path, np.concatenate(chunks), SAMPLE_RATE)
    return path


def speech_to_text(wav_path: str, locale: str) -> str:
    with open(wav_path, "rb") as audio_file:
        return speech_to_text_bytes(audio_file.read(), os.path.basename(wav_path), locale)


def speech_to_text_bytes(audio: bytes, filename: str, locale: str) -> str:
    """Transcribe an uploaded audio payload without writing it to disk."""
    response = _HTTP_SESSION.post(
        STT_URL,
        headers={"X-API-Key-ID": _get_api_key()},
        files={"audio_file": (filename, audio)},
        data={"language_code": locale, "format": "transcribe"},
        timeout=(5, 40),
    )
    response.raise_for_status()
    return response.json().get("transcript", "").strip()


def convert_audio_to_wav(audio: bytes, filename: str) -> bytes:
    """Decode browser audio formats into mono 16 kHz PCM WAV using FFmpeg."""
    executable = shutil.which("ffmpeg")
    if executable is None:
        import imageio_ffmpeg

        executable = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        result = subprocess.run(
            [
                executable,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "-acodec",
                "pcm_s16le",
                "-ac",
                "1",
                "-ar",
                str(SAMPLE_RATE),
                "pipe:1",
            ],
            input=audio,
            capture_output=True,
            check=False,
            timeout=45,
        )
    except FileNotFoundError as error:
        raise RuntimeError("FFmpeg is required to process browser audio.") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError("Audio conversion timed out.") from error

    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Unable to decode the uploaded audio: {detail[:300]}")
    if not result.stdout:
        raise ValueError("FFmpeg returned an empty WAV file.")
    return result.stdout


def synthesize_speech(text: str, locale: str) -> bytes:
    """Return a WAV audio reply from the configured speech service."""
    response = _HTTP_SESSION.post(
        TTS_URL,
        headers={
            "Content-Type": "application/json",
            "X-API-Key-ID": _get_api_key(),
        },
        json={
            "text": text,
            "voice": "Shivani",
            "model": "timbre-v3.0",
            "language": locale,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 24000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        },
        timeout=(5, 40),
    )
    response.raise_for_status()
    return response.content


def speak(text: str, locale: str) -> None:
    audio_data, sample_rate = sf.read(io.BytesIO(synthesize_speech(text, locale)))
    sd.play(audio_data, sample_rate)
    sd.wait()


def tell(text: str, locale: str, continue_on_error: bool = False) -> None:
    print("ai:", text)

    try:
        speak(text, locale)
    except Exception as error:
        if not continue_on_error:
            raise

        print(f"(Could not play the voice: {error})")


def get_user_query(locale: str, audio_path: str = DEFAULT_AUDIO_PATH) -> Optional[str]:
    """Read one user turn from typed input or microphone speech."""
    typed = input("\nPress Enter to speak (or type your answer): ").strip()

    if typed:
        return typed

    wav_path = record_audio(audio_path)

    if not wav_path:
        print("No audio recorded, try again.")
        return None

    query = speech_to_text(wav_path, locale)

    if not query:
        print("Could not understand the audio, try again.")
        return None

    return query
