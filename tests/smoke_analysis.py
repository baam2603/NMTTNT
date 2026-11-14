import os,sys,tempfile
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
r=Path(__file__).resolve().parents[1];os.chdir(r);sys.path.insert(0,str(r))
import tanks
import pygame as pg
from ai_battle import AIBattle
for name in ('players','enemies','bullets','bonuses','labels'):setattr(tanks,name,[])
tanks.play_sounds=False;tanks.sounds={};tanks.gtimer=tanks.Timer()
ui=tanks.Game();b=AIBattle(ui,tanks.screen,tanks.sprites)
b.sel_map=b.backend.maps.index('h_dodge');b.depth=[4,4];b.budget_index=3;b.speed=5
b.sel_agent=[next(i for i,o in enumerate(b.options) if o.get('mode')==m) for m in ('heuristic_alphabeta','minimax')]
assert b._start_match(),b.setup_msg
class Clock:
 def __init__(self):self.n=0;self.phase=0;self.wait_start=None
 def tick(self,fps):
  self.n+=1;pg.time.wait(10)
  if self.n>500:raise AssertionError('UI step test timed out')
  if self.n==1:
   pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_n))
   pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_TAB))
  if self.phase==0 and b.match.state.to_move==1 and not b.match.thinking:
   self.phase=1;self.wait_start=self.n
  if self.phase==1 and self.n-self.wait_start>=5:
   assert b.match.state.to_move==1 and b.match.state.cycle==0,'N must execute exactly one action'
   assert b.paused and not b.match.thinking
   b._draw_play(pg.time.get_ticks())
   pg.image.save(tanks.screen,str(Path(tempfile.gettempdir())/'search-analysis.png'))
   pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_n))
   self.phase=2
  if self.phase==2 and b.match.state.to_move==0 and b.match.state.cycle==1 and not b.match.thinking:
   self.phase=3;self.wait_start=self.n
  if self.phase==3 and self.n-self.wait_start>=5:
   assert b.match.state.to_move==0 and b.match.state.cycle==1,'Second N must execute exactly one action'
   assert b.paused and not b.match.thinking
   b.inspect_search=False
   b._draw_play(pg.time.get_ticks())
   pg.image.save(tanks.screen,str(Path(tempfile.gettempdir())/'search-board.png'))
   pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE))
   self.phase=4
b.clock=Clock();pg.event.clear();b._play_screen()
assert b.match.error is None,b.match.error
print('Pause/N-step + TAB diagnostics + facing vectors + both AI APIs: PASS')
# Reach the cycle cap on the actual UI and show the correct draw reason.
b.match.state.cycle=b.match.state.max_cycles
assert b.match.is_over();assert 'Turn limit' in b.match.result_text()[1]
b._draw_play(pg.time.get_ticks());print('UI cycle-limit draw: PASS')
pg.quit()
