"""고정 sleep 대신 관측 가능한 첫 화면을 기다린다."""
import time


def wait_for_startup(terminal,timeout=5.,clock=time.monotonic):
    deadline=clock()+timeout
    while True:
        frame=terminal.screen.text()
        code=terminal.process.poll()
        details=bytes(terminal.raw).decode('utf-8','replace')[-2000:]
        if code is not None:
            raise RuntimeError(f'Terminal exited {code} before first frame: {details}')
        if 'Marathon' in frame or 'Resize terminal' in frame:
            return
        remaining=deadline-clock()
        if remaining<=0:
            raise TimeoutError(f'No initial terminal frame: {details}')
        terminal.pump(min(.05,remaining))
