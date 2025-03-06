import asyncio
import websockets
import os
from urllib.parse import parse_qs

class TunnelManager:
    def __init__(self):
        self.tibias = {}  # {tunnel_id: websocket}
        self.otcs = {}    # {tunnel_id: websocket}

    async def handle_tunnel(self, websocket, path):
        try:
            # Extrai tunnel_id da query string
            query = parse_qs(path.split('?')[-1] if '?' in path else '')
            tunnel_id = query.get('tunnel_id', [None])[0]
            
            if not tunnel_id:
                print("[OT.py] Erro: tunnel_id não fornecido.")
                await websocket.close(code=1008, reason="tunnel_id ausente")
                return

            print(f"[OT.py] Nova conexão (Túnel: {tunnel_id})")

            # Aguarda a mensagem de registro
            message = await websocket.recv()
            if "REGISTER_TIBIA" in message:
                self.tibias[tunnel_id] = websocket
                print(f"[OT.py] Tibia registrado no túnel {tunnel_id}.")
                await self.forward_messages(websocket, tunnel_id, is_tibia=True)
            elif "REGISTER_OTC" in message:
                self.otcs[tunnel_id] = websocket
                print(f"[OT.py] OTC registrado no túnel {tunnel_id}.")
                await self.forward_messages(websocket, tunnel_id, is_tibia=False)
            else:
                print(f"[OT.py] Mensagem inválida: {message}")
                await websocket.close(code=1008, reason="Registro inválido")

        except Exception as e:
            print(f"[OT.py] Erro: {e}")

    async def forward_messages(self, websocket, tunnel_id, is_tibia):
        try:
            async for data in websocket:
                if is_tibia:
                    if tunnel_id in self.otcs:
                        await self.otcs[tunnel_id].send(data)
                        print(f"[OT.py] Tibia → OTC ({len(data)} bytes)")
                    else:
                        print(f"[OT.py] Aviso: OTC não encontrado para o túnel {tunnel_id}.")
                else:
                    if tunnel_id in self.tibias:
                        await self.tibias[tunnel_id].send(data)
                        print(f"[OT.py] OTC → Tibia ({len(data)} bytes)")
                    else:
                        print(f"[OT.py] Aviso: Tibia não encontrado para o túnel {tunnel_id}.")
        except websockets.exceptions.ConnectionClosed:
            print(f"[OT.py] Conexão fechada para o túnel {tunnel_id}.")
        except Exception as e:
            print(f"[OT.py] Erro no túnel {tunnel_id}: {e}")
        finally:
            # Remove registros ao encerrar
            if is_tibia and tunnel_id in self.tibias:
                del self.tibias[tunnel_id]
            elif not is_tibia and tunnel_id in self.otcs:
                del self.otcs[tunnel_id]
            print(f"[OT.py] Túnel {tunnel_id} encerrado.")

async def process_request(path, request_headers):
    # Se a requisição não for de upgrade para WebSocket (por exemplo, health check),
    # retorna uma resposta HTTP simples.
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

async def main():
    tunnel_manager = TunnelManager()  # Cria a instância para acessar os métodos de tratamento
    PORT = int(os.getenv("PORT", 10000))
    async with websockets.serve(
        tunnel_manager.handle_tunnel, "0.0.0.0", PORT,
        process_request=process_request
    ):
        print(f"[OT.py] Servidor WebSocket rodando em 0.0.0.0:{PORT}")
        await asyncio.Future()  # Mantém o servidor em execução

if __name__ == "__main__":
    asyncio.run(main())
