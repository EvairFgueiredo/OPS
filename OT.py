import asyncio
import os
import websockets
from urllib.parse import parse_qs

async def process_request(path, request_headers):
    # Se a requisição não for de upgrade para WebSocket (por exemplo, um health check via HEAD)
    # retorna uma resposta HTTP simples.
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

tunnels = {}  # Armazena WebSockets por tunnel_id

async def handle_tunnel(websocket, path):
    # Extrai tunnel_id
    query = parse_qs(path.split('?')[-1] if '?' in path else '')
    tunnel_id = query.get('tunnel_id', [None])[0]
    if not tunnel_id:
        print("[OT.py] Erro: tunnel_id não fornecido.")
        await websocket.close(code=1008, reason="tunnel_id ausente")
        return

    print(f"[OT.py] Túnel {tunnel_id} conectado.")

    try:
        message = await websocket.recv()
        if message.startswith("REGISTER_TIBIA"):
            tunnels[tunnel_id] = {"tibia": websocket}
            print(f"[OT.py] Tibia registrado no túnel {tunnel_id}.")
        elif message.startswith("REGISTER_OTC"):
            tunnels[tunnel_id] = {"otc": websocket}
            print(f"[OT.py] OTC registrado no túnel {tunnel_id}.")
        else:
            print(f"[OT.py] Mensagem de registro inválida: {message}")
            await websocket.close(code=1008, reason="Registro inválido")
            return

        # Roteamento entre Tibia e OTC
        if "tibia" in tunnels[tunnel_id] and "otc" in tunnels[tunnel_id]:
            tibia_ws = tunnels[tunnel_id]["tibia"]
            otc_ws = tunnels[tunnel_id]["otc"]
            async for data in websocket:
                if websocket == tibia_ws:
                    await otc_ws.send(data)
                else:
                    await tibia_ws.send(data)
    except websockets.exceptions.ConnectionClosed:
        print(f"[OT.py] Conexão fechada para o túnel {tunnel_id}.")
    except Exception as e:
        print(f"[OT.py] Erro no túnel {tunnel_id}: {e}")
    finally:
        if tunnel_id in tunnels:
            del tunnels[tunnel_id]

async def main():
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(
        handle_tunnel,
        "0.0.0.0",
        port,
        process_request=process_request
    ):
        print(f"[OT.py] Servidor WebSocket rodando em 0.0.0.0:{port}")
        await asyncio.Future()  # Mantém o servidor rodando

if __name__ == "__main__":
    asyncio.run(main())
