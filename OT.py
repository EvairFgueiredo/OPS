import asyncio
import websockets
import os

# A porta utilizada será definida pela variável de ambiente PORT do Render ou, se não estiver definida, usará 10000.
WEB_SOCKET_PORT = int(os.environ.get("PORT", 10000))

# Variável global para armazenar a conexão reversa (única, neste exemplo)
reverse_connection = None

# Handler para a conexão reversa (do cliente reverso, que está na máquina local com o Open Tibia)
async def handle_reverse_connection(websocket, path):
    global reverse_connection
    print("[Reverse] Conexão reversa estabelecida.")
    # Se já houver uma conexão reversa ativa, recusa a nova conexão
    if reverse_connection is not None:
        print("Já existe uma conexão reversa ativa. Fechando nova conexão.")
        await websocket.send("Erro: Conexão reversa já ativa.")
        await websocket.close()
        return
    reverse_connection = websocket
    try:
        await websocket.wait_closed()
    finally:
        print("Conexão reversa encerrada.")
        reverse_connection = None

# Handler para as conexões dos clientes OTC
async def handle_client_connection(websocket, path):
    global reverse_connection
    print(f"[Cliente OTC] Conexão de {websocket.remote_address}")
    if reverse_connection is None:
        await websocket.send("Erro: conexão reversa não disponível.")
        await websocket.close()
        return

    # Funções para encaminhar dados entre o cliente e a conexão reversa
    async def client_to_reverse():
        try:
            async for message in websocket:
                print(f"[Cliente -> Reverse] Enviando {len(message)} bytes")
                await reverse_connection.send(message)
        except Exception as e:
            print("Erro no encaminhamento do cliente para reverse:", e)

    async def reverse_to_client():
        try:
            async for message in reverse_connection:
                print(f"[Reverse -> Cliente] Enviando {len(message)} bytes")
                await websocket.send(message)
        except Exception as e:
            print("Erro no encaminhamento do reverse para cliente:", e)
    
    await asyncio.gather(client_to_reverse(), reverse_to_client())

# Roteador que direciona as conexões conforme o path da URL
async def router(websocket, path):
    print(f"Nova conexão: path={path}")
    if path == "/reverse":
        await handle_reverse_connection(websocket, path)
    elif path == "/client":
        await handle_client_connection(websocket, path)
    else:
        await websocket.send("Caminho inválido.")
        await websocket.close()

async def main():
    server = await websockets.serve(router, "0.0.0.0", WEB_SOCKET_PORT)
    print(f"Servidor WebSocket rodando na porta {WEB_SOCKET_PORT}")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
