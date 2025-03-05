import asyncio
import os

OTC_TCP_PORT = 860  # Porta pública para conexões do OTC
LOCAL_TIBIA_PORT = 7171  # Porta local do servidor Tibia

async def handle_tcp_connection(reader, writer):
    print("[OTC] Conexão recebida do cliente OTC.")
    
    try:
        # Conectar ao servidor Tibia local
        tibia_reader, tibia_writer = await asyncio.open_connection('127.0.0.1', LOCAL_TIBIA_PORT)
        print("[Proxy] Conectado ao servidor Tibia local.")
        
        async def client_to_server():
            try:
                while True:
                    data = await reader.read(1024)
                    if not data:
                        break
                    print(f"[OTC → Tibia] Enviando {len(data)} bytes")
                    tibia_writer.write(data)
                    await tibia_writer.drain()
            except Exception as e:
                print("[OTC → Tibia Erro]", e)

        async def server_to_client():
            try:
                while True:
                    data = await tibia_reader.read(1024)
                    if not data:
                        break
                    print(f"[Tibia → OTC] Enviando {len(data)} bytes")
                    writer.write(data)
                    await writer.drain()
            except Exception as e:
                print("[Tibia → OTC Erro]", e)
        
        # Executar ambas as direções simultaneamente
        await asyncio.gather(client_to_server(), server_to_client())
    
    except Exception as e:
        print("[Proxy Erro]", e)
    finally:
        writer.close()
        await writer.wait_closed()
        print("[OTC] Conexão encerrada.")

async def main():
    # Iniciar o servidor TCP
    server = await asyncio.start_server(handle_tcp_connection, "0.0.0.0", OTC_TCP_PORT)
    print(f"[Servidor TCP Público] Rodando na porta {OTC_TCP_PORT}")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())


# O que mudou:
# 1. Removi o WebSocket completamente.
# 2. Agora o proxy apenas conecta a porta pública (860) à porta local (7171).
# 3. As mensagens binárias são encaminhadas diretamente, sem handshake HTTP.

# Próximos passos:
# - Subir isso no Render.
# - Configurar o cliente Tibia para conectar no domínio do Render, porta 860.

# Me avise quando estiver pronto para testar! 🚀
