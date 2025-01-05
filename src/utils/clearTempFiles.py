import os
import shutil

def clear_upload_directory(upload_dir: str):
  """
  Remove todos os arquivos da pasta especificada.

  Args:
      upload_dir (str): Caminho para o diretório de uploads.
  """
  try:
      if not os.path.exists(upload_dir):
          print(f"Diretório {upload_dir} não existe.")
          return

      # Itera pelos arquivos e remove
      for file_name in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, file_name)
        if os.path.isfile(file_path):
          os.remove(file_path)
          print(f"Arquivo removido: {file_path}")
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
            print(f"Subdiretório removido: {file_path}")

      print(f"Todos os arquivos foram removidos de {upload_dir}.")
  except Exception as e:
      print(f"Erro ao limpar o diretório: {str(e)}")
