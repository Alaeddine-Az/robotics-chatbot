# Robotics Education Chatbot

An AI-powered chatbot specialized in helping high school students with robotics projects. Built with Flask and Groq's Mixtral-8x7B model.

## Features
- Interactive chat interface for robotics education
- Specialized in high school level robotics projects
- Covers Arduino, electronics, programming, and more
- Built-in rate limiting and safety features
- Token management for conversation history

## Setup
1. Clone the repository
   ```
   git clone https://github.com/Alaeddine-Az/robotics-chatbot.git
   cd robotics-chatbot
   ```

2. Create a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables
   ```
   cp .env.example .env
   # Edit .env with your GROQ_API_KEY
   ```

## Configuration

Create a `.env` file with the following variables:
```
GROQ_API_KEY=your_groq_api_key
```

## Usage

1. Start the server:
   ```
   python wsgi.py
   ```

2. Open `static/index.html` in your browser

## API Endpoints

- `GET /`: Welcome message
- `POST /chat`: Send messages to the chatbot

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Contact

<<<<<<< HEAD
Your Name - your.email@example.com
=======
Your Name - theozonecorp@gmail.com
>>>>>>> 78704aff238eb60353a2b32a12aa35d0bb14a7d9
