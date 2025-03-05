import asyncio
import os
import websockets

OTC_TCP_PORT = 860  # Porta pública para conexões OTC
WS_PORT = int(os.environ.get("PORT", 10000))

# Variáveis globais para armazenar a conexão reversa e as mensagens recebidas
reverse_tunnel = None

async def handle_ws_connection(websocket):
    global reverse_tunnel
    print("[Reverse Tunnel] Conexão estabelecida do cliente reverso.")
    reverse_tunnel = websocket
    try:
        async for message in websocket:
            print(f"[Reverse Tunnel] Mensagem recebida: {len(message)} bytes")
            if reverse_tunnel:
                await reverse_tunnel.send(message)
    except Exception as e:
        print("[Reverse Tunnel] Erro ou conexão fechada:", e)
    finally:
        print("[Reverse Tunnel] Conexão encerrada.")
        reverse_tunnel = None

async def handle_tcp_connection(reader, writer):
    global reverse_tunnel
    print("[OTC] Conexão recebida do cliente OTC.")
    
    if not reverse_tunnel:
        print("[OTC] Nenhum túnel reverso disponível!")
        writer.close()
        await writer.wait_closed()
        return

    try:
        async def tcp_to_ws():
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                print(f"[OTC → WS] Enviando {len(data)} bytes")
                await reverse_tunnel.send(data)

        async def ws_to_tcp():
            while True:
                ws_data = await reverse_tunnel.recv()
                print(f"[WS → OTC] Recebendo {len(ws_data)} bytes")
                writer.write(ws_data)
                await writer.drain()

        await asyncio.gather(tcp_to_ws(), ws_to_tcp())

    except Exception as e:
        print("[TCP ↔ WS Erro]", e)
    finally:
        writer.close()
        await writer.wait_closed()
        print("[OTC] Conexão encerrada.")

async def main():
    ws_server = await websockets.serve(handle_ws_connection, "0.0.0.0", WS_PORT)
    print(f"[Servidor WS Público] Rodando na porta {WS_PORT}")

    tcp_server = await asyncio.start_server(handle_tcp_connection, "0.0.0.0", OTC_TCP_PORT)
    print(f"[Servidor TCP Público] Rodando na porta {OTC_TCP_PORT}")

    async with tcp_server, ws_server:
        await asyncio.gather(tcp_server.serve_forever(), ws_server.wait_closed())

if __name__ == "__main__":
    asyncio.run(main())


# Isso mantém a conexão WebSocket e TCP em paralelo! 🚀
