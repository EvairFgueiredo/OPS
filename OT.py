import asyncio
import os
import websockets
from urllib.parse import parse_qs
import time  # Adicionado

tunnels = {}

async def process_request(path, request_headers):
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

async def handle_tunnel(websocket, path):
    query = parse_qs(path.split('?')[-1] if '?' in path else '')
    tunnel_id = query.get('tunnel_id', [None])[0]
    
    if not tunnel_id:
        print("[OT.py] Conexão OTC sem tunnel_id. Aguardando REQUEST_TUNNEL.")
        message = await websocket.recv()
        if message != "REQUEST_TUNNEL":
            print(f"[OT.py] Mensagem inválida: {message}")
            await websocket.close(code=1008, reason="Registro inválido")
            return
        
        # Seleciona o túnel mais recente
        available = [
            (tid, conns["created_at"])
            for tid, conns in tunnels.items()
            if conns.get("tibia") and not conns.get("otc")
        ]
        if not available:
            print("[OT.py] Nenhum túnel disponível.")
            await websocket.close(code=1008, reason="Túnel indisponível")
            return
        
        available.sort(key=lambda x: -x[1])  # Ordena do mais recente
        tunnel_id = available[0][0]
        await websocket.send(f"TUNNEL_ID:{tunnel_id}")
        print(f"[OT.py] Enviado tunnel_id {tunnel_id} para OTC.")
        
        message = await websocket.recv()
        if message != "REGISTER_OTC":
            print(f"[OT.py] Registro OTC inválido: {message}")
            await websocket.close(code=1008, reason="Registro OTC inválido")
            return
        tunnels[tunnel_id]["otc"] = websocket
        print(f"[OT.py] OTC registrado (Túnel: {tunnel_id}).")
    else:
        print(f"[OT.py] Túnel {tunnel_id} conectado.")
        message = await websocket.recv()
        if message == "REGISTER_TIBIA":
            if tunnel_id in tunnels:
                print(f"[OT.py] Erro: Tunnel_id {tunnel_id} já está em uso.")
                await websocket.close(code=1008, reason="Tunnel_id duplicado")
                return
            # Adiciona timestamp ao criar o túnel
            tunnels[tunnel_id] = {
                "tibia": websocket,
                "otc": None,
                "created_at": time.time()  # Novo campo
            }
            print(f"[OT.py] Tibia registrado (Túnel: {tunnel_id}).")
            
            timeout = 60
            while tunnels[tunnel_id]["otc"] is None and timeout > 0:
                await asyncio.sleep(1)
                timeout -= 1
            if tunnels[tunnel_id]["otc"] is None:
                print(f"[OT.py] Timeout aguardando OTC no túnel {tunnel_id}.")
                await websocket.close(code=1000, reason="Timeout aguardando OTC")
                return
        elif message == "REGISTER_OTC":
            if tunnel_id not in tunnels or tunnels[tunnel_id]["tibia"] is None:
                print(f"[OT.py] Erro: Tibia não registrado para {tunnel_id}.")
                await websocket.close(code=1008, reason="Tibia ausente")
                return
            tunnels[tunnel_id]["otc"] = websocket
            print(f"[OT.py] OTC registrado (Túnel: {tunnel_id}).")
        else:
            print(f"[OT.py] Mensagem inválida: {message}")
            await websocket.close(code=1008, reason="Registro inválido")
            return

    if tunnel_id in tunnels and tunnels[tunnel_id].get("tibia") and tunnels[tunnel_id].get("otc"):
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

    if tunnel_id in tunnels:
        del tunnels[tunnel_id]
        print(f"[OT.py] Túnel {tunnel_id} removido.")

# Função para limpar túneis antigos
async def cleanup_old_tunnels():
    while True:
        await asyncio.sleep(10)  # Verifica a cada 10 segundos
        now = time.time()
        to_delete = []
        for tid, conns in tunnels.items():
            if conns["otc"] is None and (now - conns["created_at"]) > 30:  # 30 segundos de timeout
                to_delete.append(tid)
        for tid in to_delete:
            if tunnels[tid]["tibia"]:
                await tunnels[tid]["tibia"].close()
            del tunnels[tid]
            print(f"[OT.py] Túnel {tid} removido por timeout.")

async def main():
    port = int(os.environ.get("PORT", 10000))
    async with websockets.serve(
        handle_tunnel, 
        "0.0.0.0", 
        port,
        process_request=process_request
    ):
        print(f"[OT.py] Servidor WebSocket rodando em 0.0.0.0:{port}")
        asyncio.create_task(cleanup_old_tunnels())  # Inicia a limpeza
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())