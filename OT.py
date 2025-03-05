import asyncio
import websockets

# Dicionário para armazenar túneis ativos: tunnel_id -> (ws_in, ws_out)
tunnels = {}

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
        # Recebe a mensagem inicial para identificar a conexão
        init_msg = await websocket.recv()
    except Exception as e:
        print("Erro ao receber mensagem inicial:", e)
        return

    # Protocolo simples:
    # Se a mensagem começar com "NOVO_TUNEL:" é a conexão iniciada pelo reverse client.
    # Exemplo do formato: "NOVO_TUNEL:ws://<callback>:20000:tunnel123"
    if init_msg.startswith("NOVO_TUNEL:"):
        try:
            # Extrai callback_url e tunnel_id
            _, callback_url, tunnel_id = init_msg.split(":", 2)
        except ValueError:
            await websocket.send("ERRO: formato inválido")
            return

        print(f"[OT.py] Recebeu solicitação de túnel {tunnel_id} com callback {callback_url}")

        # OT.py conecta de volta ao reverse client via callback URL
        try:
            ws_return = await websockets.connect(callback_url)
            await ws_return.send(f"CONEXAO_RETORNO:{tunnel_id}")
            print(f"[OT.py] Conectado de volta ao reverse client para túnel {tunnel_id}")
        except Exception as e:
            print(f"[OT.py] Erro ao conectar no callback {callback_url}: {e}")
            await websocket.send("ERRO: não foi possível conectar no callback")
            return

        # Armazena as duas conexões e inicia o relay
        tunnels[tunnel_id] = (websocket, ws_return)
        await websocket.send("TUNEL_ESTABELECIDO")
        print(f"[OT.py] Túnel {tunnel_id} estabelecido. Iniciando relay.")
        await relay(websocket, ws_return)
        print(f"[OT.py] Túnel {tunnel_id} encerrado.")
        del tunnels[tunnel_id]

    elif init_msg.startswith("CONEXAO_RETORNO:"):
        # Se receber essa mensagem diretamente, trata como inesperado
        await websocket.send("ERRO: Conexão de retorno inesperada")
    else:
        await websocket.send("ERRO: comando desconhecido")

async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 10000):
        print("[OT.py] Servidor ouvindo em wss://<domínio>:10000")
        await asyncio.Future()  # executa indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
