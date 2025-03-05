import asyncio
import websockets

# Dicionário para armazenar conexões pendentes: tunnel_id -> conexão "NOVO_TUNEL"
pending_tunnels = {}

async def relay(ws1, ws2):
    async def forward(ws_from, ws_to):
        try:
            async for message in ws_from:
                await ws_to.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass
    await asyncio.gather(forward(ws1, ws2), forward(ws2, ws1))

async def handle_connection(websocket, path):
    try:
        init_msg = await websocket.recv()
    except Exception as e:
        print("Erro ao receber mensagem inicial:", e)
        return

    # Se a mensagem for "NOVO_TUNEL:{tunnel_id}", armazena essa conexão
    if init_msg.startswith("NOVO_TUNEL:"):
        _, tunnel_id = init_msg.split(":", 1)
        print(f"[OT.py] Recebeu NOVO_TUNEL para {tunnel_id}")
        pending_tunnels[tunnel_id] = websocket
        # Aguarda até que a outra conexão chegue para o mesmo tunnel_id
        try:
            while tunnel_id in pending_tunnels and pending_tunnels[tunnel_id] is websocket:
                await asyncio.sleep(0.1)
        except Exception as e:
            print("Erro aguardando pareamento:", e)

    # Se a mensagem for "CONEXAO_RETORNO:{tunnel_id}", procura a conexão pendente
    elif init_msg.startswith("CONEXAO_RETORNO:"):
        _, tunnel_id = init_msg.split(":", 1)
        print(f"[OT.py] Recebeu CONEXAO_RETORNO para {tunnel_id}")
        if tunnel_id in pending_tunnels:
            ws_novo = pending_tunnels.pop(tunnel_id)
            print(f"[OT.py] Túnel {tunnel_id} pareado. Iniciando relay.")
            await websocket.send("TUNEL_ESTABELECIDO")
            await ws_novo.send("TUNEL_ESTABELECIDO")
            await relay(ws_novo, websocket)
            print(f"[OT.py] Túnel {tunnel_id} encerrado.")
        else:
            await websocket.send("ERRO: túnel não encontrado")
    else:
        await websocket.send("ERRO: comando desconhecido")

async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 10000):
        print("[OT.py] Servidor ouvindo em wss://<domínio>:10000")
        await asyncio.Future()  # executa indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
