async def worker(queue, client):
    while True:
        url, files = await queue.get()
        try:
            response = await client.post(url, files=files)
            response.raise_for_status()  # Levanta exceção se houver erro
            print(f"Requisição enviada com sucesso para {url}")
        except Exception as e:
            print(f"Erro ao enviar: {e}")
        finally:
            queue.task_done()  # Marca a tarefa como concluída