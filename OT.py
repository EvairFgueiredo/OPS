# OT.py (Atualizado)
import asyncio
import websockets

tunnels = {}  # Dicionário para armazenar conexões ativas

async def handle_tunnel(websocket, path):
    tunnel_id = path.split('=')[-1]
    tunnels[tunnel_id] = websocket
    print(f"[OT.py] Túnel {tunnel_id} conectado.")

    try:
        async for message in websocket:
            # Encaminha a mensagem para o cliente OTC correspondente
            if tunnel_id in tunnels:
                print(f"[OT.py] Encaminhando {len(message)} bytes para o cliente OTC")
                await tunnels[tunnel_id].send(message)
    except Exception as e:
        print(f"[OT.py] Erro no túnel {tunnel_id}: {e}")
    finally:
        del tunnels[tunnel_id]
        print(f"[OT.py] Túnel {tunnel_id} encerrado.")

async def main():
    server = await websockets.serve(handle_tunnel, "0.0.0.0", 10000)
    print("[OT.py] Servidor público ouvindo em wss://...:10000")
    await server.wait_closed()

asyncio.run(main())