import wfdb

import asyncio
import copy

wfdb_lock = asyncio.Lock()
#Criar cópia de wfdb record baseada no base_path disponibilizado e disponibilizar a cópia na função

async def copy_record(base_path):
  try:
    async with wfdb_lock:
      record = copy.deepcopy(wfdb.rdrecord(base_path))
      return record
  except Exception as e:
    print(f"Erro ao tentar carregar o arquivo: {e}")