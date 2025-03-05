import asyncio
import websockets

# Dicionário para armazenar túneis pendentes:
# tunnel_id -> (ws_novo, pair_future)
pending_tunnels = {}

async def handle_connection(websocket, path):
    try:
        init_msg = await websocket.recv()
    except Exception as e:
        print("Erro ao receber mensagem inicial:", e)
        return

    if init_msg.startswith("NOVO_TUNEL:"):
        # Recebe mensagem no formato "NOVO_TUNEL:<tunnel_id>"
        _, tunnel_id = init_msg.split(":", 1)
        print(f"[OT.py] NOVO_TUNEL recebido para {tunnel_id}")
        # Cria um Future para aguardar o pareamento
        pair_future = asyncio.get_event_loop().create_future()
        pending_tunnels[tunnel_id] = (websocket, pair_future)
        try:
            # Aguarda até 10 segundos para o pareamento
            partner_ws = await asyncio.wait_for(pair_future, timeout=10)
            # Se pareado, envia confirmação para a conexão NOVO_TUNEL
            await websocket.send("TUNEL_ESTABELECIDO")
            print(f"[OT.py] Túnel {tunnel_id} pareado. Iniciando relay.")
            await relay(websocket, partner_ws)
            print(f"[OT.py] Túnel {tunnel_id} encerrado.")
        except asyncio.TimeoutError:
            print(f"[OT.py] Timeout aguardando pareamento para {tunnel_id}")
            await websocket.send("ERRO: Timeout no pareamento")
        finally:
            pending_tunnels.pop(tunnel_id, None)

    elif init_msg.startswith("CONEXAO_RETORNO:"):
        # Recebe mensagem no formato "CONEXAO_RETORNO:<tunnel_id>"
        _, tunnel_id = init_msg.split(":", 1)
        print(f"[OT.py] CONEXAO_RETORNO recebido para {tunnel_id}")
        if tunnel_id in pending_tunnels:
            ws_novo, pair_future = pending_tunnels[tunnel_id]
            if not pair_future.done():
                pair_future.set_result(websocket)
                await websocket.send("TUNEL_ESTABELECIDO")
            else:
                await websocket.send("ERRO: Túnel já pareado")
        else:
            await websocket.send("ERRO: Túnel não encontrado")
    else:
        await websocket.send("ERRO: Comando desconhecido")

async def relay(ws1, ws2):
    async def forward(ws_from, ws_to):
        try:
            async for message in ws_from:
                await ws_to.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass
    await asyncio.gather(forward(ws1, ws2), forward(ws2, ws1))

async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 10000):
        print("[OT.py] Servidor ouvindo em wss://<DOMÍNIO>:10000")
        await asyncio.Future()  # roda indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
