"""Headless Pygame smoke test for imported levels and keyboard map navigation."""
import os
import sys
import tempfile
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
import tanks
import pygame as pg
from ai_battle import AIBattle

for name in ('players','enemies','bullets','bonuses','labels'):setattr(tanks,name,[])
tanks.play_sounds=False;tanks.sounds={};tanks.gtimer=tanks.Timer()
ui=tanks.Game();battle=AIBattle(ui,tanks.screen,tanks.sprites)
assert len([n for n in battle.backend.maps if n.startswith('original_')])==35
battle.row=4
class NavigationClock:
    def __init__(self):self.index=0;self.expected=None
    def tick(self,fps):
        if self.expected is not None:
            assert battle.backend.maps[battle.sel_map]==self.expected
        commands=[(pg.K_o,'original_01'),(pg.K_PAGEDOWN,'original_06'),
                  (pg.K_END,'original_35'),(pg.K_HOME,'default'),
                  (pg.K_o,'original_01'),(pg.K_RETURN,'original_01')]
        key,self.expected=commands[self.index]
        self.index+=1
        pg.event.post(pg.event.Event(pg.KEYDOWN,key=key))
battle.clock=NavigationClock();pg.event.clear()
assert battle._setup_screen()
for number in (1,19,35):
    battle.sel_map=battle.backend.maps.index(f'original_{number:02d}')
    assert battle._start_match(),battle.setup_msg
    assert len(battle.match.state.tanks)==2
    assert battle.match.state.rows==13
    battle._build_cell_sprites(battle.match.state)
    battle._draw_play(pg.time.get_ticks())
    pg.image.save(tanks.screen,str(Path(tempfile.gettempdir())/f'original-{number:02d}.png'))
human=AIBattle(ui,tanks.screen,tanks.sprites,human_mode=True)
assert not any(n.startswith('original_') for n in human.backend.maps)
print('35 original maps registered; O/Page/Home/End navigation and LV01/LV19/LV35 rendering: PASS')
print('Imported originals remain scoped to two-AI mode: PASS')
pg.quit()
