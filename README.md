# PromptToChip

A simple terminal-based Gemini/Gemma chat app with local chat memory, colored output, and selectable chat sessions.

## Features

- Chat with Google GenAI models from the terminal
- Colored terminal interface using Colorama
- Save chat history locally
- Choose existing chats with arrow keys
- Create new chat sessions
- Keeps API keys out of the repository using `.env`

## Project Files


project_test_1.py    Main chat app
gemini_test.py       Basic earlier chat test file
chat_memory.json     Local saved chat history, ignored by git
.env                 Local API key file, ignored by git
requirements.txt     Python dependencies 

Setup
Create and activate a virtual environment:

python -m venv gemini_v
.\gemini_v\Scripts\activate
Install dependencies:

pip install -r requirements.txt
Set your Gemini API key:

$env:GEMINI_API_KEY = "your_gemini_api_key_here"
Or keep it in a local .env file if you later add dotenv support.

Run
python project_test_1.py
Usage
When the app starts, use the arrow keys to select a saved chat or choose:

+ Create new chat
Press Enter to open the selected chat.

Inside the chat:

exit
or

quit
