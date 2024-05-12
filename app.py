# app.py
import json
import requests
from flask import Flask, render_template, request, jsonify
import yaml

app = Flask(__name__)

# Constants
INTENT_GREET_USER = "GreetUser"
STORY_GREET_USER_AND_COLLECT_INFO = "greet_user_and_collect_info"
FILE_TYPES = ['nlu', 'stories', 'domain']
RASA_API_URL = 'http://localhost:5005/webhooks/rest/webhook'

# Load file paths from a separate config file or environment variables
file_paths = {
    'nlu': 'nlu.yml',
    'stories': 'stories.yml',
    'domain': 'domain.yml'
}

def load_training_data(file_paths):
    training_data = {}

    for file_type in FILE_TYPES:
        with open(file_paths[file_type], 'r') as file:
            data = yaml.safe_load(file)
            if file_type == 'nlu':
                training_data[file_type] = data['nlu']
            elif file_type == 'stories':
                training_data[file_type] = data['stories']
            else:
                training_data[file_type] = data

    return training_data

def update_data(training_data, data, intent, entity, **kwargs):
    print("Received greeting in update_data:", kwargs.get('greeting'))
    data.append({
        "example": f"{kwargs['greeting']} {kwargs['name']}".strip(),
        "intent": intent,
        "entities": [{"start": 0, "end": len(kwargs['name']), "value": kwargs['name'], "entity": entity}]
    })

def update_nlu_data(training_data, greeting, name):
    print("Received greeting in update_nlu_data:", greeting)
    update_data(training_data, training_data['nlu'], INTENT_GREET_USER, 'user_name', name=name , greeting=greeting)

def update_stories_data(training_data, greeting, name, email, business_name, business_description):
    update_data(training_data, training_data['stories'], INTENT_GREET_USER, 'user_name', greeting=greeting, name=name, email=email, business_name=business_name, business_description=business_description)


def update_training_data(training_data_files, greeting, name, email, business_name, business_description):
    training_data = load_training_data(training_data_files)
    update_nlu_data(training_data, greeting, name)
    update_stories_data(training_data, greeting, name, email, business_name, business_description)
    return training_data

def train_rasa(training_data):
    url = 'http://localhost:5005/model/train'
    headers = {'Content-Type': 'application/json'}
    training_data_json = json.dumps(training_data)
    print(training_data_json)  # Print training data for debugging purposes
    try:
        response = requests.post(url, headers=headers, data=training_data_json)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        error_message = {'error': str(e)}
        print(error_message)  # Print error message for debugging purposes
        return jsonify(error_message), 500



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/business-info', methods=['POST'])
def business_info():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        business_name = request.form.get('businessName')
        greeting = request.form.get('greeting')
        business_description = request.form.get('businessDescription')
        

        print("Received greeting:", greeting)
        if not greeting:
            return 'Error: "greeting" field is missing or empty', 400
        if not business_description:
            return 'Error: "businessDescription" field is missing or empty', 400
        
        training_data = update_training_data(file_paths, greeting, name, email, business_name, business_description)
        response, _ = train_rasa(training_data)

        if response.status_code == 200:
            return render_template('chat.html')
        else:
            return 'Error training chatbot:', response.text

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')

    # Call your chatbot function to get a response
    rasa_response = requests.post(RASA_API_URL , json={'message': user_message})
    rasa_response_json = rasa_response.json()

    bot_response = rasa_response_json[0]['text'] if rasa_response_json else 'Sorry, I didn\'t understand that.'

    return jsonify({'message': bot_response})

if __name__ == "__main__":
    app.run(debug=True)
