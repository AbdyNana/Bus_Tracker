"""
Agent 1: The Ear (STT - Speech to Text)
Uses Google Web Speech API via SpeechRecognition (FREE).

Accepts ANY audio format (ogg, mp3, m4a, wav, flac).
Always converts to WAV via pydub before passing to Google API.
Guarantees cleanup of temp files in all cases.
"""
import os
import logging
import tempfile
import traceback
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Convert audio bytes to Russian text using Google Web Speech API.

    Steps:
      1. Write bytes to a named temp file (preserving original extension).
      2. Load with pydub (handles any format).
      3. Export as a clean WAV PCM temp file.
      4. Feed WAV to SpeechRecognition.
      5. Guaranteed cleanup of both temp files in finally block.

    Raises RuntimeError on STT API failure so caller can return HTTP 503.
    Returns empty string if speech is unintelligible (UnknownValueError).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "ogg"

    tmp_original = None
    tmp_wav = None

    try:
        # --- Step 1: Write source audio to a temp file ---
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
            f.write(audio_bytes)
            tmp_original = f.name
        logger.info(f"Saved source audio: {tmp_original} ({len(audio_bytes)} bytes, ext={ext})")

        # --- Step 2: Load with pydub (auto-detects codec) ---
        audio_segment = AudioSegment.from_file(tmp_original)
        logger.info(f"pydub loaded OK: {audio_segment.duration_seconds:.1f}s, "
                    f"{audio_segment.frame_rate}Hz, {audio_segment.channels}ch")

        # --- Step 3: Export as strict PCM WAV ---
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_wav = f.name
        audio_segment.export(tmp_wav, format="wav")
        logger.info(f"Exported WAV: {tmp_wav}")

        # --- Step 4: STT via Google Web Speech API ---
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_wav) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data, language="ru-RU")
        logger.info(f"STT result: '{text}'")
        return text

    except sr.UnknownValueError:
        logger.warning("STT: speech unintelligible (UnknownValueError)")
        return ""

    except sr.RequestError as e:
        logger.error(f"STT: Google API unavailable — {e}")
        raise RuntimeError(f"Google STT недоступен: {e}")

    except Exception as e:
        logger.error(f"STT: unexpected error — {e}\n{traceback.format_exc()}")
        raise RuntimeError(f"Ошибка обработки аудио: {e}")

    finally:
        # --- Step 5: Guaranteed cleanup ---
        for path in [tmp_original, tmp_wav]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Cleaned up temp file: {path}")
                except OSError as e:
                    logger.warning(f"Could not delete {path}: {e}")
