import asyncio
import websockets
import os

# Porta definida pelo Render
PORT = int(os.environ.get("PORT", 10000))

# Lista para armazenar conexões ativas
connections = set()

async def handler(websocket):
    print("[WebSocket] Nova conexão estabelecida!")
    connections.add(websocket)

    try:
        async for message in websocket:
            print(f"[WebSocket] Mensagem recebida ({len(message)} bytes)")
            # Aqui você pode fazer o que quiser com os pacotes
    except websockets.exceptions.ConnectionClosed:
        print("[WebSocket] Conexão fechada")
    finally:
        connections.remove(websocket)

async def main():
    print(f"Iniciando WebSocket na porta {PORT}...")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # Mantém o servidor rodando

if __name__ == "__main__":
    asyncio.run(main())
