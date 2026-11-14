import os, sys, random, time, tempfile
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0,str(root)); sys.path.insert(0,str(root/'task2'))
from ai_battle import Task2Backend, AIBattle
from arena import ArenaState, NPC_MODES
from game import GameState, Action, Bullet
from benchmark import build_scenarios
import pygame as pg
import tanks
for k in ('players','enemies','bullets','bonuses','labels'):
 setattr(tanks,k,[])
tanks.play_sounds=False; tanks.sounds={}; tanks.gtimer=tanks.Timer()
ui=tanks.Game()
backend=Task2Backend(root/'task2')
random.seed(42)
# All layouts spawn four distinct NPCs. Random legal actions exercise rounds and damage.
for name,base in build_scenarios().items():
 s=ArenaState.from_state(base)
 assert len(set((t.r,t.c) for t in s.tanks))==5
 for _ in range(250):
  if s.is_terminal(): break
  old=s.copy()
  s=s.apply_action(random.choice(s.legal_actions()))
  assert all(t.hp>=0 for t in s.tanks)
  assert old.tanks is not s.tanks
 print('arena map:',name,'PASS')
# Damage is applied to the fifth tank; one NPC death does not finish the match.
s=ArenaState.from_state(GameState.from_layout())
t=s.tanks[4]; s.bullets=[Bullet(t.r+1,t.c,0,0)]
s._advance_bullets(); assert s.tanks[4].hp==5
s.tanks[1]=s.tanks[1]._replace(hp=0)
assert not s.is_terminal()
s.to_move=0;s=s.apply_action(Action.STAY);assert s.to_move==2
for i in range(1,5):s.tanks[i]=s.tanks[i]._replace(hp=0)
assert s.is_terminal() and s.winner()==0
print('damage, skipped dead NPC and team victory: PASS')
# Actual rendering and keyboard event loop with all four search agents.
for human in (True,False):
 battle=AIBattle(ui,tanks.screen,tanks.sprites,human_mode=human)
 battle.depth=[2,2]; battle.speed=5
 assert all(o['kind']!='human' for o in battle.options)
 old=list(battle.sel_agent)
 for row in ('P0','P1'):
  battle._change_row(row,1)
 if human: assert battle.sel_agent==old
 battle._draw_setup(['P0','D0','P1','D1','MAP','START'])
 assert battle._start_match(),battle.setup_msg
 if human:
  assert len(battle.match.state.tanks)==5
  assert [a.mode for a in battle.match.agents[1:]]==list(NPC_MODES)
 else: assert all(a is not None for a in battle.match.agents)
 battle._build_cell_sprites(battle.match.state)
 battle._draw_play(pg.time.get_ticks())
 class TestClock:
  def __init__(self):self.n=0;self.done=False
  def tick(self,fps):
   self.n+=1; pg.time.wait(10)
   if human and battle.match.current_is_human():
    pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_SPACE))
   if battle.match.state.cycle>=2 or self.n>150:
    self.done=True
    pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE))
 battle.clock=TestClock()
 pg.event.clear();battle._play_screen()
 assert not battle.match.error,battle.match.error
 assert battle.match.state.cycle>=2
 if human: assert battle.match.last[0]['action']=='FIRE'
 assert all(info for info in battle.match.last)
 pg.image.save(tanks.screen,str(Path(tempfile.gettempdir()) / ('arena-preview.png' if human else 'ai-preview.png')))
 print('keyboard and 4 NPCs' if human else 'AI vs AI', 'rendered 2 rounds: PASS')
pg.quit()
