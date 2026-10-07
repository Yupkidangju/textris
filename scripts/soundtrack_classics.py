"""Source-grounded melody transcriptions and four-part classical arrangements.

Pitch/rhythm quotations are from the public-domain scores identified per track.
Accompaniments, introductions, transitions and endings are new TEXTRIS parts.
"""
from __future__ import annotations

from compose_soundtrack import PRODUCTION, add, accompany, chord_notes, degree, parse_phrase, source_notes

NUTCRACKER="Tchaikovsky, composer piano reduction, Jurgenson 1892 / Rahter 1898; IMSLP 57454"
FOLK=[
 ("classic_korobeiniki","Korobeiniki","Dm",[21,24,32,0],["Accordion","Nylon Guitar","Acoustic Bass","Folk Percussion"],
  "A4:1 E4 F4|G4:1 F4 E4|D4:1 D4 F4|A4:1 G4 F4|E4:1.5 F4|G4:1 A4:1|F4:1 D4:1|D4:1 r:1",
  "G4:1.5 Bb4|D5:1 C5 Bb4|A4:1.5 F4|A4:1 G4 F4|E4:1 E4 F4|G4:1 A4:1|F4:1 D4:1|D4:1 r:1",
  "Dm A Dm Dm A A Dm Dm", "Gm Gm Dm Dm A A Dm Dm",
  "Traditional Russian melody; Jack Campin Nine-Note Tunebook, tune 371 (melody-only reference)","Traditional"),
 ("classic_kalinka","Kalinka","Dm",[71,21,32,0],["Clarinet","Accordion","Acoustic Bass","Folk Percussion"],
  "G4:1 E4 F4|G4:1 E4 F4|G4:1 F4 E4|D4:1 A4 A4|G4:0.75 F4:0.25 E4 F4|G4:1 E4 F4|G4:1 F4 E4|D4:1 A4:1",
  "A4 C5 Bb4 A4:0.25 G4:0.25|F4:1 C4:1|A4 C5 Bb4 A4:0.25 G4:0.25|F4:1 C4:1|D4:1 D4 E4|G4 F4 E4 D4|C4:1 C4:1|C4:1 C5:1|A4 C5 G4 A4|F4:1 C4:1|A4 C5 G4 A4|F4:1 C4:1|D4:1 D4 E4|G4 F4 E4 D4|C5:1 Bb4:1|A4:2",
  "A A A Dm A A A Dm", "F F F F Bb G C C F F F F Bb G C A",
  "Ivan Larionov (1860), public-domain melody; John Chambers Kalinka.abc melody transcription reference","Ivan Larionov"),
 ("classic_trepak","Trepak","G",[40,48,43,0],["Violin","String Ensemble","Contrabass","Dance Percussion"],
  "G5 G5:0.25 F#5:0.25 G5 G5|E5 D5 C5 E5|D5 D5:0.25 C#5:0.25 D5 D5|B4 A4 G4 B4:0.25 D5:0.25|A4 A4:0.25 D5:0.25 G4 G4:0.25 D5:0.25|F#4 F#4:0.25 D5:0.25 A4 A4:0.25 D5:0.25|B4 B4:0.25 D5:0.25 G4 G4:0.25 D5:0.25|A4 G4 A4 D5:0.1666666667 E5:0.1666666667 F#5:0.1666666666",
  "r D5 r D5|r E5 r E5|r E5 r E5|r F#5 r F#5|r G5 r F#5|r E5 r D5|r C#5 r B4|r A4 r C#5",
  "G C G D G D G D", "G C A D G Em A A",
  NUTCRACKER+", printed pp.16-17, opening theme and middle offbeat contrast; new four-part accompaniment","Pyotr Ilyich Tchaikovsky"),
 ("classic_sugar_plum","Dance of the Sugar Plum Fairy","Em",[8,45,43,0],["Celesta","Pizzicato Strings","Contrabass","Delicate Percussion"],
  "r G6:0.25 E6:0.25 G6 F#6|D#6 E6 D6:0.25 D6:0.25 D6|C#6:0.25 C#6:0.25 C#6 C6:0.25 C6:0.25 C6|B5:0.25 E6:0.25 C6:0.25 E6:0.25 B5 r|r G5:0.25 E5:0.25 G5 F#5|C6 B5 G6:0.25 G6:0.25 G6|F#6:0.25 F#6:0.25 F#6 E6:0.25 E6:0.25 E6|D#6:0.25 F#6:0.25 E6:0.25 F#6:0.25 D#6 r",
  "r G6:0.25 E6:0.25 G6 F#6|D#6 E6 D6:0.25 D6:0.25 D6|C#6:0.25 C#6:0.25 C#6 C6:0.25 C6:0.25 C6|B5:0.25 E6:0.25 C6:0.25 E6:0.25 B5 r|r E5:0.25 C#5:0.25 E5 D#5|r D5:0.25 B4:0.25 D5 C#5|r C5:0.25 A4:0.25 C5 B4|r B4:0.125 D#5:0.125 F#5:0.125 B5:0.125 G5 E4",
  "Em B/Bm A/Am Em C Em B/Em B", "Em B/Bm A/Am Em A Bm Am Em",
  NUTCRACKER+", printed p.13, melody mm.5-20, directly transcribed (octave placement preserved)","Pyotr Ilyich Tchaikovsky"),
 ("classic_reed_flutes","Dance of the Reed Flutes","D",[73,45,42,0],["Flute","Pizzicato Strings","Cello","Light Percussion"],
  "D5:0.25 C#5:0.25 D5:0.25 C#5:0.25 D5 C#5|E5 D5:0.125 F#5:0.125 A5:0.125 D6:0.125 F#6:1|F#6:0.25 E6:0.25 F#6:0.25 E6:0.25 D6:0.25 C#6:0.25 B5:0.25 A5:0.25|D5:1 C#6:1|B5:0.25 B4:0.25 B4:0.25 B4:0.25 B4 A4|B5:0.25 B4:0.25 B4:0.25 B4:0.25 B4 A4|D6:0.25 D5:0.25 D5:0.25 D5:0.25 D5:0.25 C#5:0.25 E5:0.25 D5:0.25|D5:0.25 C#5:0.25 B4:0.25 A4:0.25 G5:0.5 E5:0.125 C#5:0.125 G4:0.125 E4:0.125",
  "D5:0.25 C#5:0.25 D5:0.25 C#5:0.25 D5 C#5|E5 D5:0.125 F#5:0.125 A5:0.125 D6:0.125 F#6:1|F#6:0.25 E6:0.25 F#6:0.25 E6:0.25 D6:0.25 C#6:0.25 B5:0.25 A5:0.25|D5:1 C#6:1|B5:0.25 B4:0.25 B4:0.25 B4:0.25 B4 A4|D6:0.25 D5:0.25 D5:0.25 D5:0.25 D5 C#5|F#6:0.25 F#5:0.25 F#5:0.25 F#5:0.25 F#5:0.25 E5:0.25 F#5:0.25 E5:0.25|A5:0.25 G#5:0.25 A5:0.25 G#5:0.25 B5:0.25 A5:0.25 B5:0.25 A5:0.25",
  "D D D Gm/A Em A G A", "D D D Gm/A Em Bm D E",
  NUTCRACKER+", printed p.25, opening melody mm.3-18 (grace ornament omitted)","Pyotr Ilyich Tchaikovsky"),
 ("classic_hungarian_five","Hungarian Dance No. 5","F#m",[40,24,32,0],["Violin","Nylon Guitar","Acoustic Bass","Dance Percussion"],
  "C#5:1.5 F#5|A5:1.5 F#5|E#5:1.5 F#5:0.25 G#5:0.25|F#5:2|D5:1.5 E5:0.25 F#5:0.25|C#5:2|B4:0.25 A4:0.25 A4:0.25 G#4:0.25 G#4:0.75 C#5:0.25|F#4:2",
  "C#5:1.5 F#5:0.25 A5:0.25|C#6:1.5 A5|G#5:1.5 A5:0.25 B5:0.25|A5:2|D5:0.25 E5:0.25 F#5:0.25 D5:0.25 C#5:0.25 D5:0.25 E5:0.25 C#5:0.25|B4:0.25 C#5:0.25 D5:0.25 B4:0.25 A4:0.25 B4:0.25 C#5:0.25 A4:0.25|B4:0.25 A4:0.25 A4:0.25 G#4:0.25 G#4:0.75 C#5:0.25|F#4:1 F#5 r",
  "F#m F#m C# F#m Bm F#m C# F#m", "F#m F#m C# F#m D Bm C# F#m",
  "Brahms own piano arrangement; Brahms Werke Breitkopf, IMSLP 103981, printed p.17, melody mm.1-16; A transposed +12 semitones, B in original register","Johannes Brahms"),
]

def arrange_manual(item):
    ident,title,key,programs,instruments,atext,btext,achords,bchords,source,composer=item
    names=("C","Db","D","Eb","E","F","F#","G","Ab","A","Bb","B")
    sixth=names[degree(6,key)%12]+("" if key.endswith("m") else "m")
    subdominant=names[degree(4,key)%12]+("m" if key.endswith("m") else "")
    dominant=names[degree(5,key)%12]
    a=parse_phrase(atext,key,2,absolute=True);b=parse_phrase(btext,key,2,absolute=True)
    alen=len(atext.split("|"));blen=len(btext.split("|"))
    blocks=[("intro",4,"a"),("theme",alen,"a"),("answer",alen,"a"),("contrast",blen,"b"),
            ("development",blen,"b"),("variation",alen,"a"),("reprise",alen,"a"),("outro",4,"a")]
    score=[[],[],[],[]];sections=[];chords=[];bar=0
    for name,count,which in blocks:
        sections.append(dict(name=name,start_beat=bar*2,end_beat=(bar+count)*2))
        progression=(achords if which=="a" else bchords).split()
        if name=="intro":progression=[key,key,sixth,dominant]
        if name=="outro":progression=[sixth,subdominant,dominant,key]
        chords.extend(progression[i%len(progression)] for i in range(count))
        if name=="intro":
            for i,d in enumerate((1,5,3,5)):add(score,0,(bar+i)*2,1.5,degree(d,key),48+4*i)
            if ident=="classic_kalinka":add(score,0,bar*2+7,0.82,69,78)
        elif name=="outro":
            for i,d in enumerate((6,4,2,1)):add(score,0,(bar+i)*2,1.60,degree(d,key),69-7*i)
        else:
            phrase=a if which=="a" else b
            for index,(beat,length,pitch) in enumerate(phrase):
                # Deliberate register changes and paired dynamic phrases are the variation.
                shift=-12 if name in ("answer","development") else 0
                if name=="variation":shift=12 if max(n[2] for n in phrase)<=83 else -12
                articulation=.79 if ident in ("classic_sugar_plum","classic_reed_flutes","classic_trepak") else .91
                add(score,0,bar*2+beat,length*articulation,pitch+shift,(80 if name in ("theme","reprise") else 72)+(4 if beat%2==0 else -3))
                if name=="development" and length>=1:
                    add(score,1,bar*2+beat+.5,min(length-.5,.42),pitch+shift-12,39)
        bar+=count
    beats=bar*2
    track=dict(id=ident,title=title,theme="classic",key=key,meter=2,bpm=round(beats*60/88,6),beats=beats,programs=programs,
               instruments=instruments,sections=sections,chords=chords,source=source,license="Apache-2.0 (new arrangement); public-domain composition",composer=composer,
               source_melody_a=atext,source_melody_b=btext)
    counterpoint_count=len(score[1])
    accompany(score,[name.split("/")[0] for name in chords],2,"cathedral" if "sugar" in ident else "mono",sections)
    for bar,name in enumerate(chords):
        if "/" not in name:continue
        # Chromatic original melodies need the harmony to change within the bar.
        # A major/minor third is never left sounding against its altered melody.
        start=bar*2
        score[1]=score[1][:counterpoint_count]+[n for n in score[1][counterpoint_count:] if not start<=n["beat"]<start+2]
        for half,chord in enumerate(name.split("/")):
            for pitch in chord_notes(chord):add(score,1,start+half,.90,pitch,47)
        second_root=chord_notes(name.split("/")[1])[0]-12
        if second_root<33:second_root+=12
        for note in score[2]:
            if start+1<=note["beat"]<start+2:note["pitch"]=second_root
    return track,score

def arrange_literal(ident,title,path,key,meter,selection,programs,instruments,source,license,*,pickup=0):
    upper=source_notes(path,1);lower=source_notes(path,2)
    intro=4*meter;outro=4*meter;body=sum(end-start for _,start,end in selection);beats=intro+body+outro
    sections=[dict(name="intro",start_beat=0,end_beat=intro)];score=[[],[],[],[]]
    for i,d in enumerate((1,5,3,2)):
        add(score,0,i*meter,min(meter*.72,meter-pickup-.1) if i==3 and pickup else meter*.72,degree(d,key),50+i*4)
    if pickup:
        for beat,length,pitch in upper:
            if beat<pickup:add(score,0,intro-pickup+beat,min(length,pickup-beat)*.93,pitch,72)
    position=intro
    for name,start,end in selection:
        sections.append(dict(name=name,start_beat=position,end_beat=position+end-start))
        for beat,length,pitch in upper:
            if start<=beat<end:
                add(score,0,position+beat-start,min(length,end-beat)*.93,pitch+(12 if name=="variation" else 0),76 if name=="theme" else 71)
        for beat,length,pitch in lower:
            if start<=beat<end:
                add(score,1,position+beat-start,min(length,end-beat)*.86,pitch+12 if pitch<57 else pitch,47)
                add(score,2,position+beat-start,min(length,end-beat)*.82,pitch-12 if pitch>=48 else pitch,60)
        position+=end-start
    sections.append(dict(name="outro",start_beat=position,end_beat=beats))
    for i,d in enumerate((6,4,2,1)):
        add(score,0,position+i*meter,meter*.85,degree(d,key),65-i*6)
        add(score,1,position+i*meter,meter*.80,degree(d,key)-12,47-i*3)
        add(score,2,position+i*meter,meter*.80,degree(d,key)-24,57-i*3)
    for bar in range(beats//meter):
        for step in range(meter):
            add(score,3,bar*meter+step,.09,51 if step==0 else 42,24 if step else 33)
        if bar%2==0:add(score,3,bar*meter,.15,36,35)
    track=dict(id=ident,title=title,theme="classic",key=key,meter=meter,bpm=round(beats*60/88,6),beats=beats,programs=programs,instruments=instruments,
               sections=sections,chords=[],source=source,license=license,composer="Johann Sebastian Bach" if "bach" in ident else "Wolfgang Amadeus Mozart",source_selection=selection)
    return track,score

def classic_tracks():
    result=[arrange_manual(item) for item in FOLK]
    result.append(arrange_literal("classic_bach_minuet","French Suite No. 3 - Minuet",PRODUCTION/"sources/bach/bach-french-suite-3-menuet.mid","Bm",3,
         [("theme",0,48),("contrast",48,108),("variation",0,24)],[6,48,42,0],["Harpsichord","Strings","Cello","Light Percussion"],
         "Bach-Gesellschaft 1863; literal digital edition Mutopia 100, Knute Snortum 2018, BWV 814 Menuet complete 36 bars plus eight-bar variation","CC-BY-SA-4.0"))
    result.append(arrange_literal("classic_rondo_turca","Rondo alla Turca",PRODUCTION/"sources/mozart-KV331_3_RondoAllaTurca.mid","Am",2,
         [("theme",1,33),("contrast",33,65),("development",65,97),("variation",1,33)],[0,48,32,0],["Grand Piano","Strings","Acoustic Bass","March Percussion"],
         "Mozart KV331 movement III; public-domain literal digital edition Mutopia 108, Rune Zedeler and Chris Sawer, opening 48 bars and varied reprise; one-quarter pickup preserved","Apache-2.0 (new arrangement); public-domain composition and digital edition",pickup=1))
    return result
