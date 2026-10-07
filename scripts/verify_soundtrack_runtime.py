"""실제 장치에서 사운드트랙 완주와 혼합을 검사한다. OS 음량은 읽기만 한다."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',choices=('soak','mixed'),default='soak')
    parser.add_argument('--mixed-seconds',type=float,default=600)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    from textris.audio import Audio
    from textris.storage import DEFAULTS
    from textris.windows_audio import EndpointMeter
    meter=EndpointMeter(peak=True)
    settings=dict(DEFAULTS,sound=True,music=True,volume=.5,music_volume=.75,sfx_volume=.85)
    report=dict(started=datetime.now(timezone.utc).isoformat(),mode=args.mode,
                listening_confirmed=False,os_state_before=meter.state(),completed=[],checks={},peak=0.)
    source_paths=[ROOT/'textris'/name for name in ('audio.py','soundtrack.py')]
    source_paths += [ROOT/'textris/assets/audio'/name for name in ('music.json','sfx.json')]
    fingerprint=lambda:{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    report['source_sha256']=fingerprint()
    audio=None
    def save():
        (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    try:
        # 외부 재생기 없이 포함된 decoder/device만 사용한다.
        previous_path=os.environ.get('PATH','');os.environ['PATH']=''
        try: audio=Audio(out/'data',settings)
        finally: os.environ['PATH']=previous_path
        deadline=time.monotonic()+30
        while not audio.catalog and time.monotonic()<deadline:
            time.sleep(.05)
        tracks=list(audio.catalog)
        assert len(tracks)==26,('catalog',len(tracks),audio.music_state)
        playlist=[track['id'] for track in tracks]
        durations={track['id']:track['duration'] for track in tracks}
        audio.audition(playlist[0],playlist=playlist,shuffle=False,repeat=False)
        started=time.monotonic();last_snapshot=started
        seen=Counter();completed_before=audio.diagnostics.get('completed_tracks',0)
        previous_completed=completed_before
        expected_duration=sum(durations.values())
        timeout=expected_duration+120 if args.mode=='soak' else args.mixed_seconds+30
        effects=['move','rotate','hold','drop','lock','clear_single','clear_double','clear_triple',
                 'tetris','tspin','all_clear','combo','b2b','fever_start','fever_end','level',
                 'danger','win','gameover','boss_hit','boss_break','ui_move','ui_select','ui_back',
                 'ui_toggle','ui_error','countdown','go','pause','resume']
        next_effect=started;effect_index=0
        while time.monotonic()-started<timeout:
            now=time.monotonic();state=dict(audio.music_state);stats=dict(audio.diagnostics)
            report['peak']=max(report['peak'],meter.peak())
            count=stats.get('completed_tracks',0)
            if count>previous_completed:
                assert count==previous_completed+1,('missed completion',stats)
                identity=stats['last_completed_track'];seen[identity]+=1
                report['completed'].append(dict(id=identity,wall_seconds=round(now-started,3),
                    expected_duration=durations[identity],diagnostics=stats))
                previous_completed=count
                print(json.dumps(dict(event='completed',track=identity,count=len(report['completed']),
                                      wall_seconds=round(now-started,2))),flush=True)
                save()
            if args.mode=='soak' and len(report['completed'])==26:
                audio.pause_audition(True)
                report['checks']['all_tracks_once']=seen==Counter(playlist)
                report['checks']['normal_wall_clock']=now-started>=expected_duration-1
                break
            if args.mode=='mixed' and now>=next_effect:
                # 입력 빈도보다 높은 부하에서도 voice 상한과 큐를 검사한다.
                audio.play(effects[effect_index%len(effects)])
                effect_index+=1;next_effect=now+.065
                if now-started>=args.mixed_seconds:
                    report['checks']['mixed_elapsed']=True
                    report['mixed_requests']=effect_index
                    break
            assert stats.get('active_voices',0)<=6,('voice limit',stats)
            assert stats.get('worker_alive',True),('worker exited',stats)
            if now-last_snapshot>=5:
                report.update(elapsed_seconds=round(now-started,3),music_state=state,diagnostics=stats)
                save();last_snapshot=now
            time.sleep(.04)
        else:
            raise AssertionError(('playback timeout',audio.music_state,audio.diagnostics))
        report.update(elapsed_seconds=round(time.monotonic()-started,3),music_state=dict(audio.music_state),
                      diagnostics=dict(audio.diagnostics))
        # 완료 카운터는 callback 제출까지의 증거다. 마지막 장치 버퍼도 소진시킨다.
        audio.pause_audition(True)
        time.sleep(.2)
        report['final_device_drain_seconds']=.2
        audio.close()
        final=dict(audio.diagnostics)
        report['closed_diagnostics']=final
        report['checks']['worker_closed']=not final.get('worker_alive',True)
        report['checks']['signal_observed']=report['peak']>.001
        report['checks']['os_state_unchanged']=meter.state()==report['os_state_before']
        report['checks']['no_device_failures']=final.get('failure_count',0)==0
        report['checks']['source_unchanged']=fingerprint()==report['source_sha256']
        report['checks']['no_output_clipping']=final.get('clipped_samples',0)==0
        report['passed']=all(report['checks'].values())
        assert report['passed'],report['checks']
    except BaseException as exc:
        report['passed']=False;report['error']=repr(exc)
        raise
    finally:
        if audio is not None: audio.close()
        meter.close();save()
    print(json.dumps(dict(passed=True,output=str(out),elapsed=report['elapsed_seconds'])),flush=True)


if __name__=='__main__':main()
