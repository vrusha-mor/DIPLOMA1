# tts_service.py
import os
from dotenv import load_dotenv
from io import BytesIO
from elevenlabs.client import ElevenLabs
from shared.constants import ELEVEN_LABS_API_PAID_KEY, ELEVEN_LABS_API_KEY

class TextToSpeechService:
    def __init__(self):
        load_dotenv()
        self.client = ElevenLabs(api_key=ELEVEN_LABS_API_PAID_KEY)
        self.voice_id = None

    def clone_voice(self, voice_name: str, file_path: str):
        """Clone a voice from an audio file."""
        with open(file_path, "rb") as f:
            audio_data = BytesIO(f.read())

        voice = self.client.voices.add(
            name=voice_name,
            files=[audio_data]
        )
        self.voice_id = voice.voice_id
        return self.voice_id

    def generate_audio(self, text: str, voice_id=None) -> BytesIO:
        """Generate audio from text and return it as a BytesIO stream."""
        if not self.voice_id and voice_id is None:
            raise Exception("Voice not cloned yet. Call clone_voice first.")

        audio_stream = self.client.generate(
            text=text,
            voice=self.voice_id if voice_id is None else voice_id ,
            model="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        audio_bytes = BytesIO()
        for chunk in audio_stream:
            audio_bytes.write(chunk)

        audio_bytes.seek(0)
        return audio_bytes
