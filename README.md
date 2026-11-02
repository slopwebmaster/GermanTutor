# 🇩🇪 Germantutor

A local, offline-first study companion for learning German with an AI tutor. 

## Features
- **EPUB Reader:** Extract text from your German books.
- **Interactive Worksheets:** Auto-generated fill-in-the-blank exercises and gender tracking.
- **10-Phase Grammar Ladder:** Progress from Accusative Definite all the way to Master Mix.
- **Daily Dashboard:** Tracks your study streak and daily goal.
- **Printable Reports:** Generate and print daily study evaluations with flashcards.

## Prerequisites
- Python 3.9 or higher
- Streamlit and Pandas

## How to Install & Run

### Windows
1. Open Command Prompt or PowerShell in this folder.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the app: `python run.py`

### Mac / Linux
1. Open Terminal in this folder.
2. Create a virtual environment: `python3 -m venv venv`
3. Activate it: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the app: `python run.py`

## How it Works
This app does not connect to the AI directly. It acts as a bridge:
1. The app generates a highly structured prompt for your AI (ChatGPT, Claude, DeepSeek).
2. You paste the AI's response back into the app.
3. The app parses the response, updates your progress, and builds an interactive worksheet.

*Note: This is an alpha release. The parser expects the AI to follow strict markdown formatting. If the AI hallucinates or breaks the format, you may need to ask it to try again.*