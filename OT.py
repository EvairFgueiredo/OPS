import asyncio
import os
import websockets
from urllib.parse import parse_qs
import time

# Dicionário para armazenar túneis ativos.
# Cada túnel terá: 'tibia', 'otc' e 'timestamp'
tunnels = {}

async def process_request(path, request_headers):
    if request_headers.get("Upgrade", "").lower() != "websocket":
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None

async def handle_tunnel(websocket, path):
    # Extrai tunnel_id da query string, se fornecido
    query = parse_qs(path.split('?')[-1] if '?' in path else '')
    tunnel_id = query.get('tunnel_id', [None])[0]
    
    if not tunnel_id:
        # Conexão OTC que não forneceu tunnel_id; espera REQUEST_TUNNEL
        g_msg = "[OT.py] Conexão OTC sem tunnel_id. Aguardando REQUEST_TUNNEL."
        print(g_msg)
        await websocket.send("ERROR: TunnelID not provided, send REQUEST_TUNNEL")
        try:
            message = await websocket.recv()
        except Exception as e:
            print("[OT.py] Erro ao receber mensagem:", e)
            return
        if message != "REQUEST_TUNNEL":
            print(f"[OT.py] Mensagem inválida sem tunnel_id: {message}")
            await websocket.close(code=1008, reason="Registro inválido")
            return
        
        # Procura o túnel com o timestamp mais recente que tem Tibia registrado e OTC ausente
        if not tunnels:
            print("[OT.py] Nenhum túnel disponível no momento.")
            await websocket.send("ERROR: No tunnel available")
            await websocket.close(code=1008, reason="Túnel indisponível")
            return
        
        # Encontra o tunnel com maior timestamp
        latest_tunnel_id = None
        latest_ts = 0
        for tid, conns in tunnels.items():
            if conns.get("tibia") is not None and conns.get("otc") is None:
                if conns.get("timestamp", 0) > latest_ts:
                    latest_ts = conns["timestamp"]
                    latest_tunnel_id = tid
        if not latest_tunnel_id:
            print("[OT.py] Nenhum túnel disponível para OTC.")
            await websocket.send("ERROR: Tunnel indisponível")
            await websocket.close(code=1008, reason="Túnel indisponível")
            return
        
        # Envia o tunnel_id para o OTC
        await websocket.send(f"TUNNEL_ID:{latest_tunnel_id}")
        print(f"[OT.py] Enviado tunnel_id {latest_tunnel_id} para OTC.")
        # Aguarda que o OTC confirme o registro
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
        except asyncio.TimeoutError:
            print(f"[OT.py] Timeout aguardando registro OTC para túnel {latest_tunnel_id}.")
            await websocket.close(code=1000, reason="Timeout OTC")
            return
        if message != "REGISTER_OTC":
            print(f"[OT.py] Registro OTC inválido: {message}")
            await websocket.close(code=1008, reason="Registro OTC inválido")
            return
        tunnels[latest_tunnel_id]["otc"] = websocket
        tunnel_id = latest_tunnel_id
        print(f"[OT.py] OTC registrado (Túnel: {tunnel_id}).")
    else:
        # Se tunnel_id foi fornecido, trata o registro
        print(f"[OT.py] Túnel {tunnel_id} conectado.")
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
        except asyncio.TimeoutError:
            print(f"[OT.py] Timeout aguardando registro no túnel {tunnel_id}.")
            await websocket.close(code=1000, reason="Timeout")
            return
        if message == "REGISTER_TIBIA":
            if tunnel_id in tunnels:
                print(f"[OT.py] Erro: Tunnel_id {tunnel_id} já está em uso.")
                await websocket.close(code=1008, reason="Tunnel_id duplicado")
                return
            # Registra a conexão do Tibia e guarda o timestamp atual
            tunnels[tunnel_id] = {"tibia": websocket, "otc": None, "timestamp": time.time()}
            print(f"[OT.py] Tibia registrado (Túnel: {tunnel_id}).")
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

    # Se ambos os lados estiverem registrados, inicia o encaminhamento
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

    # Limpeza final
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
