"""Playback follows engine endpoints without changing any simulation input."""
import random
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'task2'))
import game
from game import GameState, Action, Bullet
from presentation import BulletPlayback
from benchmark import build_scenarios
from arena import ArenaState


def board():
    return GameState.from_layout(['      b']+['       ']*5+['a      '],tank_pos=((5,1),(1,5)))


def fingerprint(s):
    return (dict(s.walls),list(s.tanks),list(s.bases),list(s.bullets),s.to_move,s.cycle)


class PlaybackTest(unittest.TestCase):
    def phase(self,state):
        playback=BulletPlayback(game);playback.reset(state)
        half=state.apply_action(Action.STAY)
        playback.observe(state,half,Action.STAY,0,300)
        end=half.apply_action(Action.STAY)
        playback.observe(half,end,Action.STAY,10,300)
        return playback,end

    def test_continuous_motion_across_three_cells(self):
        state=board();state.bullets=[Bullet(4,0,3,0)]
        before=fingerprint(state)
        playback,end=self.phase(state)
        self.assertEqual(playback.positions(10),[(4,0,3)])
        self.assertEqual(playback.positions(60),[(4,.5,3)])
        self.assertEqual(playback.positions(160),[(4,1.5,3)])
        self.assertEqual(playback.positions(310),[(4,3,3)])
        self.assertEqual(fingerprint(state),before)
        # The half turn following a bullet phase must not restart its trajectory.
        next_state=end.apply_action(Action.STAY)
        playback.observe(end,next_state,Action.STAY,310,300)
        self.assertEqual(playback.positions(310),[(4,3,3)])

    def test_removed_bullet_is_visible_until_wall_contact(self):
        state=board();state.walls[(4,2)]=3;state.bullets=[Bullet(4,0,3,0)]
        playback,end=self.phase(state)
        self.assertEqual(end.bullets,[])
        self.assertEqual(playback.state_at(125).walls[(4,2)],3)
        self.assertEqual(playback.positions(135),[(4,1.25,3)])
        self.assertEqual(playback.positions(160),[])
        self.assertEqual(playback.state_at(160).walls[(4,2)],2)
        self.assertEqual(playback.effects[0]['at'],160)
        self.assertEqual(playback.effects[0]['point'],(4,1.5))

    def test_crossing_bullets_meet_visually(self):
        state=board();state.bullets=[Bullet(4,2,3,0),Bullet(4,3,2,1)]
        playback,end=self.phase(state)
        self.assertEqual(playback.positions(35),[(4,2.25,3),(4,2.75,2)])
        self.assertEqual(playback.positions(60),[])
        self.assertTrue(all(e['point']==(4,2.5) for e in playback.effects))
        self.assertEqual(end.bullets,[])

    def test_new_bullet_starts_at_muzzle_and_waits_for_bullet_phase(self):
        state=board();playback=BulletPlayback(game);playback.reset(state)
        child=state.apply_action(Action.FIRE)
        playback.observe(state,child,Action.FIRE,0,300)
        self.assertEqual(playback.positions(0),[(4.65,1,0)])
        self.assertEqual(playback.positions(100),[(4.65,1,0)])
        end=child.apply_action(Action.STAY)
        playback.observe(child,end,Action.STAY,110,300)
        self.assertEqual(playback.positions(110),[(4.65,1,0)])
        self.assertEqual(playback.positions(175),[(4,1,0)])

    def test_replay_matches_engine_on_maps_and_four_npc_extension(self):
        rng=random.Random(20261114)
        count=0
        for name,initial in build_scenarios().items():
            for arena in ((False,) if name.startswith('original_') else (False,True)):
                state=ArenaState.from_state(initial) if arena else initial.copy()
                playback=BulletPlayback(game);playback.reset(state)
                now=0
                for _ in range(80):
                    if state.is_terminal():break
                    before=fingerprint(state)
                    action=rng.choice(state.legal_actions())
                    end=state.apply_action(action)
                    playback.observe(state,end,action,now,300)
                    self.assertEqual(fingerprint(state),before)
                    shown=playback.frames[-1]
                    self.assertEqual(fingerprint(shown),fingerprint(end))
                    self.assertEqual(len(playback.ids),len(end.bullets))
                    state=end;now+=500;count+=1
        self.assertGreater(count,500)


if __name__=='__main__':unittest.main()
