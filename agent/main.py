import asyncio
import json
import os
import websockets
import google.generativeai as genai
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema import GameEvent

# Load the Gemini API key from the .env file
from dotenv import load_dotenv
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

async def agent_player(agent_id: str):
    uri = f"ws://localhost:8000/ws/{agent_id}"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            game_event = GameEvent.model_validate_json(message)

            if game_event.event_type == "QUESTION":
                question = game_event.payload["question"]
                options = game_event.payload["options"]

                # Use the generative model to answer the question
                model = genai.GenerativeModel('gemini-pro')
                prompt = f"Question: {question}
Options: {options}

Please choose the best option (A, B, C, or D) and provide a brief thought process."
                response = await model.generate_content_async(prompt)

                # Extract the answer and thought
                # This is a simple parsing logic, a more robust solution would be needed for production
                try:
                    answer_text = response.text.strip()
                    thought = answer_text
                    # A simple way to extract the choice, assuming the model returns the letter first.
                    chosen_option = answer_text.split()[0].replace(".", "").replace(")", "").upper()
                    if chosen_option not in ["A", "B", "C", "D"]:
                        # fallback to a random choice if the model's output is not as expected
                        import random
                        chosen_option = random.choice(list(options.keys()))
                        thought = "The model's output was not in the expected format, so I'm choosing a random answer."
                except Exception as e:
                    import random
                    chosen_option = random.choice(list(options.keys()))
                    thought = f"An error occurred while parsing the model's response: {e}"

                answer_payload = {
                    "answer": chosen_option,
                    "thought": thought,
                }
                answer_event = GameEvent(event_type="ANSWER", payload=answer_payload)
                await websocket.send(answer_event.model_dump_json())

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-id", type=str, default="agent1")
    args = parser.parse_args()

    asyncio.run(agent_player(args.agent_id))
