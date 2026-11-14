"""Convert bundled 26x26 Battle City levels into the existing 13x13 AI format.

The search and game engine are not extended: water becomes steel, grass and ice
become empty. Mixed 2x2 blocks use steel > brick > empty. Source files are read-only.
"""
import argparse
import hashlib
import json
from collections import Counter, deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from game import GameState, HUONG

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'levels'
CONVERTED = ROOT / 'levels_ai'
TANK_POS = ((12, 4), (0, 12))
BASE_POS = ((12, 6), (0, 6))


@dataclass(frozen=True)
class ConvertedLevel:
    layout: tuple
    source_counts: dict

    def state(self):
        return GameState.from_layout(self.layout, tank_pos=TANK_POS)


class OriginalLevelConverter:
    """A conservative 2x2 pool keeps source obstacles on a tank-sized grid."""
    def convert(self, text):
        lines = text.splitlines()
        if len(lines) != 26 or any(len(row) != 26 for row in lines):
            raise ValueError('Map gốc phải có 26 dòng, mỗi dòng 26 ký tự.')
        counts = Counter(''.join(lines))
        unknown = set(counts) - set('.#@~%- ')
        if unknown:
            raise ValueError('Ký tự map gốc không hỗ trợ: ' + repr(sorted(unknown)))
        grid = []
        for row in range(13):
            cells = []
            for col in range(13):
                block = {lines[2*row+dr][2*col+dc] for dr in (0,1) for dc in (0,1)}
                cells.append('S' if block & set('@~') else 'W' if '#' in block else '.')
            grid.append(cells)
        # Do not silently clear walls/steel to make a spawn work.
        for row,col in TANK_POS + BASE_POS:
            if grid[row][col] != '.':
                raise ValueError(f'Vị trí xe/căn cứ bị chặn sau chuyển đổi: {(row,col)}')
        for marker,(row,col) in zip('ab',BASE_POS):
            grid[row][col] = marker
        result = ConvertedLevel(tuple(''.join(row) for row in grid), dict(sorted(counts.items())))
        self.validate_paths(result.state())
        return result

    @staticmethod
    def validate_paths(state):
        # Static reachability permits destructible brick, but not steel or own base.
        for player in (0,1):
            tank,own,enemy = state.tanks[player],state.bases[player],state.bases[1-player]
            goal=(enemy.r,enemy.c)
            seen={(tank.r,tank.c)}
            queue=deque(seen)
            while queue:
                row,col=queue.popleft()
                for dr,dc in HUONG:
                    cell=(row+dr,col+dc)
                    if (cell not in seen and state.in_bounds(*cell) and cell not in state.steel
                            and cell != (own.r,own.c)):
                        seen.add(cell);queue.append(cell)
            if goal not in seen:
                raise ValueError(f'P{player} không có đường qua địa hình tới căn cứ đối thủ.')

    def convert_all(self, source=SOURCE, output=CONVERTED):
        source,output=Path(source),Path(output)
        inputs=sorted((p for p in source.iterdir() if p.is_file() and p.name.isdecimal()),
                      key=lambda p:int(p.name))
        if not inputs:
            raise ValueError('Không tìm thấy file màn chơi đánh số trong thư mục nguồn.')
        if len({int(p.name) for p in inputs}) != len(inputs) or any(int(p.name)<1 for p in inputs):
            raise ValueError('Số màn phải dương và không trùng nhau.')
        # Validate the full batch before writing any of it.
        converted=[]
        for path in inputs:
            try:
                level=self.convert(path.read_text(encoding='utf-8'))
            except ValueError as exc:
                raise ValueError(f'Map gốc {path.name}: {exc}') from exc
            converted.append((path,level))
        output.mkdir(parents=True,exist_ok=True)
        manifest={'format':1,'source_size':[26,26],'target_size':[13,13],
                  'block_size':2,'hash_normalization':'UTF-8 with LF line endings','priority':['steel_or_water','brick','empty'],
                  'mapping':{'#':'W','@':'S','~':'S','%':'.','-':'.','.':'.'},'levels':{}}
        for path,level in converted:
            number=int(path.name)
            name=f'{number:02d}.txt'
            data=('\n'.join(level.layout)+'\n').encode('utf-8')
            (output/name).write_bytes(data)
            manifest['levels'][str(number)]={
                'layout':name,'source':'levels/'+path.name,
                'source_sha256':hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                'layout_sha256':hashlib.sha256(data).hexdigest(),
                'tank_pos':TANK_POS,'base_pos':BASE_POS,'directions':[0,1],
                'source_counts':level.source_counts}
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        return len(converted)


@lru_cache(maxsize=8)
def _manifest(path,modified):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format')!=1:
        raise ValueError('Định dạng manifest levels_ai không hỗ trợ.')
    return data


def _load_manifest(folder):
    path=Path(folder)/'manifest.json'
    return _manifest(str(path.resolve()),path.stat().st_mtime_ns)


def original_map_names(folder=CONVERTED):
    folder=Path(folder)
    if not (folder/'manifest.json').is_file():
        return []
    return [f'original_{n:02d}' for n in sorted(int(k) for k in _load_manifest(folder)['levels'])]


def load_original_level(number,folder=CONVERTED):
    folder=Path(folder)
    record=_load_manifest(folder)['levels'][str(int(number))]
    layout=(folder/record['layout']).read_text(encoding='utf-8').splitlines()
    state=GameState.from_layout(layout,tank_pos=tuple(tuple(p) for p in record['tank_pos']))
    for p,direction in enumerate(record['directions']):
        if direction not in range(4):raise ValueError('Hướng xuất phát phải nằm trong 0..3.')
        state.tanks[p]=state.tanks[p]._replace(d=direction)
    return state


def build_original_maps(folder=CONVERTED):
    return {name:load_original_level(int(name.split('_')[1]),folder) for name in original_map_names(folder)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--convert',action='store_true',help='Convert numbered source levels and write layouts + manifest.')
    parser.add_argument('--source-dir',type=Path,default=SOURCE)
    parser.add_argument('--output-dir',type=Path,default=CONVERTED)
    args=parser.parse_args()
    if args.convert:
        count=OriginalLevelConverter().convert_all(args.source_dir,args.output_dir)
        print(f'Đã chuyển {count} map sang {args.output_dir}')
    else:
        print('\n'.join(original_map_names(args.output_dir)) or 'Chưa có map chuyển đổi. Dùng --convert.')


if __name__=='__main__':main()
