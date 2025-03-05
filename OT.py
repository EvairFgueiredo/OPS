import asyncio
import websockets

# Armazena a conexão do cliente reverso
reverse_tunnel = None

async def handle_reverse_client(websocket):
    global reverse_tunnel
    reverse_tunnel = websocket
    print("[Reverse Tunnel] Cliente reverso conectado via WebSocket.")
    try:
        # Mantém a conexão e encaminha mensagens bidirecionalmente
        async for message in websocket:
            print(f"[Tibia → OTC] Encaminhando {len(message)} bytes para o cliente OTC")
            if reverse_tunnel:
                await reverse_tunnel.send(message)
    except Exception as e:
        print("[Erro no túnel reverso]:", e)
    finally:
        reverse_tunnel = None

async def main():
    server = await websockets.serve(handle_reverse_client, "0.0.0.0", 10000)
    print("[Servidor Público] Ouvindo em wss://...:10000")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())