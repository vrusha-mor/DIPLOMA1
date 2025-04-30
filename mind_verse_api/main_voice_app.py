from flask import Flask, request, jsonify, send_file
import os
import speech_recognition as sr
import google.generativeai as genai
import datetime
import warnings
import requests
from io import BytesIO
from mind_verse_api.shared.constants import GEMINI_API_KEY, ELEVEN_LABS_API_KEY
from flask_cors import CORS  # Import the CORS package
from elevenlabs_api import TextToSpeechService

warnings.simplefilter('ignore')

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

UPLOAD_FOLDER = "temp/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Predefined voice options
VOICE_DATA = {
    "jessica": "cgSgspJ2msm6clMCkdW9",
    "alice": "Xb7hH8MSUJpSbSDYk0k2",
    "roger": "CwhRBWXzGAHq8TQ4Fs17",
    "thomas": "GBv7mTt0atIp3Br8iCZE",
    "glinda": "z9fAnlkpzviPz146aGWa"
    ""
}

# Store selected voice globally
selected_voice_id = "Xb7hH8MSUJpSbSDYk0k2"  # Default to Alice

class PersonalAITherapist:
    def __init__(self, gemini_api_key, eleven_labs_api_key):
        self.gemini_api_key = gemini_api_key
        self.eleven_labs_api_key = eleven_labs_api_key
        genai.configure(api_key=self.gemini_api_key)

    def process_audio_to_text(self, audio_bytes):
        """Convert speech to text using Google Speech Recognition directly from bytes."""
        recognizer = sr.Recognizer()

        try:
            # Create AudioFile directly from bytes
            with sr.AudioFile(BytesIO(audio_bytes)) as source:
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio)
                return text
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand."
        except sr.RequestError:
            return "Speech recognition service is unavailable."
        except Exception as e:
            return f"Error processing audio: {str(e)}"

    def generate_response(self, user_input):
        """Generate AI response using Gemini AI."""
        if user_input.lower() in ["time", "today", "what is time"]:
            current_time = datetime.datetime.now().strftime("%H:%M")
            today_date = datetime.datetime.now().strftime("%B %d, %Y")
            return f"The current time is {current_time}." if "time" in user_input.lower() else f"Today's date is {today_date}."
        else:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(user_input + " in 30 words", stream=True)
            return "".join(chunk.text for chunk in response)

    def text_to_speech(self, text, voice_id=None):
        """Convert text to speech using Eleven Labs API and save as MP3."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id if voice_id is None else voice_id}"
        headers = {
            "xi-api-key": self.eleven_labs_api_key,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
        }
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            audio_data = BytesIO(response.content)
            file_path = os.path.join(UPLOAD_FOLDER, "response_audio.mp3")
            with open(file_path, "wb") as f:
                f.write(audio_data.getbuffer())
            return file_path
        else:
            print("Failed to synthesize speech:", response.text)
            return None

    def start(self, name):
        greet = f"Hello {name}! I am your Personal AI therapist. How can I assist you today?"
        return greet


# Initialize AI Therapist instance
ai_therapist = PersonalAITherapist(GEMINI_API_KEY, ELEVEN_LABS_API_KEY)

@app.route('/voice/list', methods=['GET'])
def voice_list():
    return jsonify({
        "message": "Available voices",
        "data": VOICE_DATA
    }), 200

@app.route('/voice/set', methods=['POST'])
def voice_set():
    global selected_voice_id

    data = request.json
    print(data)
    if not data or "voice_id" not in data:
        return jsonify({"message": "Missing 'voice_id' in request body"}), 400

    voice_id = data["voice_id"]
    # if voice_id not in VOICE_DATA.values():
    #     return jsonify({"message": "Invalid 'voice_id', please choose from available voices"}), 400

    selected_voice_id = voice_id  # Save the selected voice
    return jsonify({"message": "Voice set successfully", "selected_voice": voice_id}), 200


@app.route('/voice', methods=['POST'])
def receive_voice():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    if 'audio_data' not in data:
        return jsonify({"error": "No audio_data in request body"}), 400

    try:
        import base64

        # Decode the base64 audio data
        audio_bytes = base64.b64decode(data['audio_data'])

        # Process the audio bytes directly
        user_input = ai_therapist.process_audio_to_text(audio_bytes)

        if not user_input or "Sorry" in user_input or "Error" in user_input:
            return jsonify({"error": "Speech recognition failed: " + user_input}), 400

        response_text = ai_therapist.generate_response(user_input)
        response_audio_path = ai_therapist.text_to_speech(response_text)

        if response_audio_path:
            return send_file(response_audio_path, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "Failed to generate voice response"}), 500

    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500


@app.route('/start', methods=['POST'])
def start():
    # take name from firebase database and pass to start method

    # Generate AI response
    response_text = ai_therapist.start("Omkar")

    # Convert AI response to speech
    response_audio_path = ai_therapist.text_to_speech(response_text)

    if response_audio_path:
        return send_file(response_audio_path, mimetype="audio/mpeg")
    else:
        return jsonify({"error": "Failed to generate voice response"}), 500

# ----------------------------------------------------------------------------------------------------------------------
# TEXT CHAT WITH VOICE CLONE ------------
# ----------------------------------------------------------------------------------------------------------------------

from elevenlabs_api import TextToSpeechService

@app.route('/voice/clone', methods=['POST'])
def voice_clone():
    if 'file' not in request.files:
        return jsonify({"message": "No file provided"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "Empty filename"}), 400

    try:
        # Save the file temporarily in memory
        file_path = f"temp_{file.filename}"
        file.save(file_path)

        # Clone the voice using the TTS service
        tts = TextToSpeechService()
        voice_id = tts.clone_voice("Aryan Voice Clone", file_path)

        # Clean up the temporary file
        os.remove(file_path)

        return jsonify({
            "voiceId": voice_id,
            "message": "Voice Clone Successfully"
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error cloning voice: {str(e)}"}), 500


@app.route('/voice/chat', methods=['POST'])
def voice_chat():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    if 'text' not in data:
        return jsonify({"error": "No text in request body"}), 400

    try:
        # Process the audio bytes directly
        user_input = data["text"]

        if not user_input or "Sorry" in user_input or "Error" in user_input:
            return jsonify({"error": "Speech recognition failed: " + user_input}), 400

        response_text = ai_therapist.generate_response(user_input)

        if response_text:
            response_text = response_text.replace("/","")
            response_text = response_text.replace("*", "")
            response_text = response_text.replace('"', "")
            response_text = response_text.replace('\n', "")
            tts = TextToSpeechService()
            audio_bytes = tts.generate_audio(response_text, data["voice_id"])
            import base64
            mp3_base64_str = base64.b64encode(audio_bytes.getvalue()).decode('utf-8')

            return jsonify({"status":1,"text":response_text, "voice": mp3_base64_str}), 200
        else:
            return jsonify({"error": "Failed to generate voice response"}), 500

    except Exception as e:
        return jsonify({"status":0, "error": f"Processing error: {str(e)}"}), 500


@app.route('/voice/chat/start', methods=['POST'])
def voice_chat_start():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    if 'voice_id' not in data:
        return jsonify({"error": "No Voice ID in request body"}), 400
    try:
        # Process the audio bytes directly
        user_input = "Say hello greet me and say hows your mental health ?"

        if not user_input or "Sorry" in user_input or "Error" in user_input:
            return jsonify({"error": "Speech recognition failed: " + user_input}), 400

        response_text = ai_therapist.generate_response(user_input)

        if response_text:
            response_text = response_text.replace("/","")
            response_text = response_text.replace("*", "")
            response_text = response_text.replace('"', "")
            response_text = response_text.replace('\n', "")
            tts = TextToSpeechService()
            audio_bytes = tts.generate_audio(response_text, data["voice_id"])
            import base64
            mp3_base64_str = base64.b64encode(audio_bytes.getvalue()).decode('utf-8')

            return jsonify({"status":1,"text":response_text, "voice": mp3_base64_str}), 200
        else:
            return jsonify({"error": "Failed to generate voice response"}), 500

    except Exception as e:
        return jsonify({"status":0, "error": f"Processing error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

# from flask import Flask, request, jsonify, send_file
# import os
# import speech_recognition as sr
# import google.generativeai as genai
# import datetime
# import warnings
# import requests
# from io import BytesIO
# from pydub import AudioSegment  # Ensure this is installed: pip install pydub
# from shared.constants import GEMINI_API_KEY, ELEVEN_LABS_API_KEY
# from flask_cors import CORS  # Import the CORS package
#
# warnings.simplefilter('ignore')
#
# app = Flask(__name__)
# CORS(app)  # Enable CORS for all routes
#
# UPLOAD_FOLDER = "temp/"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#
# # Predefined voice options
# VOICE_DATA = {
#     "jessica": "cgSgspJ2msm6clMCkdW9",
#     "alice": "Xb7hH8MSUJpSbSDYk0k2",
#     "roger": "CwhRBWXzGAHq8TQ4Fs17",
#     "thomas": "GBv7mTt0atIp3Br8iCZE",
#     "glinda": "z9fAnlkpzviPz146aGWa"
# }
#
# # Store selected voice globally
# selected_voice_id = "Xb7hH8MSUJpSbSDYk0k2"  # Default to Alice
#
#
# class PersonalAITherapist:
#     def __init__(self, gemini_api_key, eleven_labs_api_key):
#         self.gemini_api_key = gemini_api_key
#         self.eleven_labs_api_key = eleven_labs_api_key
#
#         if not self.gemini_api_key:
#             print("⚠ ERROR: Gemini API Key is missing!")
#
#         genai.configure(api_key=self.gemini_api_key)
#
#     def process_audio_to_text(self, file_path):
#         """Convert speech to text using Google Speech Recognition."""
#         recognizer = sr.Recognizer()
#
#         print(f"🔍 Processing file: {file_path}")
#
#         if not os.path.exists(file_path):
#             print(f"❌ ERROR: File does not exist: {file_path}")
#             return "Error: File not found."
#
#         # Check file size
#         file_size = os.path.getsize(file_path)
#         print(f"📏 File Size: {file_size} bytes")
#
#         # Check if file is too small to contain speech
#         if file_size < 1000:  # Less than ~1KB is likely silence or corrupt
#             print("⚠ ERROR: Audio file is too small to contain valid speech.")
#             return "Error: Audio file is too short or empty. Please try again."
#
#         # Log audio properties
#         try:
#             audio = AudioSegment.from_file(file_path)
#             print(
#                 f"🎵 Audio Details: Duration={len(audio) / 1000:.2f}s, Channels={audio.channels}, Sample Rate={audio.frame_rate}")
#
#             # Ensure correct format
#             if audio.channels != 1 or audio.frame_rate not in [16000, 44100]:
#                 print("⚠ WARNING: Audio is not in the expected format (Mono, 16-bit PCM).")
#         except Exception as e:
#             print(f"⚠ ERROR reading audio properties: {e}")
#
#         with sr.AudioFile(file_path) as source:
#             audio_data = recognizer.record(source)
#
#         try:
#             text = recognizer.recognize_google(audio_data)
#             print(f"🎤 Recognized Speech: {text}")  # Debugging output
#             return text
#         except sr.UnknownValueError:
#             print("⚠ Speech recognition could not understand the audio.")
#             return "Sorry, I couldn't understand the audio. Please speak clearly."
#         except sr.RequestError as e:
#             print(f"⚠ Speech recognition request failed: {e}")
#             return "Speech recognition service is unavailable."
#
#     def generate_response(self, user_input):
#         """Generate AI response using Gemini AI."""
#         print(f"🤖 User Input: {user_input}")  # Debugging output
#
#         if user_input.lower() in ["time", "today", "what is time"]:
#             current_time = datetime.datetime.now().strftime("%H:%M")
#             today_date = datetime.datetime.now().strftime("%B %d, %Y")
#             return f"The current time is {current_time}." if "time" in user_input.lower() else f"Today's date is {today_date}."
#
#         try:
#             model = genai.GenerativeModel('gemini-2.0-flash')
#             response = model.generate_content(user_input, stream=True)
#             response_text = "".join(chunk.text for chunk in response)
#
#             if not response_text.strip():
#                 print("⚠ Gemini returned an empty response.")
#                 return "I'm sorry, I didn't understand that. Can you rephrase?"
#
#             print(f"💬 Gemini Response: {response_text}")  # Debugging output
#             return response_text
#         except Exception as e:
#             print(f"⚠ Error in AI response: {e}")
#             return "My apologies, I didn't understand your request. Please try again."
#
#     def text_to_speech(self, text):
#         """Convert text to speech using Eleven Labs API and save as MP3."""
#         print(f"🔊 Converting to speech: {text}")  # Debugging output
#
#         url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}"
#         headers = {
#             "xi-api-key": self.eleven_labs_api_key,
#             "Content-Type": "application/json",
#         }
#         data = {
#             "text": text,
#             "model_id": "eleven_monolingual_v1",
#             "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
#         }
#         response = requests.post(url, headers=headers, json=data)
#
#         if response.status_code == 200:
#             audio_data = BytesIO(response.content)
#             file_path = os.path.join(UPLOAD_FOLDER, "response_audio.mp3")
#             with open(file_path, "wb") as f:
#                 f.write(audio_data.getbuffer())
#             return file_path
#         else:
#             print("⚠ Failed to synthesize speech:", response.text)
#             return None
#
#
# # Initialize AI Therapist instance
# ai_therapist = PersonalAITherapist(GEMINI_API_KEY, ELEVEN_LABS_API_KEY)
#
#
# @app.route('/voice', methods=['POST'])
# def receive_voice():
#     """Handles incoming voice requests."""
#     if 'file' not in request.files:
#         return jsonify({"error": "No file uploaded"}), 400
#
#     file = request.files['file']
#     file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(file_path)
#
#     # Convert voice to text
#     user_input = ai_therapist.process_audio_to_text(file_path)
#
#     if "Error" in user_input:
#         return jsonify({"error": user_input}), 400
#
#     # Generate AI response
#     response_text = ai_therapist.generate_response(user_input)
#
#     # Convert AI response to speech
#     response_audio_path = ai_therapist.text_to_speech(response_text)
#
#     if response_audio_path:
#         return send_file(response_audio_path, mimetype="audio/mpeg")
#     else:
#         return jsonify({"error": "Failed to generate voice response"}), 500
#
#
# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0')
