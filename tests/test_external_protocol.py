import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'task2'))
from ai_battle import Task2Backend, Match


class ExternalProtocolTest(unittest.TestCase):
    def test_import_reset_budget_history_and_action_conversion(self):
        backend=Task2Backend(ROOT/'task2')
        cases=[
            '''from dataclasses import dataclass
@dataclass
class Bot:
    player: int
    def reset(self, player): self.player = player
    def act(self, state, time_limit_ms=None, history=None):
        return 'STAY', dict(budget=time_limit_ms, seen=len(history), player=self.player)
def create_agent(player_id): return Bot(player_id)
''',
            '''def choose_action(state): return 5\n''',
            '''def act(state, time_limit_ms=None, history=None):
    return 'STAY', dict(budget=time_limit_ms, seen=len(history))
''']
        with tempfile.TemporaryDirectory() as folder:
            for i,source in enumerate(cases):
                path=Path(folder)/('external_test_'+str(i)+'.py');path.write_text(source)
                option={'kind':'file','path':str(path),'short':'TEST'}
                bot=backend.create_agent(option,0,2)
                match=Match(backend,backend.new_state('open'),[bot,bot],[option,option],[2,2],time_limit_ms=120)
                match.request_ai_move();match._thread.join(timeout=2)
                self.assertTrue(match.poll(),match.error)
                self.assertEqual(match.last[0]['action'],'STAY')
                if i != 1:
                    self.assertEqual(match.last[0]['budget'],120)
                    self.assertEqual(match.last[0]['seen'],1)

    def test_cycle_draw_consistent_with_ui(self):
        backend=Task2Backend(ROOT/'task2');state=backend.new_state('open')
        state.cycle=state.max_cycles
        match=Match(backend,state,[None,None],[{},{}],[2,2])
        self.assertTrue(match.is_over())
        self.assertEqual(match.result_text()[0],'DRAW')
        self.assertIn('Turn limit',match.result_text()[1])


if __name__=='__main__':unittest.main()
