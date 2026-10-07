"""플랫폼 속도와 무관하게 PTY 첫 화면을 기다리는 검사 도구 계약."""
import unittest
from types import SimpleNamespace


class TerminalWaitTests(unittest.TestCase):
    def terminal(self,ready_at=1.,exit_code=None):
        state={'now':0.}
        t=SimpleNamespace(raw=b'boot diagnostics')
        t.screen=SimpleNamespace(text=lambda:'Marathon' if state['now']>=ready_at else '')
        t.process=SimpleNamespace(poll=lambda:exit_code)
        t.pump=lambda seconds:state.update(now=state['now']+seconds)
        return t,state

    def test_slow_first_frame_waits_for_observed_menu(self):
        from tests.terminal_wait import wait_for_startup
        t,state=self.terminal(ready_at=.8)
        wait_for_startup(t,clock=lambda:state['now'])
        self.assertGreaterEqual(state['now'],.8)
        self.assertLess(state['now'],1.)

    def test_no_frame_is_bounded_and_diagnostic(self):
        from tests.terminal_wait import wait_for_startup
        t,state=self.terminal(ready_at=9.)
        with self.assertRaisesRegex(TimeoutError,'boot diagnostics'):
            wait_for_startup(t,timeout=.2,clock=lambda:state['now'])

    def test_exit_before_first_frame_is_not_a_success(self):
        from tests.terminal_wait import wait_for_startup
        t,state=self.terminal(exit_code=1)
        with self.assertRaisesRegex(RuntimeError,'exited 1'):
            wait_for_startup(t,clock=lambda:state['now'])

    def test_exited_child_with_menu_text_is_not_ready(self):
        from tests.terminal_wait import wait_for_startup
        t,state=self.terminal(ready_at=0.,exit_code=1)
        with self.assertRaisesRegex(RuntimeError,'exited 1'):
            wait_for_startup(t,clock=lambda:state['now'])
