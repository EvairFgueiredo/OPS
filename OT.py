import asyncio
import websockets

# Dicionário para armazenar conexões pendentes
pending_tunnels = {}

async def handle_connection(websocket, path):
    try:
        init_msg = await websocket.recv()
    except Exception as e:
        print("[OT.py] Erro ao receber mensagem inicial:", e)
        return

    if init_msg.startswith("NOVO_TUNEL:"):
        _, tunnel_id = init_msg.split(":", 1)
        print(f"[OT.py] Recebeu NOVO_TUNEL para {tunnel_id}")

        pair_future = asyncio.get_event_loop().create_future()
        pending_tunnels[tunnel_id] = (websocket, pair_future)

        try:
            partner_ws = await asyncio.wait_for(pair_future, timeout=15)
            await websocket.send("TUNEL_ESTABELECIDO")
            print(f"[OT.py] Túnel {tunnel_id} pareado. Iniciando relay.")
            await relay(websocket, partner_ws)
            print(f"[OT.py] Túnel {tunnel_id} encerrado.")
        except asyncio.TimeoutError:
            print(f"[OT.py] Timeout aguardando pareamento para {tunnel_id}")
            try:
                await websocket.send("ERRO: Timeout no pareamento")
            except Exception as e:
                print(f"[OT.py] Erro ao enviar timeout: {e}")
        except Exception as ex:
            print(f"[OT.py] Exceção durante o pareamento ou relay: {ex}")
        finally:
            pending_tunnels.pop(tunnel_id, None)

    elif init_msg.startswith("CONEXAO_RETORNO:"):
        _, tunnel_id = init_msg.split(":", 1)
        print(f"[OT.py] Recebeu CONEXAO_RETORNO para {tunnel_id}")

        if tunnel_id in pending_tunnels:
            ws_novo, pair_future = pending_tunnels[tunnel_id]
            if not pair_future.done():
                pair_future.set_result(websocket)
                try:
                    await websocket.send("TUNEL_ESTABELECIDO")
                except Exception as e:
                    print(f"[OT.py] Erro ao enviar TUNEL_ESTABELECIDO na conexão de retorno: {e}")
            else:
                await websocket.send("ERRO: Túnel já pareado")
        else:
            await websocket.send("ERRO: Túnel não encontrado")
    else:
        await websocket.send("ERRO: Comando desconhecido")

async def relay(ws1, ws2):
    async def forward(ws_from, ws_to, name):
        try:
            async for message in ws_from:
                await ws_to.send(message)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[Relay {name}] Conexão fechada: {e.code} {e.reason}")
        except Exception as e:
            print(f"[Relay {name}] Erro: {e}")

    await asyncio.gather(
        forward(ws1, ws2, "ws1->ws2"),
        forward(ws2, ws1, "ws2->ws1")
    )

async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 10000):
        print("[OT.py] Servidor ouvindo em wss://<DOMÍNIO>:10000")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
