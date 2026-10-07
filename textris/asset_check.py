"""기기 재생과 독립적인 배포 음원 목록·무결성 검사."""
from collections import Counter
import hashlib
from importlib import resources
import json
import math
from pathlib import Path, PurePosixPath
from .soundtrack import AssetLibrary

THEMES=('cathedral','cyberpunk','space','fire','crt','mono')
REQUIRED_EFFECTS=frozenset(('ui_move','ui_select','ui_back','ui_toggle','ui_error','countdown','go','pause','resume',
    'move','rotate','hold','drop','lock','clear_single','clear_double','clear_triple','tetris','tspin','all_clear',
    'combo','b2b','fever_start','fever_end','level','danger','win','gameover','boss_hit','boss_break'))


def verify_audio_assets(root=None):
    """파일 decode/청취와 구분되는 package inventory 검증이다."""
    root=root if root is not None else resources.files('textris').joinpath('assets','audio')
    counts={};seen=set();files=set();total_bytes=0;music_seconds=0.;themes=Counter()
    library=AssetLibrary(root,Path.cwd())
    try:
        for catalog,key,count,folder,suffix in (('music.json','tracks',26,'music','.ogg'),
                                                ('sfx.json','effects',30,'sfx','.wav')):
            entries=library._read_catalog(catalog,key)
            if len(entries)!=count:
                raise ValueError(f'{catalog}: expected {count} entries')
            if key=='effects' and {entry['id'] for entry in entries}!=REQUIRED_EFFECTS:
                raise ValueError('effects must cover the thirty required event cue IDs')
            for entry in entries:
                identity=entry['id'];filename=entry['file'];duration=entry['duration']
                if not isinstance(identity,str) or not identity or identity in seen:
                    raise ValueError(f'{catalog}: duplicate/invalid id')
                seen.add(identity)
                if not isinstance(filename,str) or '\\' in filename or ':' in filename:
                    raise ValueError(f'{identity}: unsafe asset path')
                path=PurePosixPath(filename)
                if path.is_absolute() or '..' in path.parts or len(path.parts)!=2 or path.parts[0]!=folder or path.suffix!=suffix:
                    raise ValueError(f'{identity}: unexpected asset path')
                if filename in files:
                    raise ValueError(f'{identity}: duplicate audio file')
                files.add(filename)
                if isinstance(root,Path) and not root.joinpath(*path.parts).resolve().is_relative_to(root.resolve()):
                    raise ValueError(f'{identity}: audio path escapes package')
                if type(duration) not in (int,float) or not math.isfinite(duration):
                    raise ValueError(f'{identity}: invalid duration')
                if key=='tracks':
                    if not 85<=duration<=95 or entry['theme'] not in (*THEMES,'classic'):
                        raise ValueError(f'{identity}: invalid music duration/theme')
                    themes[entry['theme']]+=1;music_seconds+=duration
                elif not 0<duration<=5:
                    raise ValueError(f'{identity}: invalid effect duration')
                content=root.joinpath(*path.parts).read_bytes()
                if not content or hashlib.sha256(content).hexdigest()!=entry['sha256']:
                    raise ValueError(f'{identity}: audio hash mismatch')
                total_bytes+=len(content)
            counts[key]=len(entries)
        if themes!=Counter({**{theme:3 for theme in THEMES},'classic':8}):
            raise ValueError('expected three tracks per theme and eight classics')
    except (OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError(f'audio package unavailable or malformed: {exc}') from exc
    return dict(**counts,bytes=total_bytes,music_seconds=round(music_seconds,3))
