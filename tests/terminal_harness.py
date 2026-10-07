"""실제 curses 프로세스용 PTY와 ANSI 화면 재구성(표준 라이브러리만 사용)."""
import codecs
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unicodedata


class Screen:
    def __init__(self, rows, cols):
        self.rows,self.cols=rows,cols
        self.grid=[[' ']*cols for _ in range(rows)]
        self.x=self.y=0
        self.pending=''
        self.decoder=codecs.getincrementaldecoder('utf-8')('replace')

    def feed(self,data):
        self.pending+=self.decoder.decode(data)
        s=self.pending; i=0
        while i<len(s):
            c=s[i]
            if c=='\x1b':
                if i+1>=len(s): break
                if s[i+1]=='[':
                    m=re.match(r'\x1b\[([0-?]*)([ -/]*)([@-~])',s[i:])
                    if not m: break
                    self.csi(m[1],m[3]); i+=len(m[0]); continue
                if s[i+1] in '()':
                    if i+2>=len(s): break
                    i+=3; continue
                if s[i+1]==']':
                    m=re.search(r'\x07|\x1b\\',s[i+2:])
                    if not m: break
                    i+=2+m.end(); continue
                i+=2; continue
            if c=='\r': self.x=0
            elif c=='\n': self.y=min(self.rows-1,self.y+1)
            elif c=='\b': self.x=max(0,self.x-1)
            elif ord(c)>=32:
                w=0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W','F') else 1
                if w and 0<=self.y<self.rows and 0<=self.x<self.cols:
                    self.grid[self.y][self.x]=c
                    if w==2 and self.x+1<self.cols: self.grid[self.y][self.x+1]=''
                self.x+=w
            i+=1
        self.pending=s[i:]

    def csi(self,params,op):
        if params.startswith('?'): return
        a=[int(p) if p.isdigit() else 0 for p in params.split(';')]
        n=a[0] or 1
        if op in 'Hf': self.y=(a[0] or 1)-1; self.x=(a[1] or 1)-1 if len(a)>1 else 0
        elif op=='d': self.y=n-1
        elif op=='G': self.x=n-1
        elif op=='A': self.y=max(0,self.y-n)
        elif op=='B': self.y=min(self.rows-1,self.y+n)
        elif op=='C': self.x=min(self.cols-1,self.x+n)
        elif op=='D': self.x=max(0,self.x-n)
        elif op=='J':
            if a[0] in (2,3): self.grid=[[' ']*self.cols for _ in range(self.rows)]
            elif a[0]==0:
                self.grid[self.y][self.x:]=[' ']*(self.cols-self.x)
                for y in range(self.y+1,self.rows): self.grid[y]=[' ']*self.cols
        elif op=='K':
            if a[0]==2: self.grid[self.y]=[' ']*self.cols
            elif a[0]==0: self.grid[self.y][self.x:]=[' ']*(self.cols-self.x)
            else: self.grid[self.y][:self.x+1]=[' ']*(self.x+1)
        elif op=='X':
            end=min(self.cols,self.x+n); self.grid[self.y][self.x:end]=[' ']*(end-self.x)
        elif op=='P':
            row=self.grid[self.y]; self.grid[self.y]=row[:self.x]+row[self.x+n:]+[' ']*min(n,self.cols-self.x)
        elif op=='@':
            row=self.grid[self.y]; self.grid[self.y]=(row[:self.x]+[' ']*n+row[self.x:])[:self.cols]

    def text(self): return '\n'.join(''.join(r) for r in self.grid)


class Terminal:
    def __init__(self,directory,arguments=(),rows=32,cols=90):
        self.master,self.slave=pty.openpty()
        self.original=termios.tcgetattr(self.slave)
        fcntl.ioctl(self.slave,termios.TIOCSWINSZ,struct.pack('HHHH',rows,cols,0,0))
        self.screen=Screen(rows,cols)
        self.raw=bytearray()
        env=dict(os.environ,TERM='xterm-256color',LC_ALL='C.UTF-8')
        self.process=subprocess.Popen([sys.executable,'-m','textris','--data-dir',str(directory),*arguments],
            stdin=self.slave,stdout=self.slave,stderr=self.slave,env=env,
            cwd=Path(__file__).resolve().parent.parent,start_new_session=True)
        self.pump(.35)

    def pump(self,seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            readable,_,_=select.select([self.master],[],[],min(.03,max(0,deadline-time.monotonic())))
            if readable:
                try: data=os.read(self.master,65536)
                except OSError: break
                if not data: break
                self.raw.extend(data); self.screen.feed(data)

    def send(self,keys,wait=.18):
        os.write(self.master,keys.encode() if isinstance(keys,str) else keys)
        self.pump(wait)

    def resize(self,rows,cols):
        fcntl.ioctl(self.slave,termios.TIOCSWINSZ,struct.pack('HHHH',rows,cols,0,0))
        self.screen=Screen(rows,cols)
        self.process.send_signal(signal.SIGWINCH)
        self.pump(.3)

    def close(self):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try: self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=3)
        self.pump(.05)
        os.close(self.master); os.close(self.slave)
