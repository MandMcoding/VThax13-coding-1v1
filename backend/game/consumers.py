from channels.generic.websocket import AsyncWebsocketConsumer
import json

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.group_name = f"match_{self.match_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Handle incoming messages: answers, ready, etc.
        # Broadcast to both players as needed
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game_message",
                "message": data
            }
        )

    async def game_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))