# OT.py
import asyncio
import websockets
import os

class TunnelManager:
    def __init__(self):
        self.tibias = {}  # {tunnel_id: websocket}
        self.otcs = {}    # {tunnel_id: websocket}

    async def handle_tunnel(self, websocket, path):
        tunnel_id = path.split('=')[-1]
        print(f"[OT.py] Nova conexão (Túnel: {tunnel_id})")

        try:
            message = await websocket.recv()
            if "REGISTER_TIBIA" in message:
                self.tibias[tunnel_id] = websocket
                print(f"[OT.py] Tibia registrado no túnel {tunnel_id}.")
                await self.forward_messages(websocket, tunnel_id, is_tibia=True)
            elif "REGISTER_OTC" in message:
                self.otcs[tunnel_id] = websocket
                print(f"[OT.py] OTC registrado no túnel {tunnel_id}.")
                await self.forward_messages(websocket, tunnel_id, is_tibia=False)
        except Exception as e:
            print(f"[OT.py] Erro: {e}")

    async def forward_messages(self, websocket, tunnel_id, is_tibia):
        try:
            async for data in websocket:
                if is_tibia and tunnel_id in self.otcs:
                    await self.otcs[tunnel_id].send(data)
                    print(f"[OT.py] Tibia → OTC ({len(data)} bytes)")
                elif not is_tibia and tunnel_id in self.tibias:
                    await self.tibias[tunnel_id].send(data)
                    print(f"[OT.py] OTC → Tibia ({len(data)} bytes)")
        except Exception as e:
            print(f"[OT.py] Erro no túnel {tunnel_id}: {e}")
        finally:
            if is_tibia:
                del self.tibias[tunnel_id]
            else:
                del self.otcs[tunnel_id]
            print(f"[OT.py] Túnel {tunnel_id} encerrado.")

async def main():
    tunnel_manager = TunnelManager()
    PORT = int(os.getenv("PORT", 10000))  # Usa a porta do Render ou 10000
    async with websockets.serve(tunnel_manager.handle_tunnel, "0.0.0.0", PORT):
        print(f"[OT.py] Servidor WebSocket rodando em 0.0.0.0:{PORT}")
        await asyncio.Future()

asyncio.run(main())