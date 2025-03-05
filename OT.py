# Programa 2: relay_server.py
import asyncio
import websockets
from urllib.parse import urlparse, parse_qs

# Dicionário para armazenar túneis ativos.
# Cada túnel é identificado por 'tunnel_id' e possui duas conexões:
# 'client' (Programa 1) e 'server' (Programa 3).
tunnels = {}

async def relay_messages(ws, tunnel_id, role):
    try:
        async for message in ws:
            print(f"[Programa 2] Mensagem de {role} no túnel {tunnel_id}: {len(message)} bytes")
            other_role = "server" if role == "client" else "client"
            if tunnel_id in tunnels and tunnels[tunnel_id].get(other_role):
                other_ws = tunnels[tunnel_id][other_role]
                await other_ws.send(message)
                print(f"[Programa 2] Encaminhado para {other_role} no túnel {tunnel_id}")
            else:
                print(f"[Programa 2] Outro lado ({other_role}) não conectado para túnel {tunnel_id}")
    except Exception as e:
        print(f"[Programa 2] Erro no túnel {tunnel_id} ({role}): {e}")
    finally:
        print(f"[Programa 2] Conexão {role} no túnel {tunnel_id} encerrada")
        if tunnel_id in tunnels:
            tunnels[tunnel_id].pop(role, None)
            if not tunnels[tunnel_id]:
                tunnels.pop(tunnel_id)

async def handler(websocket, path):
    # Extrai parâmetros da URL: role e tunnel_id.
    parsed = urlparse(path)
    params = parse_qs(parsed.query)
    role = params.get("role", [None])[0]
    tunnel_id = params.get("tunnel_id", [None])[0]
    if role not in ["client", "server"] or not tunnel_id:
        await websocket.close()
        return
    print(f"[Programa 2] Nova conexão: role={role}, tunnel_id={tunnel_id}")
    if tunnel_id not in tunnels:
        tunnels[tunnel_id] = {}
    tunnels[tunnel_id][role] = websocket
    await relay_messages(websocket, tunnel_id, role)

async def main():
    ws_server = await websockets.serve(handler, "0.0.0.0", 10000)
    print("[Programa 2] Servidor WebSocket (Relay) rodando na porta 10000")
    await ws_server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
