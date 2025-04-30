# ----------------------------------------------------------------------------------------------------------------------
# IMPORT
# ----------------------------------------------------------------------------------------------------------------------
from flask import Flask, jsonify, request
from model.voice_model import PersonalAITherapist
from shared.constants import GEMINI_API_KEY, ELEVEN_LABS_API_KEY
import os
# ----------------------------------------------------------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------------------------------------------------------

app = Flask(__name__)
UPLOAD_FOLDER = "temp/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ----------------------------------------------------------------------------------------------------------------------
# FUNCTIONS
# ----------------------------------------------------------------------------------------------------------------------

def set_voice(voice_id):
    global mind_verse
    mind_verse = PersonalAITherapist(
        voice_id=voice_id,
        gemini_api_key=GEMINI_API_KEY,
        eleven_labs_api_key=ELEVEN_LABS_API_KEY
    )

@app.route('/voice/list', methods=['GET'])
def voice_list():
    voice_data = {
        "arabella": "aEO01A4wXwd1O8GPgGlF",
        "alice": "Xb7hH8MSUJpSbSDYk0k2",
        "roger": "CwhRBWXzGAHq8TQ4Fs17",
        "thomas": "GBv7mTt0atIp3Br8iCZE",
        "glinda": "z9fAnlkpzviPz146aGWa"
    }
    return jsonify({
        "message": "Select Voice",
        "data": voice_data
    }), 200

# ----------------------------------------------------------------------------------------------------------------------

@app.route('/voice/set', methods=['POST'])
def voice_set():
    data = request.json if request.json.get("voice_id") is not None or '' else None
    if data is None:
        return jsonify({
            "message": "Something went wrong...",
        }), 400

    voice_id = data.get("voice_id")
    if voice_id is not None: set_voice(voice_id)

    return jsonify({
        "message": "Voice set successfully",
    }), 200

# ----------------------------------------------------------------------------------------------------------------------

@app.route('/voice', methods=['POST'])
def receive_voice():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Convert voice to text
    text = process_audio_to_text(file_path)

    # Generate AI response
    response_text = generate_response(text)

    # Convert AI response to speech
    response_audio_path = text_to_speech(response_text)

    # Send back the voice response as an audio file
    return send_file(response_audio_path, mimetype="audio/mpeg")


def process_audio_to_text(file_path):
    """Convert speech to text using Google STT"""
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand."
    except sr.RequestError:
        return "Speech recognition service is unavailable."

# ----------------------------------------------------------------------------------------------------------------------
# MAIN PROGRAM
# ----------------------------------------------------------------------------------------------------------------------

# Run the Flask app
if __name__ == '__main__':
    app.run(
        debug=True,
        host= "0.0.0.0"
    )