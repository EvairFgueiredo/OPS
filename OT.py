# OT.py
import asyncio
import websockets

# Variável global para armazenar a conexão do cliente reverso
reverse_tunnel = None

async def handle_reverse_client(websocket):
    global reverse_tunnel
    reverse_tunnel = websocket
    print("[Reverse Tunnel] Cliente reverso conectado via WebSocket.")
    try:
        # Mantém a conexão aberta
        await websocket.wait_closed()
    finally:
        reverse_tunnel = None

async def main():
    server = await websockets.serve(handle_reverse_client, "0.0.0.0", 10000)
    print("[Servidor Público] Ouvindo em wss://...:10000")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())