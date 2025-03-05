# OT.py (Simplificado)
import asyncio
import websockets

async def handle_tunnel(websocket, path):
    tunnel_id = path.split('=')[-1]
    print(f"[OT.py] Túnel {tunnel_id} conectado.")
    try:
        async for message in websocket:
            print(f"[OT.py] Dados recebidos: {len(message)} bytes")
    except Exception as e:
        print(f"[OT.py] Erro: {e}")

async def main():
    server = await websockets.serve(handle_tunnel, "0.0.0.0", 10000)
    await server.wait_closed()

asyncio.run(main())