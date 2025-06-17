import tempfile
from pathlib import Path

def get_available_records(UPLOAD_DIR: str):
    """
    Obtém uma lista dos nomes dos registros disponíveis no diretório UPLOAD_DIR.
    Apenas inclui arquivos com as extensões padrão: .hea, .dat, .atr, .xws.
    
    Retorna:
        list: Nomes dos registros (sem duplicatas) baseados no stem dos arquivos.
    """
    try:
        # Converter o caminho temporário de string para Path
        UPLOAD_DIR = Path(UPLOAD_DIR)
        
        # Verificar se é um diretório válido
        if not UPLOAD_DIR.is_dir():
            raise ValueError(f"{UPLOAD_DIR} não é um diretório válido.")
        
        # Definir as extensões padrão
        valid_extensions = {'.hea', '.dat', '.atr', '.xws'}
        
        # Obter os stems dos arquivos com extensão válida
        files = [p.stem for p in UPLOAD_DIR.glob('*') if p.suffix.lower() in valid_extensions]
        
        print('files: ', list(dict.fromkeys(files)))
        # Remover duplicatas mantendo a ordem
        return list(dict.fromkeys(files))
    
    except Exception as e:
        print(f"Error listing records (utils): {str(e)}")
        return []