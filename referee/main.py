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
        self.active_connections: Dict[str, WebSocket] = {}
        self.spectators: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id == "spectator":
            self.spectators.append(websocket)
        else:
            self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # Spectator disconnects are handled by removing them from the list
        # This part is simplified; a more robust solution would map websockets to client_ids
        # to handle spectator disconnections more cleanly.

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
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

class Game:
    def __init__(self, players: List[str]):
        self.players = players
        self.scores = {player: 0 for player in players}
        self.answers = {}
        self.game_task = None

    async def run(self):
        for question_data in QUESTIONS:
            question_event = GameEvent(
                event_type="QUESTION",
                payload={
                    "question": question_data["question"],
                    "options": question_data["options"],
                },
            )
            await manager.broadcast(question_event.model_dump_json())

            self.answers.clear()

            try:
                await asyncio.wait_for(self.wait_for_answers(), timeout=10.0)
            except asyncio.TimeoutError:
                log_event = GameEvent(
                    event_type="LOG",
                    payload={"message": "Did not receive answers from all agents in time."}
                )
                await manager.broadcast(log_event.model_dump_json())

            winner_of_the_round = None
            for client_id, answer in self.answers.items():
                if answer == question_data["correct_answer"]:
                    self.scores[client_id] += 1
                    winner_of_the_round = client_id

            result_payload = {
                "winner": winner_of_the_round,
                "scores": self.scores,
            }
            
            result_event = GameEvent(event_type="RESULT", payload=result_payload)
            await manager.broadcast(result_event.model_dump_json())
            
            state_update_payload = {
                "scores": self.scores,
                "current_question": question_data["question"],
                "last_action": f"Round finished. Winner: {winner_of_the_round}"
            }

            state_update_event = GameEvent(event_type="STATE_UPDATE", payload=state_update_payload)
            await manager.broadcast(state_update_event.model_dump_json())
            await asyncio.sleep(1)

        log_event = GameEvent(
            event_type="LOG",
            payload={"message": "Game over!"}
        )
        await manager.broadcast(log_event.model_dump_json())


    async def wait_for_answers(self):
        while len(self.answers) < len(self.players):
            await asyncio.sleep(0.1)

    def receive_answer(self, client_id: str, answer: str):
        if client_id in self.players:
            self.answers[client_id] = answer

game: Game = None

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    global game
    
    if client_id != "spectator" and len(manager.active_connections) == 2 and game is None:
        players = list(manager.active_connections.keys())
        game = Game(players)
        game.game_task = asyncio.create_task(game.run())
        
    try:
        while True:
            data = await websocket.receive_text()
            game_event = GameEvent.model_validate_json(data)
            if game_event.event_type == "ANSWER" and game is not None:
                game.receive_answer(client_id, game_event.payload["answer"])
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        log_event = GameEvent(
            event_type="LOG",
            payload={"message": f"Client #{client_id} left the game."}
        )
        await manager.broadcast(log_event.model_dump_json())
        
        if game is not None and client_id in game.players:
            if game.game_task is not None:
                game.game_task.cancel()
            game = None
            log_event = GameEvent(
                event_type="LOG",
                payload={"message": "Game has been stopped because a player disconnected."}
            )
            await manager.broadcast(log_event.model_dump_json())
