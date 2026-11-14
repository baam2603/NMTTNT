import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'task2'))
from original_maps import OriginalLevelConverter, load_original_level, original_map_names
from benchmark import build_scenarios
from ai_battle import Task2Backend
from game import TANK_HP, BASE_HP, WALL_HP


class OriginalMapsTest(unittest.TestCase):
    def test_all_saved_layouts_reproduce_sources_and_are_registered(self):
        converter=OriginalLevelConverter()
        manifest=json.loads((ROOT/'levels_ai/manifest.json').read_text())
        names=original_map_names()
        self.assertEqual(names,[f'original_{i:02d}' for i in range(1,36)])
        scenarios=build_scenarios()
        for number in range(1,36):
            with self.subTest(level=number):
                source=ROOT/'levels'/str(number)
                converted=converter.convert(source.read_text())
                record=manifest['levels'][str(number)]
                saved=ROOT/'levels_ai'/record['layout']
                self.assertEqual(tuple(saved.read_text().splitlines()),converted.layout)
                self.assertEqual(hashlib.sha256(source.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),record['source_sha256'])
                self.assertEqual(hashlib.sha256(saved.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),record['layout_sha256'])
                self.assertIn(f'original_{number:02d}',scenarios)
                state=load_original_level(number)
                self.assertEqual((state.rows,state.cols),(13,13))
                self.assertEqual([(t.r,t.c) for t in state.tanks],[(12,4),(0,12)])
                self.assertEqual([(b.r,b.c) for b in state.bases],[(12,6),(0,6)])
                self.assertEqual([t.hp for t in state.tanks],[TANK_HP,TANK_HP])
                self.assertEqual([b.hp for b in state.bases],[BASE_HP,BASE_HP])
                self.assertTrue(all(hp==WALL_HP for hp in state.walls.values()))
                self.assertFalse(state.is_terminal())
                converter.validate_paths(state)

    def test_pool_priority_and_unsupported_terrain_mapping(self):
        grid=[list('.'*26) for _ in range(26)]
        grid[4][4]='#';grid[5][5]='@'  # steel wins a mixed brick/steel block
        grid[6][6]='~'
        grid[8][8]='%';grid[9][9]='-'
        result=OriginalLevelConverter().convert('\n'.join(''.join(r) for r in grid))
        self.assertEqual(result.layout[2][2],'S')
        self.assertEqual(result.layout[3][3],'S')
        self.assertEqual(result.layout[4][4],'.')
        self.assertEqual(result.layout[12][6],'a')
        self.assertEqual(result.layout[0][6],'b')

    def test_invalid_input_and_blocked_spawn_are_rejected(self):
        c=OriginalLevelConverter()
        with self.assertRaises(ValueError):c.convert('.'*26)
        grid=[list('.'*26) for _ in range(26)]
        grid[3][3]='?'
        with self.assertRaises(ValueError):c.convert('\n'.join(''.join(r) for r in grid))
        grid[3][3]='.';grid[24][8]='@'
        with self.assertRaises(ValueError):c.convert('\n'.join(''.join(r) for r in grid))

    def test_exports_are_relocatable_and_states_fresh(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(OriginalLevelConverter().convert_all(ROOT/'levels',folder),35)
            a,b=load_original_level(1,folder),load_original_level(1,folder)
            a.walls.clear()
            self.assertTrue(b.walls)
            self.assertEqual(len(original_map_names(folder)),35)
        backend=Task2Backend(ROOT/'task2')
        self.assertIn('original_35',backend.maps)
        self.assertEqual(backend.new_state('original_35').rows,13)


if __name__=='__main__':unittest.main()
