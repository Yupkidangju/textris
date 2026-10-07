"""Rebuild authored four-part scores and MIDI; no random note generation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import mido

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "assets/audio-production/music"
RUNTIME = ROOT / "textris/assets/audio"
TPB = 480
CHANNELS = (0, 1, 2, 9)
ROLES = ("lead", "harmony", "bass", "drums")

# Every phrase below is authored, in scale degrees; ':' gives quarter-note duration.
# Bare scale degrees last half a beat. Each bar is checked against its meter.
ORIGINALS = [
 ("cathedral_vault", "Vault of Light", "cathedral", "Dm", 4, 32,
  "1:1 3 5 4:1 3:1|5:1 6 5 3:1 2:1|4:1 6 8 7:1 6:1|5:2 3:1 2:1|1 3 5:1 8:1 7:1|6:1 5 4 3:2|2 3 4:1 5 4 2:1|1:3 r:1",
  "6:1 8 7 6:1 5:1|4 6 8:1 9:1 8:1|7:1 5 3 4:1 6:1|5:3 r:1|8:1 7 6 5:1 3:1|4:1 2 4 6:2|5 6 5 4 3:1 2:1|1:4",
  "Dm Bb F C Dm Bb Gm A", "Bb F C Dm Gm Dm A A"),
 ("cathedral_rose", "Rose Window", "cathedral", "Gm", 3, 40,
  "5:1 6 5 3:1|4:1 2:1 1:1|3 4 5:1 8:1|7:2 5:1|6:1 8 7 6:1|5:1 3:1 2:1|4 3 2:1 7-:1|1:3",
  "8:1 9 8 6:1|7:1 5:1 4:1|6 5 4:1 2:1|3:3|5:1 8 7 6:1|4:1 6:1 8:1|7 6 5:1 2:1|1:3",
  "Gm Eb Bb F Gm Cm D D", "Eb Bb Cm Gm Eb Cm D Gm"),
 ("cathedral_orbits", "Celestial Procession", "cathedral", "Em", 4, 36,
  "1:1 5:1 8:1 7:1|6:1 3:1 4 5 6:1|5:1 2:1 3:1 4:1|2:2 7-:2|1 2 3:1 5:1 8:1|7:1 6 5 4:1 3:1|2:1 4:1 7:1 5:1|1:4",
  "3:2 6:1 8:1|9:1 8:1 7 6 5:1|4:2 6:1 5:1|3:3 2:1|6:1 5 4 3:1 2:1|4:1 6:1 8:2|7 8 7 6 5:1 2:1|1:4",
  "Em C G D Em C Am B", "C G Am Em C Am B Em"),
 ("cyberpunk_neon", "Neon Lattice", "cyberpunk", "Fm", 4, 48,
  "1 .5r 5 1 3:1 2 1|6- 1 3 5 6:1 5 3|4 .5r 6 8 7 6 4 2|5:1 4 3 2:1 7-:1|1 3 5 8 7 .5r 5 3|6 5 3 1 6-:1 1 3|4 6 8 6 5 4 2 7-|1:2 r:1 5-:1",
  "8 .5r 7 5 6:1 8 9|10 9 8 6 5 .5r 3 5|6 8 9 8 7 5 4 2|3:1 5 7 8:2|6 .5r 4 2 3 4 6 8|5 3 1 3 6 5 4 3|2 .5r 7- 2 5 4 3 2|1:3 r:1",
  "Fm Db Ab Eb Fm Db Bbm C", "Db Ab Bbm Fm Db Bbm C Fm"),
 ("cyberpunk_pursuit", "Chrome Pursuit", "cyberpunk", "Bm", 4, 48,
  "1 1 3 .5r 5 4 3 2|1:1 7- 1 3 .5r 5 6|5 5 7 5 4 3 2 1|2:1 4:1 7-:2|3 2 1 3 5 8 7 5|6 6 5 3 1 3 4 6|5 4 2 5 7 6 4 2|1:2 5-:1 r:1",
  "6:1 8 9 10 9 8 6|5 3 5 7 8:1 7 5|4 6 4 2 1 2 4 6|3:1 5:1 8:2|9 8 6 5 4 6 8 6|5 3 1 3 5 7 8 7|6 4 2 4 7 5 3 2|1:4",
  "Bm G D A Bm G Em F#", "G D Em Bm G Em F# Bm"),
 ("cyberpunk_midnight", "Midnight Circuit", "cyberpunk", "Cm", 4, 44,
  "5:1 1 3 5 .5r 4 3|6:1 5 3 1 .5r 2 3|4:1 6 8 7 6 5 4|2:2 7-:1 r:1|1 2 3 5 8:1 7 5|6:1 4 3 1:1 3 5|4 6 5 4 2:1 7-:1|1:3 r:1",
  "8:1 10 9 8:1 6:1|7 5 3 5 7:1 8:1|6 4 2 4 6:1 7:1|5:2 3:1 r:1|9 8 7 6 5:1 3:1|4:1 6:1 8 7 6 4|5 4 3 2 7-:1 2:1|1:4",
  "Cm Ab Eb Bb Cm Ab Fm G", "Ab Eb Fm Cm Ab Fm G Cm"),
 ("space_orbit", "Quiet Orbit", "space", "D", 4, 32,
  "1:2 5:1 3:1|2:1 3 5 6:2|5:1 3:1 2:1 1:1|7-:3 r:1|3:2 5:1 8:1|7:1 6:1 5:2|4:1 3:1 2:2|1:4",
  "6:2 8:1 9:1|8:1 7:1 5:2|4:2 6:1 5:1|3:3 r:1|8:1 7 6 5:2|6:1 4:1 2:2|3:1 2:1 7-:1 5-:1|1:4",
  "D Bm G A D Bm Em A", "G D Em Bm G Em A D"),
 ("space_nebula", "Nebula Lanterns", "space", "Am", 3, 36,
  "1:1 3:1 5:1|6:2 5:1|4:1 6 5 3:1|2:3|3:1 5:1 8:1|7:1 6:1 5:1|4:1 2:1 7-:1|1:3",
  "8:2 9:1|10:1 9:1 8:1|6:1 4:1 2:1|3:3|5 6 8:1 7:1|6:1 5:1 4:1|2:1 3:1 7-:1|1:3",
  "Am F C G Am F Dm E", "F C Dm Am F Dm E Am"),
 ("space_starlight", "Starlight Transit", "space", "E", 4, 32,
  "5:1 8:1 7 6 5:1|3:2 2:1 1:1|4:1 6:1 8:2|7:2 5:1 r:1|1:1 3 5 6:1 8:1|7:1 5:1 3:2|4 3 2:1 7-:1 5-:1|1:4",
  "6:1 8:1 10:2|9:1 8:1 7:2|4:1 5 6 8:1 6:1|5:3 r:1|8:2 7 6 5:1|6:1 4:1 3:1 2:1|3 4 2:1 7-:2|1:4",
  "E C#m A B E C#m F#m B", "A E F#m C#m A F#m B E"),
 ("fire_ember", "Ember Foundry", "fire", "Dm", 4, 40,
  "1:1 1 3 5:1 4 3|6-:1 1 3 6:1 5 3|4 4 6 8 7:1 6 4|5:1 4 3 2:2|1 3 5 3 8:1 7 5|6:1 5 3 4:1 3 1|2 4 5 7 5 4 3 2|1:4",
  "8:1 8 7 6:1 5 4|5:1 3 5 8:1 7 5|6 4 6 8 9:1 8 6|5:2 3:1 r:1|6:1 8 10 9:1 8 6|4 6 8 6 5:1 4 3|2 3 4 5 7 5 3 2|1:4",
  "Dm Bb F C Dm Bb Gm A", "Bb F Gm Dm Bb Gm A Dm"),
 ("fire_furnace", "Furnace Heart", "fire", "Em", 4, 44,
  "1 5 1 3 5:1 3 2|1 6- 1 3 6:1 5 3|4 8 4 6 7:1 6 4|2 5 2 4 7-:2|3 5 8 7 5 3 2 1|6 8 6 5 3 1 3 4|2 4 7 5 4 2 7- 2|1:3 r:1",
  "6 8 10 9 8:1 6 5|5 7 8 7 5:1 3 2|4 6 9 8 6 4 2 4|3:1 5:1 8:2|9 8 7 6 5 4 3 2|6 4 2 4 8 6 5 4|7 5 4 2 3 2 7- 2|1:4",
  "Em C G D Em C Am B", "C G Am Em C Am B Em"),
 ("fire_solar", "Solar Breaker", "fire", "Gm", 4, 40,
  "5:1 8 7 5:1 3:1|6:1 8 6 5:1 3:1|4 6 8:1 7 6 4:1|2:1 4:1 7-:2|1 3 5 8 7:1 5:1|6 5 3 1 4:1 6:1|5 4 2 4 7:1 2:1|1:4",
  "8:2 10 9 8:1|7:1 5:1 3 5 8:1|6:1 9:1 8 6 4:1|5:3 r:1|6 8 9 10 9:1 8:1|6:1 4:1 2 4 6:1|7 8 7 5 4 3 2 7-|1:4",
  "Gm Eb Bb F Gm Eb Cm D", "Eb Bb Cm Gm Eb Cm D Gm"),
 ("crt_arcade", "After Hours Arcade", "crt", "A", 4, 44,
  "1 3 5 3 8:1 5 3|6 5 3 1 2:1 3 5|4 6 8 6 5 4 3 2|5:1 2:1 7-:2|3 5 8 7 6:1 5 3|6 8 6 5 3:1 2 1|2 4 6 5 4 2 7- 2|1:3 r:1",
  "8 9 10 8 6:1 8 9|7 8 9 7 5:1 3 5|6 8 9 6 4:1 2 4|3:1 5:1 8:2|10 9 8 6 5:1 3 5|6 5 4 2 4:1 6 8|7 6 5 4 3 2 7- 2|1:4",
  "A F#m D E A F#m Bm E", "D A Bm F#m D Bm E A"),
 ("crt_scanline", "Scanline Carousel", "crt", "Cm", 3, 48,
  "1 3 5:1 8:1|7 5 3:1 2:1|4 6 8:1 6:1|5:2 2:1|3 5 8:1 7:1|6 5 4:1 3:1|2 4 7:1 5:1|1:3",
  "6 8 10:1 9:1|8 7 5:1 3:1|4 6 9:1 8:1|5:3|8 7 6:1 5:1|4 6 8:1 6:1|7 5 4:1 2:1|1:3",
  "Cm Ab Eb Bb Cm Ab Fm G", "Ab Eb Fm Cm Ab Fm G Cm"),
 ("crt_radio", "Phosphor Radio", "crt", "F", 4, 40,
  "3:1 5 6 5:1 3:1|1 2 3:1 6:1 5:1|4:1 6 8 7:1 6:1|5:2 2:1 r:1|1 3 5:1 8 7 6:1|5:1 3 1 2:1 3:1|4 6 5 4 2:1 7-:1|1:4",
  "6:1 8 9 10:1 9:1|8:1 7 5 3:2|4 6 8:1 9 8 6:1|5:3 r:1|8:1 9 8 6:1 5:1|4:1 2 4 6:2|5 4 3 2 7-:1 2:1|1:4",
  "F Dm Bb C F Dm Gm C", "Bb F Gm Dm Bb Gm C F"),
 ("mono_geometry", "Paper Geometry", "mono", "C", 4, 32,
  "1:1 3:1 2 3 5:1|6:1 5:1 3:2|4:1 6:1 5 4 2:1|3:2 2:1 r:1|5:1 8:1 7 6 5:1|6:1 4:1 3:2|2:1 4:1 7-:2|1:4",
  "3:1 6:1 8:2|7:1 5:1 3:2|4:1 2:1 6:1 5:1|3:3 r:1|8:1 7 6 5:1 3:1|4:1 6:1 8:2|7 6 5 4 3:1 2:1|1:4",
  "C Am F G C Am Dm G", "F C Dm Am F Dm G C"),
 ("mono_nocturne", "Graphite Nocturne", "mono", "Bm", 3, 36,
  "3:1 2 1 5-:1|6-:1 1:1 3:1|4:1 6:1 5:1|2:3|1:1 3 5 8:1|7:1 5:1 3:1|2:1 4:1 7-:1|1:3",
  "6:2 8:1|9:1 8:1 5:1|4 5 6:1 8:1|5:3|8:1 7:1 6:1|4:1 2:1 3:1|5 4 3:1 2:1|1:3",
  "Bm G D A Bm G Em F#", "G D Em Bm G Em F# Bm"),
 ("mono_etching", "Silver Etching", "mono", "Eb", 4, 36,
  "5:1 3:1 1 2 3:1|6:1 5 3 2:2|4:1 6:1 8 7 6:1|5:3 r:1|1:1 3 5 8:1 7:1|6 5 3:1 4:1 3:1|2:1 4:1 7-:1 2:1|1:4",
  "8:1 6:1 3 5 6:1|7:1 5 3 2:2|4 6 8:1 9:1 8:1|5:3 r:1|10:1 9:1 8 7 6:1|4:1 2:1 6 5 4:1|3 4 2:1 7-:2|1:4",
  "Eb Cm Ab Bb Eb Cm Fm Bb", "Ab Eb Fm Cm Ab Fm Bb Eb"),
]

ENSEMBLES = {
 "cathedral": ([19,48,43,48],["Church Organ","String Ensemble","Contrabass","Orchestral Percussion"]),
 "cyberpunk": ([81,89,38,24],["Saw Lead","Warm Synth Pad","Synth Bass","Electronic Kit"]),
 "space": ([88,89,39,0],["New Age Lead","Warm Pad","Round Synth Bass","Light Percussion"]),
 "fire": ([61,29,34,0],["Brass Section","Overdriven Guitar","Electric Bass","Tight Rock Kit"]),
 "crt": ([80,4,38,24],["Square Lead","Electric Piano","Synth Bass","Electronic Kit"]),
 "mono": ([0,48,32,40],["Grand Piano","Soft Strings","Acoustic Bass","Brush Kit"]),
}
PITCH = {"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}

def note_number(name: str) -> int:
    match = re.fullmatch(r"([A-G][#b]?)(-?\d+)", name)
    if not match:
        raise ValueError(name)
    pitch=PITCH.get(match[1])
    if pitch is None:
        pitch=PITCH[match[1][0]]+(1 if match[1][1:]=="#" else -1)
    return (int(match[2])+1)*12+pitch

def degree(number: int, key: str) -> int:
    minor=key.endswith("m")
    root=PITCH[key[:-1] if minor else key]+60
    scale=(0,2,3,5,7,8,10) if minor else (0,2,4,5,7,9,11)
    octave,index=divmod(number-1,7)
    return root+12*octave+scale[index]

def parse_phrase(text: str, key: str, meter: int, *, absolute=False):
    notes=[]
    for bar,line in enumerate(text.split("|")):
        position=0.0
        for token in line.split():
            if token==".5r":token="r:0.5"
            value,_,length=token.partition(":")
            duration=float(length) if length else .5
            if value!="r":
                if absolute:pitch=note_number(value)
                else:pitch=degree(int(value.rstrip("-"))-7*value.endswith("-"),key)
                notes.append((bar*meter+position,duration,pitch))
            position+=duration
        if abs(position-meter)>1e-6:raise ValueError(f"{key}: bar {bar+1} is {position}, wanted {meter}: {line}")
    return notes

def chord_notes(name: str):
    minor=name.endswith("m")
    root=PITCH[name[:-1] if minor else name]
    return [root+48,root+48+(3 if minor else 4),root+55]

def source_notes(path: Path, track: int):
    midi=mido.MidiFile(path)
    tick=0;active={};notes=[]
    for msg in midi.tracks[track]:
        tick+=msg.time
        if msg.type=="note_on" and msg.velocity:
            active.setdefault(msg.note,[]).append(tick)
        elif msg.type=="note_off" or (msg.type=="note_on" and not msg.velocity):
            if active.get(msg.note):
                start=active[msg.note].pop(0)
                notes.append((start/midi.ticks_per_beat,(tick-start)/midi.ticks_per_beat,msg.note))
    if any(active.values()):raise ValueError(f"Dangling source notes: {path}")
    return sorted(notes)

def add(score, role, beat, duration, pitch, velocity):
    if duration<=0:return
    score[role].append({"beat":round(beat,6),"duration":round(duration,6),"pitch":int(pitch),"velocity":int(max(1,min(127,velocity)))})

def accompany(score, chords, meter, theme, sections):
    previous=[55,59,64]
    for bar,name in enumerate(chords):
        start=bar*meter
        section=next(s["name"] for s in sections if s["start_beat"]<=start<s["end_beat"])
        intro=section=="intro";outro=section=="outro"
        energetic=theme in ("cyberpunk","fire","crt")
        base=chord_notes(name)
        # Choose a close, ordered inversion: fewer leaps leave room for the lead.
        candidates=[]
        for shift in range(-1,3):
            for inv in range(3):
                candidate=sorted([n+12*shift+(12 if i<inv else 0) for i,n in enumerate(base)])
                if 48<=min(candidate) and max(candidate)<=76:
                    candidates.append(candidate)
        voicing=min(candidates,key=lambda c:sum(abs(a-b) for a,b in zip(c,previous)))
        previous=voicing
        level=48 if intro or outro else (61 if section=="variation" else 55)
        if energetic and not intro:
            for step in range(meter*2):
                for note in voicing[:2] if step%2 else voicing:
                    if step%2 or theme=="fire":add(score,1,start+step*.5,.32,note,level+(4 if step%4==1 else 0))
        elif theme=="mono" or (section in ("contrast","variation") and theme=="space"):
            for step in range(meter*2):
                add(score,1,start+step*.5,.43,voicing[(step+bar)%3],level-7)
        else:
            for note in voicing:add(score,1,start,meter-.10,note,level)
        bass=base[0]-12
        if bass<33:bass+=12
        for step in range(meter):
            if intro and step%2:continue
            if outro and bar==len(chords)-1 and step:continue
            pitch=bass+(7 if step==meter-1 and not outro else 0)
            add(score,2,start+step,.73 if energetic else .90,pitch,68 if step==0 else 58)
            if energetic and section=="variation" and step==meter-2:add(score,2,start+step+.75,.20,bass+12,48)
        if outro and bar==len(chords)-1:
            add(score,3,start,.15,49,38)
            continue
        if intro and bar<2:
            add(score,3,start,.10,51,26)
            continue
        for step in range(meter*2):
            beat=start+step*.5
            if energetic:
                add(score,3,beat,.075,42 if step%4!=3 else 46,37+(8 if step%2==0 else 0))
                if step in (0,4):add(score,3,beat,.13,36,72 if theme=="fire" else 62)
                if step in (2,6):add(score,3,beat,.14,38,58)
            else:
                if step%2==0:add(score,3,beat,.075,42 if theme=="mono" else (81 if theme=="cathedral" else 51),25 if theme=="space" else 31)
                if step==0:add(score,3,beat,.15,36,42 if theme=="cathedral" else 34)
                if step==meter:add(score,3,beat,.12,80 if theme=="cathedral" else 37,28)
        if section=="variation" and bar%8==7:
            for step,pitch in enumerate((45,47,50,38)):
                add(score,3,start+meter-1+step*.25,.12,pitch,40+step*5)

def write_midi(track, score):
    midi=mido.MidiFile(type=1,ticks_per_beat=TPB)
    conductor=mido.MidiTrack();midi.tracks.append(conductor)
    conductor.append(mido.MetaMessage("track_name",name=track["title"]))
    conductor.append(mido.MetaMessage("set_tempo",tempo=mido.bpm2tempo(track["bpm"])))
    conductor.append(mido.MetaMessage("time_signature",numerator=track["meter"],denominator=4))
    conductor.append(mido.MetaMessage("key_signature",key=track["key"]))
    last=0
    for s in track["sections"]:
        tick=round(s["start_beat"]*TPB)
        conductor.append(mido.MetaMessage("marker",text=s["name"],time=tick-last));last=tick
    end=round(track["beats"]*TPB)
    conductor.append(mido.MetaMessage("end_of_track",time=end-last))
    for role,channel in enumerate(CHANNELS):
        part=mido.MidiTrack();midi.tracks.append(part)
        part.append(mido.MetaMessage("track_name",name=ROLES[role]))
        part.append(mido.Message("program_change",channel=channel,program=track["programs"][role]))
        for control,value in ((7,(99,78,92,76)[role]),(10,(60,82,60,64)[role]),(91,(36,42,12,15)[role]),(93,10)):
            part.append(mido.Message("control_change",channel=channel,control=control,value=value))
        events=[]
        for n in score[role]:
            events.append((round(n["beat"]*TPB),1,mido.Message("note_on",channel=channel,note=n["pitch"],velocity=n["velocity"])))
            events.append((round((n["beat"]+n["duration"])*TPB),0,mido.Message("note_off",channel=channel,note=n["pitch"],velocity=0)))
        last=0
        for tick,_,msg in sorted(events,key=lambda e:(e[0],e[1],e[2].note)):
            part.append(msg.copy(time=tick-last));last=tick
        part.append(mido.Message("control_change",channel=channel,control=123,value=0,time=max(0,end-last)))
        part.append(mido.MetaMessage("end_of_track"))
    target=PRODUCTION/"midi"/(track["id"]+".mid");target.parent.mkdir(parents=True,exist_ok=True);midi.save(target)
    return target

def original_track(item):
    ident,title,theme,key,meter,bars,phrase_a,phrase_b,progress_a,progress_b=item
    tonic_pc=PITCH[key[:-1] if key.endswith("m") else key]
    dominant=("C","Db","D","Eb","E","F","F#","G","Ab","A","Bb","B")[(tonic_pc+7)%12]
    a=parse_phrase(phrase_a,key,meter);b=parse_phrase(phrase_b,key,meter)
    # Both authored periods end on a sustained tonic. Close the harmony on I/i;
    # retaining V here would leave a long unresolved fourth above the dominant.
    progress_a=" ".join(progress_a.split()[:-1]+[key])
    progress_b=" ".join(progress_b.split()[:-1]+[key])
    if ident=="cathedral_rose":
        progression=progress_a.split();progression[6]="F";progress_a=" ".join(progression)
    blocks=[("intro",4),("theme",8)]
    if bars>=40:blocks.append(("answer",8))
    blocks.extend([("contrast",8),("variation",8)])
    remaining=bars-sum(n for _,n in blocks)-4
    if remaining:blocks.append(("bridge",remaining))
    blocks.append(("outro",4))
    sections=[];chords=[];score=[[],[],[],[]];bar=0
    for name,count in blocks:
        sections.append(dict(name=name,start_beat=bar*meter,end_beat=(bar+count)*meter))
        progression=(progress_b if name in ("contrast","bridge") else progress_a).split()
        if name=="intro":progression=[key,key,progress_a.split()[1],dominant]
        if name=="outro":progression=[progress_a.split()[1],progress_a.split()[-2],dominant,key]
        chords.extend(progression[i%len(progression)] for i in range(count))
        phrase=b if name in ("contrast","bridge") else a
        if name=="intro":
            for i,d in enumerate((1,5,3,2)):
                add(score,0,(bar+i)*meter,meter*.76,degree(d,key),48+i*3)
        elif name=="outro":
            for i,d in enumerate((6,4,2,1)):
                add(score,0,(bar+i)*meter,meter-.30,degree(d,key),66-i*5)
        else:
            for start,length,pitch in phrase:
                if start>=count*meter:break
                if name=="answer":pitch+=12
                if name=="variation":
                    if length>=1 and int(start)%meter!=meter-1:
                        add(score,0,bar*meter+start,length*.42,pitch,80)
                        add(score,0,bar*meter+start+length*.5,length*.40,pitch+12,65)
                        continue
                add(score,0,bar*meter+start,length*(.84 if theme in ("fire","crt") else .92),pitch,
                    (72 if name=="contrast" else 78)+(4 if start%meter==0 else -3))
        bar+=count
    beats=bars*meter;bpm=beats*60/88
    programs,instruments=ENSEMBLES[theme]
    track=dict(id=ident,title=title,theme=theme,key=key,meter=meter,bpm=round(bpm,6),beats=beats,
               programs=programs,instruments=instruments,sections=sections,chords=chords,
               source="Original composition for TEXTRIS",license="Apache-2.0",composer="TEXTRIS contributors")
    accompany(score,chords,meter,theme,sections)
    return track,score

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--originals-only",action="store_true");args=parser.parse_args()
    work=[original_track(item) for item in ORIGINALS]
    if not args.originals_only:
        from soundtrack_classics import classic_tracks
        work.extend(classic_tracks())
    records=[]
    for track,score in work:
        midi=write_midi(track,score)
        (PRODUCTION/"scores").mkdir(parents=True,exist_ok=True)
        (PRODUCTION/"scores"/(track["id"]+".json")).write_text(json.dumps(dict(**track,notes={ROLES[i]:notes for i,notes in enumerate(score)}),indent=2)+"\n",encoding="utf-8")
        records.append(dict(id=track["id"],title=track["title"],theme=track["theme"],file="music/"+track["id"]+".ogg",
          duration=90.0,bpm=track["bpm"],time_signature=f"{track['meter']}/4",instruments=track["instruments"],
          sha256="",composer=track["composer"],source=track["source"],license=track["license"],
          source_midi=midi.relative_to(ROOT).as_posix(),sections=track["sections"]))
        print(track["id"],sum(map(len,score)),"notes",flush=True)
    RUNTIME.mkdir(parents=True,exist_ok=True)
    # The renderer replaces pending hashes/durations only after all encodes succeed.
    (PRODUCTION/"catalog-pending.json").write_text(json.dumps(dict(version=1,tracks=records),indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
