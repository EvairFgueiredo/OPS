# render_server.py
import asyncio
import websockets
from urllib.parse import parse_qs
import uuid

# Configurações
WS_HOST = "0.0.0.0"
WS_PORT = 8765

# Dicionário para armazenar os túneis ativos (tunnel_id: websocket)
active_tunnels = {}

async def handle_connection(websocket, path):
    try:
        # Extrai parâmetros da query string
        query = parse_qs(path.split('?')[1] if '?' in path else '')
        tunnel_id = query.get('tunnel_id', [None])[0]
        role = query.get('role', [None])[0]  # 'host' ou 'client'

        # Conexão do Host (Tibia Server)
        if role == 'host':
            if not tunnel_id:
                tunnel_id = str(uuid.uuid4())  # Gera novo ID se não fornecido
                
            print(f"⚡ Novo túnel reverso registrado: {tunnel_id}")
            active_tunnels[tunnel_id] = websocket
            await websocket.send(f"TUNNEL_ID:{tunnel_id}")

            # Mantém a conexão ativa
            while True:
                await websocket.recv()  # Mantém o heartbeat

        # Conexão do Cliente OTC
        elif role == 'client':
            if not tunnel_id or tunnel_id not in active_tunnels:
                await websocket.close(code=4001, reason="Tunnel ID inválido")
                return

            host_websocket = active_tunnels[tunnel_id]
            print(f"🔗 Cliente OTC conectado ao túnel {tunnel_id}")

            # Bridge: OTC ↔ Host
            async def forward_client_to_host():
                try:
                    while True:
                        data = await websocket.recv()
                        await host_websocket.send(data)
                        print(f"OTC → Host ({len(data)} bytes)")
                except websockets.exceptions.ConnectionClosed:
                    pass

            async def forward_host_to_client():
                try:
                    while True:
                        data = await host_websocket.recv()
                        await websocket.send(data)
                        print(f"Host → OTC ({len(data)} bytes)")
                except websockets.exceptions.ConnectionClosed:
                    pass

            await asyncio.gather(
                forward_client_to_host(),
                forward_host_to_client()
            )

    except Exception as e:
        print(f"Erro: {str(e)}")
    finally:
        # Limpeza do túnel
        if role == 'host' and tunnel_id in active_tunnels:
            del active_tunnels[tunnel_id]
            print(f"♻️ Túnel {tunnel_id} removido")

async def main():
    async with websockets.serve(
        handle_connection, 
        WS_HOST, 
        WS_PORT, 
        ping_interval=None
    ):
        print(f"🚀 Servidor WebSocket rodando em {WS_HOST}:{WS_PORT}")
        await asyncio.Future()  # Executa indefinidamente

if __name__ == "__main__":
    asyncio.run(main())