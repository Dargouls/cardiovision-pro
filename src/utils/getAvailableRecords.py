from pathlib import Path


UPLOAD_DIR = Path('./uploads')

from pathlib import Path

def get_available_records():
  """
  Get a list of available record names in the base directory.
  Only includes files with standard extensions: .hea, .dat, .atr, .xws.
  
  Returns:
      list: Available record names without duplicates
  """
  try:
    # Definir as extensões padrão
    valid_extensions = {'.hea', '.dat', '.atr', '.xws'}
    
    # Obter todos os arquivos correspondentes
    files = [p.stem for p in UPLOAD_DIR.glob('*') if p.suffix in valid_extensions]
    
    # Remover duplicados, mantendo a ordem
    return list(dict.fromkeys(files))
  except Exception as e:
    print(f"Error listing records: {str(e)}")
    return []
