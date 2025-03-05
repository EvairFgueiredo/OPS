import asyncio
import websockets

WEB_SOCKET_PORT = 10000
TCP_SERVER_HOST = '127.0.0.1'
TCP_SERVER_PORT = 7171
OTC_TCP_PORT = 860  # Porta para o OTC se conectar

async def bridge(websocket, tcp_reader, tcp_writer):
    async def ws_to_tcp():
        try:
            async for data in websocket:
                print(f"[WS → TCP] Enviando {len(data)} bytes: {data.hex()}")
                tcp_writer.write(data)
                await tcp_writer.drain()
        except Exception as e:
            print("[WS → TCP Erro]", e)

    async def tcp_to_ws():
        try:
            while True:
                # Lê o header do pacote (2 bytes indicando o tamanho)
                header = await tcp_reader.read(2)
                if len(header) < 2:
                    break
                size = int.from_bytes(header, byteorder='little')
                # Lê o restante do pacote
                data = await tcp_reader.read(size)
                packet = header + data
                print(f"[TCP → WS] Recebido {len(packet)} bytes: {packet.hex()}")
                await websocket.send(packet)
        except Exception as e:
            print("[TCP → WS Erro]", e)

    await asyncio.gather(ws_to_tcp(), tcp_to_ws())

async def handle_otc_connection(reader, writer):
    print("[Nova Conexão OTC]")
    try:
        # Conecta ao servidor WebSocket (ponte)
        async with websockets.connect(f"ws://{TCP_SERVER_HOST}:{WEB_SOCKET_PORT}") as websocket:
            print("[Conectado ao WebSocket]")
            await bridge(websocket, reader, writer)
    except Exception as e:
        print("[Erro OTC]", e)
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_ws_connection(websocket, path):
    print(f"[Nova Conexão WebSocket] {websocket.remote_address}")
    try:
        # Conecta ao servidor Open Tibia
        tcp_reader, tcp_writer = await asyncio.open_connection(TCP_SERVER_HOST, TCP_SERVER_PORT)
        print("[Conectado ao Open Tibia Server]")
        await bridge(websocket, tcp_reader, tcp_writer)
    except Exception as e:
        print("[Erro WebSocket]", e)
    finally:
        await websocket.close()

async def main():
    # Servidor TCP para o OTC (cliente)
    tcp_server = await asyncio.start_server(handle_otc_connection, "0.0.0.0", OTC_TCP_PORT)
    print(f"[Servidor TCP para OTC] Porta {OTC_TCP_PORT}")

    # Servidor WebSocket (ponte)
    async with websockets.serve(handle_ws_connection, "0.0.0.0", WEB_SOCKET_PORT):
        print(f"[Servidor WebSocket] Porta {WEB_SOCKET_PORT}")
        await tcp_server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())