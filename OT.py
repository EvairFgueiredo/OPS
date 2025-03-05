import asyncio
import os
import websockets

OTC_TCP_PORT = 860  # Porta pública para conexões OTC
WS_PORT = int(os.environ.get("PORT", 10000))

# Variáveis globais para armazenar a conexão reversa e as mensagens recebidas
reverse_tunnel = None
reverse_queue = asyncio.Queue()

async def handle_ws_connection(websocket, path=None):
    global reverse_tunnel
    print("[Reverse Tunnel] Conexão estabelecida do cliente reverso.")
    reverse_tunnel = websocket
    try:
        # Loop para ler mensagens do cliente reverso e armazená-las na fila
        while True:
            msg = await websocket.recv()
            print(f"[Reverse Tunnel] Mensagem recebida: {len(msg)} bytes")
            await reverse_queue.put(msg)
    except Exception as e:
        print("[Reverse Tunnel] Erro ou conexão fechada:", e)
    finally:
        print("[Reverse Tunnel] Conexão encerrada.")
        reverse_tunnel = None
        # Limpa a fila (opcional)
        while not reverse_queue.empty():
            reverse_queue.get_nowait()

async def handle_tcp_connection(reader, writer):
    global reverse_tunnel
    print("[OTC] Conexão recebida do cliente OTC.")
    if not reverse_tunnel:
        print("[OTC] Nenhum túnel reverso disponível!")
        writer.close()
        await writer.wait_closed()
        return

    async def tcp_to_ws():
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    print("[OTC → WS] Sem dados recebidos, encerrando.")
                    break
                print(f"[OTC → WS] Enviando {len(data)} bytes: {data.hex()}")
                await reverse_tunnel.send(data)
        except Exception as e:
            print("[OTC → WS Erro]", e)

    async def ws_to_tcp():
        try:
            while True:
                data = await reverse_queue.get()
                if data is None:
                    break
                print(f"[WS → OTC] Enviando {len(data)} bytes: {data.hex()}")
                writer.write(data)
                await writer.drain()
        except Exception as e:
            print("[WS → OTC Erro]", e)

    await asyncio.gather(tcp_to_ws(), ws_to_tcp())
    writer.close()
    await writer.wait_closed()
    print("[OTC] Conexão encerrada.")

async def main():
    # Inicia o WebSocket server para o túnel reverso, desabilitando pings automáticos
    ws_server = await websockets.serve(
        handle_ws_connection, "0.0.0.0", WS_PORT, ping_interval=None
    )
    print(f"[Servidor WS Público] Rodando na porta {WS_PORT}")

    # Inicia o TCP server para conexões do OTC
    tcp_server = await asyncio.start_server(handle_tcp_connection, "0.0.0.0", OTC_TCP_PORT)
    print(f"[Servidor TCP Público] Rodando na porta {OTC_TCP_PORT}")

    async with tcp_server, ws_server:
        await asyncio.gather(tcp_server.serve_forever(), ws_server.wait_closed())

if __name__ == "__main__":
    asyncio.run(main())
