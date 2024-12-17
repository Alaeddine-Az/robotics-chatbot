from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from groq import Groq
from dotenv import load_dotenv
from typing import List, Dict
import logging
from datetime import datetime, timedelta
import time
from collections import defaultdict
import tiktoken

# Setup logging
logging.basicConfig(
    filename='chatbot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CORS(app)

# Constants
MAX_HISTORY_TOKENS = 3000
MAX_REQUESTS_PER_MINUTE = 20
REQUEST_WINDOW = 60  # seconds

# Initialize Groq client
try:
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
except Exception as e:
    logging.error(f"Failed to initialize Groq client: {str(e)}")
    raise

# Rate limiting
request_history = defaultdict(list)

def count_tokens(text: str) -> int:
    """Count tokens in a text string"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logging.warning(f"Error counting tokens: {str(e)}")
        return len(text.split()) * 2  # Rough estimation fallback

def truncate_history(history: List[Dict], max_tokens: int) -> List[Dict]:
    """Truncate history to stay within token limit"""
    total_tokens = 0
    truncated_history = []
    
    # Reverse history to keep most recent messages
    for message in reversed(history):
        message_tokens = count_tokens(message['content'])
        if total_tokens + message_tokens <= max_tokens:
            truncated_history.insert(0, message)
            total_tokens += message_tokens
        else:
            break
    
    if len(truncated_history) < len(history):
        logging.info(f"Truncated history from {len(history)} to {len(truncated_history)} messages")
    
    return truncated_history

def check_rate_limit(ip: str) -> bool:
    """Check if request is within rate limits"""
    now = time.time()
    
    # Clean old requests
    request_history[ip] = [req_time for req_time in request_history[ip] 
                          if now - req_time < REQUEST_WINDOW]
    
    # Check if under limit
    if len(request_history[ip]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    # Add new request
    request_history[ip].append(now)
    return True

def validate_message(message: str) -> bool:
    """Validate user message"""
    if not isinstance(message, str):
        return False
    if not message.strip():
        return False
    return True

def validate_history(history: List[Dict]) -> bool:
    """Validate conversation history"""
    if not isinstance(history, list):
        return False
    
    for entry in history:
        if not isinstance(entry, dict):
            return False
        if 'role' not in entry or 'content' not in entry:
            return False
        if not isinstance(entry['role'], str) or not isinstance(entry['content'], str):
            return False
        if entry['role'] not in ['user', 'assistant', 'system']:
            return False
    
    return True

# Define the system prompt for a robotics education agent
SYSTEM_PROMPT = """You are an educational AI agent specialized in helping high school students with robotics projects. Your role is to:

1. Guide students through robotics concepts in an age-appropriate and engaging way
2. Help troubleshoot common robotics problems
3. Suggest project ideas suitable for high school level
4. Explain programming concepts related to robotics (Arduino, Python, etc.)
5. Provide safety guidelines when working with electronics and tools
6. Break down complex concepts into manageable steps
7. Encourage learning and experimentation while emphasizing safety

Key areas of expertise:
- Basic electronics and circuits
- Arduino programming and projects
- Sensor integration (IR, ultrasonic, etc.)
- Motor control and mechanics
- Basic AI and machine learning concepts
- 3D printing for robotics
- Robot design and construction
- Competition preparation (FIRST Robotics, VEX, etc.)

Always:
- Use student-friendly language
- Provide practical examples
- Include safety warnings when relevant
- Encourage best practices
- Break down complex tasks into steps
- Suggest additional resources for learning
- Be encouraging and supportive

If a project seems too advanced or unsafe, suggest appropriate alternatives."""

@app.route('/', methods=['GET'])
def home():
    return "Welcome to the Robotics Education Assistant! Send POST requests to /chat to interact."

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'GET':
        return jsonify({'message': 'Please send a POST request with your message'})
    
    try:
        # Rate limiting
        if not check_rate_limit(request.remote_addr):
            logging.warning(f"Rate limit exceeded for IP: {request.remote_addr}")
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

        # Log request
        logging.info(f"Request from IP: {request.remote_addr}")
        
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        # Validate user message
        user_message = data.get('message', '')
        if not validate_message(user_message):
            return jsonify({'error': 'Invalid or empty message'}), 400
        
        # Validate and get conversation history
        conversation_history = data.get('history', [])
        if not validate_history(conversation_history):
            return jsonify({'error': 'Invalid conversation history format'}), 400
        
        # Truncate history if needed
        conversation_history = truncate_history(conversation_history, MAX_HISTORY_TOKENS)
        
        # Prepare messages for the API
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]
        messages.extend(conversation_history)
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            start_time = time.time()
            
            # Create chat completion using Groq
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1024,
                timeout=30  # 30 seconds timeout
            )

            # Log response time
            response_time = time.time() - start_time
            logging.info(f"LLM response time: {response_time:.2f} seconds")

            # Extract and validate the response
            assistant_response = chat_completion.choices[0].message.content
            if not validate_message(assistant_response):
                raise ValueError("Invalid response from LLM")
            
            # Update conversation history
            new_history = conversation_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ]
            
            return jsonify({
                'response': assistant_response,
                'history': new_history
            })
            
        except Exception as e:
            logging.error(f"LLM Error: {str(e)}")
            error_message = "Error generating response. Please try again."
            
            if "timeout" in str(e).lower():
                error_message = "Request timed out. Please try again."
            elif "api key" in str(e).lower():
                error_message = "API authentication error. Please contact support."
            
            return jsonify({'error': error_message}), 500
    
    except Exception as e:
        logging.error(f"General Error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Error handlers
@app.errorhandler(400)
def bad_request(e):
    logging.error(f"Bad Request: {str(e)}")
    return jsonify({'error': 'Bad Request'}), 400

@app.errorhandler(429)
def too_many_requests(e):
    logging.warning(f"Too Many Requests: {str(e)}")
    return jsonify({'error': 'Too many requests. Please try again later.'}), 429

@app.errorhandler(500)
def internal_error(e):
    logging.error(f"Internal Server Error: {str(e)}")
    return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)