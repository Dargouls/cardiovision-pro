from pathlib import Path


UPLOAD_DIR = Path('./uploads')

def get_available_records():
  """
  Get a list of available record names in the base directory.
  
  Returns:
      list: Available record names
  """
  try:
    return [p.stem for p in UPLOAD_DIR.glob('*.hea')]
  except Exception as e:
    print(f"Error listing records: {str(e)}")
    return []