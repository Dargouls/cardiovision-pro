import os

from .clearTempFiles import clear_upload_directory

async def saveTempFiles(UPLOAD_DIR, files):
# Processar os arquivos recebidos e armazena, retornando ordenado pelo arquivo `.hea`
  file_paths = []

  for file in files:
      file_path = os.path.join(UPLOAD_DIR, file.filename)
      with open(file_path, "wb") as f:
          f.write(await file.read())
      file_paths.append(file_path)
  
  print(f'arquivos salvos: {file_paths}')
    # Ordenar os arquivos para garantir que .hea seja o primeiro
  return sorted(file_paths, key=lambda path: (not path.endswith('.hea'), path))
