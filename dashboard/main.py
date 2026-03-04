import asyncio
import json
import websockets
from rich.console import Console
from rich.table import Table
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema import GameEvent

console = Console()

def display_event(event: GameEvent):
    """Displays a game event in a rich table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Event Type", style="dim", width=12)
    table.add_column("Details")

    if event.event_type == "STATE_UPDATE":
        scores = event.payload.get("scores", {})
        question = event.payload.get("current_question", "")
        last_action = event.payload.get("last_action", "")
        
        score_str = ", ".join([f"{agent}: {score}" for agent, score in scores.items()])
        
        table.add_row(
            "STATE_UPDATE",
            f"Question: {question}
Scores: {score_str}
Last Action: {last_action}"
        )
    elif event.event_type == "LOG":
        table.add_row("LOG", event.payload.get("message", ""))
    elif event.event_type == "QUESTION":
        question = event.payload.get("question", "")
        options = event.payload.get("options", {})
        options_str = "
".join([f"{key}: {value}" for key, value in options.items()])
        table.add_row("QUESTION", f"{question}
{options_str}")
    elif event.event_type == "RESULT":
        winner = event.payload.get("winner")
        scores = event.payload.get("scores", {})
        score_str = ", ".join([f"{agent}: {score}" for agent, score in scores.items()])
        table.add_row("RESULT", f"Winner: {winner}
Scores: {score_str}")
    else:
        table.add_row(event.event_type, json.dumps(event.payload, indent=2))
        
    console.print(table)

async def spectator():
    uri = "ws://localhost:8000/ws/spectator"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            game_event = GameEvent.model_validate_json(message)
            display_event(game_event)

if __name__ == "__main__":
    asyncio.run(spectator())
