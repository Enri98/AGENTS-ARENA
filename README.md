# AI Agent Tournament

This project is a stateless trivia quiz game designed to be played by AI agents. It consists of a referee, an AI agent, and a dashboard.

## Project Structure

- `referee/`: The FastAPI server that manages the game logic.
- `agent/`: The AI agent that connects to the referee and plays the game.
- `dashboard/`: A spectator dashboard that displays the game flow.
- `schema.py`: Defines the Pydantic models for the game events.
- `requirements.txt`: The Python dependencies.
- `.env.example`: An example file for the environment variables.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- An API key for the Google Generative AI (Gemini)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd AGENTS-ARENA
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS and Linux
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables:**
    - Rename `.env.example` to `.env`.
    - Open the `.env` file and add your Gemini API key:
      ```
      GEMINI_API_KEY=YOUR_API_KEY
      ```

### Running the Application

1.  **Start the referee:**
    ```bash
    uvicorn referee.main:app --host 0.0.0.0 --port 8000
    ```

2.  **Start the dashboard (in a new terminal):**
    ```bash
    python dashboard/main.py
    ```

3.  **Start the first agent (in a new terminal):**
    ```bash
    python agent/main.py --agent-id agent1
    ```

4.  **Start the second agent (in a new terminal):**
    ```bash
    python agent/main.py --agent-id agent2
    ```

The game will start once two agents have connected. The dashboard will display the game's progress.

## How It Works

### Referee

The referee is a FastAPI application that uses WebSockets to communicate with the agents and the dashboard. It manages the game flow, sends questions to the agents, collects their answers, calculates the scores, and broadcasts the results.

### Agent

The agent is a Python script that connects to the referee via WebSocket. When it receives a question, it uses the Google Generative AI (Gemini) SDK to determine the best answer. It then sends the answer back to the referee, including its "thought" process.

### Dashboard

The dashboard is a simple Python script that connects to the referee as a spectator. It uses the `rich` library to display the game flow in a beautiful table format.

### Schema

All messages exchanged between the referee, agents, and dashboard follow a standardized schema defined in `schema.py` using Pydantic. The main data model is `GameEvent`, which has an `event_type` and a `payload`.
