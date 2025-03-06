import asyncio
import os
import websockets
from urllib.parse import parse_qs

tunnels = {}  # Armazena conexões Tibia e OTC por tunnel_id

async def process_request(path, request_headers):
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

async def handle_tunnel(websocket, path):
    # ... (extração do tunnel_id)

    try:
        message = await websocket.recv()
        if message == "REGISTER_TIBIA":
            if tunnel_id in tunnels:
                print(f"[OT.py] Erro: tunnel_id {tunnel_id} já registrado.")
                await websocket.close(code=1008, reason="Tunnel_id em uso")
                return
            tunnels[tunnel_id] = {"tibia": websocket, "otc": None}
            print(f"[OT.py] Tibia registrado no túnel {tunnel_id}.")
        elif message == "REGISTER_OTC":
            if tunnel_id not in tunnels or tunnels[tunnel_id]["tibia"] is None:
                print(f"[OT.py] Erro: Tibia não registrado para o túnel {tunnel_id}.")
                await websocket.close(code=1008, reason="Tibia não registrado")
                return
            tunnels[tunnel_id]["otc"] = websocket
            print(f"[OT.py] OTC registrado no túnel {tunnel_id}.")

            # Inicia o roteamento
            tibia_ws = tunnels[tunnel_id]["tibia"]
            otc_ws = tunnels[tunnel_id]["otc"]

            async def forward(source, target):
                try:
                    async for data in source:
                        await target.send(data)
                        print(f"[OT.py] Dados encaminhados: {len(data)} bytes.")
                except websockets.exceptions.ConnectionClosed:
                    print("[OT.py] Conexão fechada durante o encaminhamento.")

            await asyncio.gather(
                forward(tibia_ws, otc_ws),
                forward(otc_ws, tibia_ws)
            )

    except websockets.exceptions.ConnectionClosed:
        print(f"[OT.py] Conexão fechada para o túnel {tunnel_id}.")
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
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())