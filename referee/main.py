import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema import GameEvent

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.spectators: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id == "spectator":
            self.spectators.append(websocket)
        else:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id == "spectator":
            self.spectators.remove(websocket)
        else:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
        for spectator in self.spectators:
            await spectator.send_text(message)

manager = ConnectionManager()

# Hardcoded questions for the MVP
QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "options": {"A": "Berlin", "B": "Madrid", "C": "Paris", "D": "Rome"},
        "correct_answer": "C",
    },
    {
        "question": "What is 2 + 2?",
        "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
        "correct_answer": "B",
    },
]

scores = {}
answers = {}

async def game_runner():
    # Wait for 2 agents to connect
    while len(manager.active_connections) < 2:
        await asyncio.sleep(1)
    
    # Initialize scores
    for conn in manager.active_connections:
        scores[conn.path_params['client_id']] = 0

    for question_data in QUESTIONS:
        question_event = GameEvent(
            event_type="QUESTION",
            payload={
                "question": question_data["question"],
                "options": question_data["options"],
            },
        )
        await manager.broadcast(question_event.model_dump_json())
        
        # Reset answers for the new round
        answers.clear()
        
        # Wait for answers from both agents, with a timeout
        try:
            await asyncio.wait_for(wait_for_answers(), timeout=10.0)
        except asyncio.TimeoutError:
            log_event = GameEvent(
                event_type="LOG",
                payload={"message": "Did not receive answers from all agents in time."}
            )
            await manager.broadcast(log_event.model_dump_json())

        # Score answers and determine the winner of the round
        winner_of_the_round = None
        for client_id, answer in answers.items():
            if answer == question_data["correct_answer"]:
                scores[client_id] += 1
                winner_of_the_round = client_id

        result_payload = {
            "winner": winner_of_the_round,
            "scores": scores,
        }
        
        result_event = GameEvent(event_type="RESULT", payload=result_payload)
        await manager.broadcast(result_event.model_dump_json())
        
        state_update_payload = {
            "scores": scores,
            "current_question": question_data["question"],
            "last_action": f"Round finished. Winner: {winner_of_the_round}"
        }

        state_update_event = GameEvent(event_type="STATE_UPDATE", payload=state_update_payload)
        await manager.broadcast(state_update_event.model_dump_json())
        await asyncio.sleep(1) # Pause between questions

async def wait_for_answers():
    while len(answers) < len(manager.active_connections):
        await asyncio.sleep(0.1)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    # Start the game runner if it's not already running and we have 2 players
    if client_id != "spectator" and len(manager.active_connections) == 2 and not hasattr(app.state, "game_running"):
        app.state.game_running = True
        asyncio.create_task(game_runner())
        
    try:
        while True:
            data = await websocket.receive_text()
            game_event = GameEvent.model_validate_json(data)
            if game_event.event_type == "ANSWER":
                answers[client_id] = game_event.payload["answer"]
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        log_event = GameEvent(
            event_type="LOG",
            payload={"message": f"Client #{client_id} left the game."}
        )
        await manager.broadcast(log_event.model_dump_json())
        # Stop the game if a player disconnects
        if hasattr(app.state, "game_running") and app.state.game_running:
            app.state.game_running = False
