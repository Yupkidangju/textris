"""Offline FluidSynth/FFmpeg mastering; the game never imports this module."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/".antigravity/audio-overhaul-20261008"
PRODUCTION=ROOT/"assets/audio-production/music"
RUNTIME=ROOT/"textris/assets/audio"

def run(args):
    result=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding="utf-8",errors="replace")
    if result.returncode:raise RuntimeError(result.stderr[-6000:])
    return result

def loudness(path):
    result=run(["ffmpeg","-hide_banner","-nostdin","-i",path,"-af","loudnorm=I=-18:TP=-1.5:LRA=11:print_format=json","-f","null","-"])
    return json.loads(result.stderr[result.stderr.rfind("{"):result.stderr.rfind("}")+1])

def render(track,fluidsynth,soundfont):
    ident=track["id"];outdir=WORK/"production/masters";outdir.mkdir(parents=True,exist_ok=True)
    wav=outdir/(ident+"-raw.wav");flac=outdir/(ident+".flac")
    ogg=RUNTIME/track["file"];ogg.parent.mkdir(parents=True,exist_ok=True)
    run([fluidsynth,"-ni","-r","44100","-g","0.65","-o","synth.reverb.room-size=0.48","-o","synth.reverb.damp=0.45",
         "-o","synth.reverb.level=0.24","-o","synth.chorus.active=0","-F",wav,soundfont,ROOT/track["source_midi"]])
    prepared=outdir/(ident+"-prepared.wav")
    run(["ffmpeg","-hide_banner","-nostdin","-y","-i",wav,"-af","highpass=f=35,lowpass=f=16000,afade=t=in:d=0.025,afade=t=out:st=87.7:d=2.3,apad=whole_dur=90,atrim=duration=90",
         "-ar","44100","-ac","2","-c:a","pcm_s24le",prepared])
    first=loudness(prepared)
    settings=f"loudnorm=I=-18:TP=-1.5:LRA=11:measured_I={first['input_i']}:measured_TP={first['input_tp']}:measured_LRA={first['input_lra']}:measured_thresh={first['input_thresh']}:offset={first['target_offset']}:linear=true"
    run(["ffmpeg","-hide_banner","-nostdin","-y","-i",prepared,"-af",settings,"-ar","44100","-ac","2","-c:a","flac",flac])
    run(["ffmpeg","-hide_banner","-nostdin","-y","-i",flac,"-c:a","libvorbis","-q:a","6","-metadata","title="+track["title"],"-metadata","artist=TEXTRIS contributors",
         "-metadata","copyright="+track["license"],ogg])
    final=loudness(ogg)
    # Analyze the distributed decode rather than relying on encoder input only.
    pcm=run_bytes(["ffmpeg","-v","error","-nostdin","-i",ogg,"-f","f32le","-acodec","pcm_f32le","-"])
    audio=np.frombuffer(pcm,dtype="<f4").reshape(-1,2)
    if not np.isfinite(audio).all():raise ValueError("Nonfinite decode: "+ident)
    duration=len(audio)/44100
    rms=float(np.sqrt(np.mean(audio.astype(np.float64)**2)))
    correlation=float(np.corrcoef(audio[:,0],audio[:,1])[0,1])
    chunks=audio[:len(audio)//4410*4410].reshape(-1,4410,2)
    chunk_rms=np.sqrt(np.mean(chunks.astype(np.float64)**2,axis=(1,2)))
    audible=np.flatnonzero(chunk_rms>10**(-55/20))
    spectrum=np.abs(np.fft.rfft(audio[44100*10:44100*30].mean(axis=1)))**2
    freq=np.fft.rfftfreq(44100*20,1/44100)
    energy=float(spectrum.sum())
    bands={label:round(float(spectrum[(freq>=lo)&(freq<hi)].sum()/energy),6) for label,lo,hi in [("sub",0,80),("low",80,250),("mid",250,2000),("presence",2000,6000),("air",6000,22051)]}
    report=dict(id=ident,duration=duration,sample_rate=44100,channels=2,lufs=float(final["input_i"]),true_peak_dbtp=float(final["input_tp"]),lra=float(final["input_lra"]),
                peak=float(np.max(np.abs(audio))),rms=rms,stereo_correlation=correlation,leading_silence_seconds=float(audible[0]/10),trailing_silence_seconds=float((len(chunk_rms)-1-audible[-1])/10),spectral_energy=bands,
                sha256=hashlib.sha256(ogg.read_bytes()).hexdigest(),master_sha256=hashlib.sha256(flac.read_bytes()).hexdigest(),midi_sha256=hashlib.sha256((ROOT/track["source_midi"]).read_bytes()).hexdigest(),human_listening="not performed")
    if not 85<=duration<=95 or not -19<=report["lufs"]<=-17 or report["true_peak_dbtp"]>-1:
        raise ValueError("Mastering gate: "+str(report))
    if report["leading_silence_seconds"]>1 or report["trailing_silence_seconds"]>3 or correlation<-.15:
        raise ValueError("Signal gate: "+str(report))
    (PRODUCTION/"render-reports").mkdir(parents=True,exist_ok=True)
    (PRODUCTION/"render-reports"/(ident+".json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    track=dict(track,duration=round(duration,6),sha256=report["sha256"])
    print(f"{ident}: {duration:.2f}s {report['lufs']:.2f} LUFS {report['true_peak_dbtp']:.2f} dBTP",flush=True)
    return track,report

def run_bytes(args):
    result=subprocess.run([str(x) for x in args],capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fluidsynth",type=Path,default=next((WORK/"fluidsynth").rglob("fluidsynth.exe"),None))
    parser.add_argument("--soundfont",type=Path,default=WORK/"GeneralUser-GS.sf2")
    parser.add_argument("--only",nargs="*")
    parser.add_argument("--jobs",type=int,default=2)
    args=parser.parse_args()
    pending=json.loads((PRODUCTION/"catalog-pending.json").read_text(encoding="utf-8"))
    tracks=[t for t in pending["tracks"] if not args.only or t["id"] in args.only]
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        results=list(executor.map(lambda t:render(t,args.fluidsynth,args.soundfont),tracks))
    existing={}
    if (RUNTIME/"music.json").exists():existing={t["id"]:t for t in json.loads((RUNTIME/"music.json").read_text(encoding="utf-8"))["tracks"]}
    existing.update({t["id"]:t for t,_ in results})
    ordered=[existing[t["id"]] for t in pending["tracks"] if t["id"] in existing]
    (RUNTIME/"music.json").write_text(json.dumps(dict(version=1,tracks=ordered),indent=2)+"\n",encoding="utf-8")
    print(f"Published {len(ordered)} verified music tracks",flush=True)

if __name__=="__main__":main()
