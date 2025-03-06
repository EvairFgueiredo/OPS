import asyncio
import websockets
from urllib.parse import parse_qs
import os

class TunnelManager:
    def __init__(self):
        self.tibias = {}  # Armazena o websocket do Tibia por tunnel_id
        self.otcs = {}    # Armazena o websocket do OTC por tunnel_id

    async def handle_tunnel(self, websocket, path):
        # Extrai o tunnel_id da query string (ex: ?tunnel_id=abc123)
        query = parse_qs(path.split('?')[-1] if '?' in path else '')
        tunnel_id = query.get('tunnel_id', [None])[0]
        if not tunnel_id:
            print("[OT.py] Erro: tunnel_id não fornecido.")
            await websocket.close(code=1008, reason="tunnel_id ausente")
            return

        print(f"[OT.py] Túnel {tunnel_id} conectado.")

        try:
            # Aguarda a mensagem de registro
            message = await websocket.recv()
            if message.startswith("REGISTER_TIBIA"):
                self.tibias[tunnel_id] = websocket
                print(f"[OT.py] Tibia registrado no túnel {tunnel_id}.")
            elif message.startswith("REGISTER_OTC"):
                self.otcs[tunnel_id] = websocket
                print(f"[OT.py] OTC registrado no túnel {tunnel_id}.")
            else:
                print(f"[OT.py] Mensagem de registro inválida: {message}")
                await websocket.close(code=1008, reason="Registro inválido")
                return

            # Encaminha mensagens entre os dois pares se ambos estiverem conectados
            async for data in websocket:
                if tunnel_id in self.tibias and tunnel_id in self.otcs:
                    # Se o websocket atual é o Tibia, encaminha para o OTC; caso contrário, vice-versa.
                    if websocket == self.tibias[tunnel_id]:
                        target = self.otcs[tunnel_id]
                        print(f"[OT.py] Encaminhando mensagem de Tibia para OTC ({len(data)} bytes).")
                    else:
                        target = self.tibias[tunnel_id]
                        print(f"[OT.py] Encaminhando mensagem de OTC para Tibia ({len(data)} bytes).")
                    await target.send(data)
                else:
                    print(f"[OT.py] Nenhum par encontrado para o túnel {tunnel_id}.")
        except websockets.exceptions.ConnectionClosed:
            print(f"[OT.py] Conexão fechada para o túnel {tunnel_id}.")
        finally:
            if tunnel_id in self.tibias and self.tibias[tunnel_id] == websocket:
                del self.tibias[tunnel_id]
            if tunnel_id in self.otcs and self.otcs[tunnel_id] == websocket:
                del self.otcs[tunnel_id]
            print(f"[OT.py] Túnel {tunnel_id} removido.")

async def main():
    manager = TunnelManager()
    port = int(os.environ.get("PORT", 10000))  # Use a porta do Render ou 10000 localmente
    server = await websockets.serve(manager.handle_tunnel, "0.0.0.0", port)
    print(f"[OT.py] Servidor rodando em 0.0.0.0:{port}")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
