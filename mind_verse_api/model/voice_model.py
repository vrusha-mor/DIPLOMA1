import requests
import speech_recognition as sr
import google.generativeai as genai
import datetime
import warnings
import pygame
from io import BytesIO
from shared.constants import GEMINI_API_KEY, ELEVEN_LABS_API_KEY
warnings.simplefilter('ignore')



class PersonalAITherapist:
    def __init__(self, gemini_api_key, eleven_labs_api_key, voice_id):
        self.gemini_api_key = gemini_api_key
        self.eleven_labs_api_key = eleven_labs_api_key
        self.voice_id = voice_id
        genai.configure(api_key=self.gemini_api_key)
        pygame.mixer.init()

    def speak_with_eleven_labs(self, text):
        """Use Eleven Labs API to synthesize speech and play directly."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.eleven_labs_api_key,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
            },
        }
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            audio_data = BytesIO(response.content)
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            print(f"==> Friday AI: {text}")
        else:
            print("Failed to synthesize speech:", response.text)

    def get_user_input(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening....")
            recognizer.pause_threshold = 1
            audio = recognizer.listen(source, 0, 5)

        try:
            query = recognizer.recognize_google(audio, language="en").lower()
            print("You said:", query)
            return query
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Request failed: {e}")
            return None

    def handle_user_intent(self, user_input):
        if user_input.lower() in ["time", "today", "what is time"]:
            current_time = datetime.datetime.now().strftime("%H:%M")
            today_date = datetime.datetime.now().strftime("%B %d, %Y")
            if "time" in user_input.lower():
                self.speak_with_eleven_labs(f"The current time is {current_time}.")
            else:
                self.speak_with_eleven_labs(f"Today's date is {today_date}.")
        elif user_input.lower() not in ["exit", "goodbye"]:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(user_input + " in 30 words", stream=True)
            response_text = "".join(chunk.text for chunk in response)
            print(f"==> Friday AI: {response_text}")
            self.speak_with_eleven_labs(response_text)
        else:
            self.speak_with_eleven_labs("Goodbye!")
            exit(0)

    def start(self):
        self.speak_with_eleven_labs(f"Hello Aaryan! I am your Personal AI therapist. How can I assist you today?")
        while True:
            user_input = self.get_user_input()
            if user_input:
                self.handle_user_intent(user_input)


if __name__ == "__main__":
    GEMINI_API_KEY = GEMINI_API_KEY
    ELEVEN_LABS_API_KEY = ELEVEN_LABS_API_KEY
    ELEVEN_LABS_VOICE_ID = "cgSgspJ2msm6clMCkdW9"

    ai_therapist = PersonalAITherapist(GEMINI_API_KEY, ELEVEN_LABS_API_KEY, ELEVEN_LABS_VOICE_ID)
    ai_therapist.start()
