import aiohttp
import asyncio
import websockets
import uuid
import json
import io
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

server_address = "127.0.0.1:7821"
client_id = str(uuid.uuid4())

async def queue_prompt_async(session, prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    async with session.post(f"http://{server_address}/prompt", data=data) as response:
        return await response.json()

async def get_image_async(session, filename, subfolder, folder_type):
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    async with session.get(f"http://{server_address}/view", params=params) as response:
        return await response.read()

async def get_history_async(session, prompt_id):
    async with session.get(f"http://{server_address}/history/{prompt_id}") as response:
        return await response.json()

async def get_images_async(ws, prompt, session):
    try:
        prompt_id = (await queue_prompt_async(session, prompt))['prompt_id']
        output_images = {}

        while True:
            out = await asyncio.wait_for(ws.recv(), timeout=180)
            if isinstance(out, str):
                message = json.loads(out)
                logger.debug(f"Received WebSocket message: {message}")

                if message['type'] == 'status' and 'data' in message:
                    data = message['data']
                    if 'status' in data and 'exec_info' in data['status']:
                        exec_info = data['status']['exec_info']
                        queue_remaining = exec_info.get('queue_remaining', None)

                        # Check if the queue is empty and execution is done
                        if queue_remaining == 0:
                            logger.debug(f"Queue is empty for prompt_id: {prompt_id}")
                            break

            else:
                logger.debug("Received non-string WebSocket message")
                continue  # Handle binary data (previews)

        # Close the WebSocket connection explicitly
        await ws.close()
        logger.debug("WebSocket connection closed")

        # Retrieve and process images
        history = await get_history_async(session, prompt_id)
        history = history[prompt_id]
        for node_id, node_output in history['outputs'].items():
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = await get_image_async(session, image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
                output_images[node_id] = images_output

        return output_images
    except asyncio.TimeoutError:
        logger.error(f"Timeout while waiting for WebSocket message for prompt_id: {prompt_id}")
        await ws.close()
        raise
    except Exception as e:
        logger.error(f"Error in get_images_async: {str(e)}")
        await ws.close()  # Ensure WebSocket is closed on error
        raise  # Re-raise the exception to be caught in the calling function

async def generate_images_async(prompt_text: str, server_address: str, client_id: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            # Load and update the workflow JSON
            with open("comfy/workflow_api2.json", "r", encoding="utf-8") as f:
                workflow_jsondata = f.read()

            jsonw = json.loads(workflow_jsondata)
            jsonw["6"]["inputs"]["text"] = prompt_text

            # Connect to the WebSocket server
            async with websockets.connect(f"ws://{server_address}/ws?clientId={client_id}", ping_interval=20, ping_timeout=60) as ws:
                images = await get_images_async(ws, jsonw, session)

            # Convert images to PIL Image objects
            pil_images = {}
            for node_id in images:
                pil_images[node_id] = []
                for image_data in images[node_id]:
                    image = Image.open(io.BytesIO(image_data))
                    pil_images[node_id].append(image)

            return pil_images
    except Exception as e:
        print(f"Error in generate_images_async: {str(e)}")
        raise  # Re-raise the exception to be caught in the calling function

# Example usage (you can remove this in your actual implementation)
async def main():
    prompt_text = "A beautiful sunset over a mountain range"
    images = await generate_images_async(prompt_text, server_address, client_id)
    print(f"Generated {sum(len(img_list) for img_list in images.values())} images")

if __name__ == "__main__":
    asyncio.run(main())
