import asyncio
import os
import websockets
from urllib.parse import parse_qs

# Dicionário para armazenar túneis ativos.
# Cada túnel terá duas chaves: 'tibia' e 'otc'
tunnels = {}

# Processa requisições não-WebSocket (opcional)
async def process_request(path, request_headers):
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

async def handle_tunnel(websocket, path):
    # Extrai o tunnel_id da query string.
    query = parse_qs(path.split('?')[-1] if '?' in path else '')
    tunnel_id = query.get('tunnel_id', [None])[0]
    
    if not tunnel_id:
        print("[OT.py] Erro: tunnel_id não fornecido.")
        await websocket.close(code=1008, reason="tunnel_id ausente")
        return

    print(f"[OT.py] Túnel {tunnel_id} conectado.")

    try:
        # Aguarda a primeira mensagem para identificar o papel (registro)
        message = await websocket.recv()
        if message == "REGISTER_TIBIA":
            if tunnel_id in tunnels:
                print(f"[OT.py] Erro: Tunnel_id {tunnel_id} já está em uso.")
                await websocket.close(code=1008, reason="Tunnel_id duplicado")
                return
            tunnels[tunnel_id] = {"tibia": websocket, "otc": None}
            print(f"[OT.py] Tibia registrado (Túnel: {tunnel_id}).")

            # Aguarda até 60 segundos pelo registro do OTC
            timeout = 60
            while tunnels[tunnel_id]["otc"] is None and timeout > 0:
                await asyncio.sleep(1)
                timeout -= 1
            if tunnels[tunnel_id]["otc"] is None:
                print(f"[OT.py] Timeout aguardando OTC no túnel {tunnel_id}. Encerrando conexão Tibia.")
                await websocket.close(code=1000, reason="Timeout aguardando OTC")
                return

            otc_ws = tunnels[tunnel_id]["otc"]
            tibia_ws = tunnels[tunnel_id]["tibia"]

            async def forward(source, target, direction):
                try:
                    async for data in source:
                        await target.send(data)
                        print(f"[OT.py] {direction}: {len(data)} bytes encaminhados.")
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"[OT.py] Conexão fechada em {direction}: {e.reason}")
                except Exception as e:
                    print(f"[OT.py] Erro em {direction}: {str(e)}")

            await asyncio.gather(
                forward(tibia_ws, otc_ws, "Tibia → OTC"),
                forward(otc_ws, tibia_ws, "OTC → Tibia")
            )

        elif message == "REGISTER_OTC":
            if tunnel_id not in tunnels or tunnels[tunnel_id]["tibia"] is None:
                print(f"[OT.py] Erro: Tibia não registrado para {tunnel_id}.")
                await websocket.close(code=1008, reason="Tibia ausente")
                return
            tunnels[tunnel_id]["otc"] = websocket
            print(f"[OT.py] OTC registrado (Túnel: {tunnel_id}).")

            # Se o Tibia já estiver registrado, inicie o encaminhamento
            tibia_ws = tunnels[tunnel_id]["tibia"]
            otc_ws = tunnels[tunnel_id]["otc"]

            async def forward(source, target, direction):
                try:
                    async for data in source:
                        await target.send(data)
                        print(f"[OT.py] {direction}: {len(data)} bytes encaminhados.")
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"[OT.py] Conexão fechada em {direction}: {e.reason}")
                except Exception as e:
                    print(f"[OT.py] Erro em {direction}: {str(e)}")

            await asyncio.gather(
                forward(tibia_ws, otc_ws, "Tibia → OTC"),
                forward(otc_ws, tibia_ws, "OTC → Tibia")
            )

        else:
            print(f"[OT.py] Mensagem inválida: {message}")
            await websocket.close(code=1008, reason="Registro inválido")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"[OT.py] Conexão fechada (Túnel: {tunnel_id}). Motivo: {e.reason}")
    except Exception as e:
        print(f"[OT.py] Erro inesperado (Túnel: {tunnel_id}): {str(e)}")
    finally:
        if tunnel_id in tunnels:
            del tunnels[tunnel_id]
            print(f"[OT.py] Túnel {tunnel_id} removido.")

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
