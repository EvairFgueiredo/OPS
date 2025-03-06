import asyncio
import os
import websockets
from urllib.parse import parse_qs
import time

# Dicionário para armazenar túneis ativos
tunnels = {}

async def process_request(path, request_headers):
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

async def handle_tunnel(websocket, path):
    query = parse_qs(path.split('?')[-1]) if '?' in path else {}
    tunnel_id = query.get('tunnel_id', [None])[0]

    if not tunnel_id:
        print("[OT.py] Conexão OTC sem tunnel_id. Aguardando REQUEST_TUNNEL.")
        try:
            message = await websocket.recv()
            if message == "REQUEST_TUNNEL":
                # Se não há túnel, espera até que o Tibia registre um túnel
                await websocket.send("WAITING_FOR_TUNNEL")
                print("[OT.py] Esperando registro do Tibia...")
                
                # Espera até que o túnel seja criado
                for _ in range(60):  # Espera até 60 segundos
                    if tunnels:
                        latest_tunnel_id = max(tunnels, key=lambda t: tunnels[t]["timestamp"])
                        await websocket.send(f"TUNNEL_ID:{latest_tunnel_id}")
                        print(f"[OT.py] Enviado tunnel_id {latest_tunnel_id} para OTC.")
                        tunnels[latest_tunnel_id]["otc"] = websocket
                        break
                    await asyncio.sleep(1)
                else:
                    await websocket.send("ERROR: No tunnel available")
                    await websocket.close(code=1008, reason="Túnel indisponível")
        except Exception as e:
            print("[OT.py] Erro ao receber mensagem do OTC:", e)

    else:
        print(f"[OT.py] Túnel {tunnel_id} conectado.")
        try:
            message = await websocket.recv()
            if message == "REGISTER_TIBIA":
                tunnels[tunnel_id] = {"tibia": websocket, "otc": None, "timestamp": time.time()}
                print(f"[OT.py] Tibia registrado (Túnel: {tunnel_id}).")
            elif message == "REGISTER_OTC":
                if tunnel_id in tunnels and tunnels[tunnel_id]["tibia"]:
                    tunnels[tunnel_id]["otc"] = websocket
                    print(f"[OT.py] OTC registrado (Túnel: {tunnel_id}).")
                else:
                    await websocket.send("ERROR: Tibia not registered")
                    await websocket.close(code=1008, reason="Tibia não registrado")
        except Exception as e:
            print("[OT.py] Erro ao processar conexão:", e)

    if tunnel_id in tunnels and tunnels[tunnel_id].get("tibia") and tunnels[tunnel_id].get("otc"):
        tibia_ws = tunnels[tunnel_id]["tibia"]
        otc_ws = tunnels[tunnel_id]["otc"]

        async def forward(source, target, direction):
            try:
                async for data in source:
                    await target.send(data)
                    print(f"[OT.py] {direction}: {len(data)} bytes encaminhados.")
            except websockets.exceptions.ConnectionClosed:
                print(f"[OT.py] Conexão fechada em {direction}.")
            except Exception as e:
                print(f"[OT.py] Erro em {direction}: {str(e)}")

        await asyncio.gather(forward(tibia_ws, otc_ws, "Tibia → OTC"), forward(otc_ws, tibia_ws, "OTC → Tibia"))

        del tunnels[tunnel_id]
        print(f"[OT.py] Túnel {tunnel_id} removido.")

async def main():
    port = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handle_tunnel, "0.0.0.0", port, process_request=process_request):
        print(f"[OT.py] Servidor WebSocket rodando em 0.0.0.0:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
