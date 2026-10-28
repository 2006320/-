from pathlib import Path
from storage import init
from dedup import import_lines,pool_stats
init()
for f in sorted((Path(__file__).parent/'history_seed').glob('*.txt')):
 with f.open(encoding='utf-8-sig',errors='replace') as stream:
  print(f.name,import_lines(stream,f.name))
print('Total unique:',pool_stats()[0])
