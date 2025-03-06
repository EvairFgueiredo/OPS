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
    query = parse_qs(path.split('?')[-1] if '?' in path else '')
    tunnel_id = query.get('tunnel_id', [None])[0]
    
    if not tunnel_id:
        await websocket.close(code=1008, reason="tunnel_id ausente")
        return

    print(f"[OT.py] Túnel {tunnel_id} conectado.")

    try:
        message = await websocket.recv()
        if message == "REGISTER_TIBIA":
            tunnels[tunnel_id] = {"tibia": websocket, "otc": None}
            print(f"[OT.py] Tibia registrado no túnel {tunnel_id}.")
        elif message == "REGISTER_OTC":
            if tunnel_id in tunnels and tunnels[tunnel_id]["tibia"]:
                tunnels[tunnel_id]["otc"] = websocket
                print(f"[OT.py] OTC registrado no túnel {tunnel_id}.")
            else:
                await websocket.close(code=1008, reason="Tibia não registrado")
                return
        else:
            await websocket.close(code=1008, reason="Registro inválido")
            return

        # Encaminha mensagens entre Tibia e OTC
        tibia_ws = tunnels[tunnel_id]["tibia"]
        otc_ws = tunnels[tunnel_id]["otc"]

        async def forward(source, target):
            async for data in source:
                await target.send(data)
                print(f"[OT.py] Encaminhados {len(data)} bytes.")

        tasks = []
        if otc_ws:
            tasks.append(forward(tibia_ws, otc_ws))
            tasks.append(forward(otc_ws, tibia_ws))
        
        await asyncio.gather(*tasks)

    except websockets.exceptions.ConnectionClosed:
        print(f"[OT.py] Conexão fechada para o túnel {tunnel_id}.")
    finally:
        if tunnel_id in tunnels:
            del tunnels[tunnel_id]

async def main():
    port = int(os.environ.get("PORT", 10000))
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