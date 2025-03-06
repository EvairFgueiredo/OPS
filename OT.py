import asyncio
import websockets

# Configurações
LOCAL_WS_IP = "0.0.0.0"
LOCAL_WS_PORT = 10000

# Armazena conexões ativas
tunnels = {}

async def ws_handler(websocket, path):
    tunnel_id = path.split('=')[-1]
    print(f"[Servidor Render] Nova conexão WebSocket para túnel {tunnel_id}")
    
    tunnels[tunnel_id] = websocket
    try:
        while True:
            message = await websocket.recv()
            if tunnel_id in tunnels:
                await tunnels[tunnel_id].send(message)
    except websockets.ConnectionClosed:
        print(f"[Servidor Render] Túnel {tunnel_id} fechado")
    finally:
        tunnels.pop(tunnel_id, None)

async def start_ws_server():
    server = await websockets.serve(ws_handler, LOCAL_WS_IP, LOCAL_WS_PORT)
    print(f"[Servidor Render] WebSocket rodando em {LOCAL_WS_IP}:{LOCAL_WS_PORT}")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_ws_server())

# 📌 Esse programa deve rodar no Render para ser o intermediário de WebSocket! 🚀
