# TEXTRIS soundtrack attribution

Created 2026-10-08. This file accompanies the 26-track TEXTRIS soundtrack.
The recordings are new offline MIDI performances, not recordings sampled from
other games, orchestras or commercial releases. Classic tracks are compact new
four-part excerpt arrangements, not complete performances of every original work.

## Original compositions

The 18 cathedral, cyberpunk, space, fire, crt and mono compositions, authored score
data, MIDI performances and recordings are project contributions under Apache-2.0.
The reusable composition/render scripts are also Apache-2.0. Scores and intermediate
MIDI are in `assets/audio-production/music/scores/` and `midi/` in the source release.

## Classic sources

| Recording ID | Composer / original source | Digital source and usage |
| --- | --- | --- |
| classic_korobeiniki | Traditional Russian melody; words Nikolay Nekrasov (1861), no lyrics used | Melody checked against Jack Campin's Nine-Note Tunebook, tune371, [reference](https://abcnotation.com/tunePage?a=trillian.mit.edu%2F~jc%2Fmusic%2Fabc%2Fmirror%2Fcampin.me.uk%2FChalumeau_55%2F0417). Only the public-domain traditional tune is used; accompaniment is new. |
| classic_kalinka | Ivan Larionov (1830–1889), 1860 | Melody checked against [John Chambers' Kalinka ABC](https://trillian.mit.edu/~jc/music/abc/Russia/Kalinka.abc); original tune, with new accompaniment. |
| classic_bach_minuet | Johann Sebastian Bach, BWV814 Menuet; Bach-Gesellschaft, 1863 | [Mutopia100](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=100), literal digital edition by Knute Snortum, 2018. **CC BY-SA 4.0**. |
| classic_trepak | Pyotr Ilyich Tchaikovsky, Op.71a; composer's piano reduction, Jurgenson1892 / Rahter1898 | [IMSLP57454](https://imslp.org/wiki/Special:ReverseLookup/57454), printed pp.16–17. Public-domain score, manually transcribed melody. |
| classic_sugar_plum | Same composer and original edition | Same score, printed p.13. Public-domain score, manually transcribed celesta melody. No modern flute arrangement is used as a production input. |
| classic_reed_flutes | Same composer and original edition | Same score, printed pp.25–26. Public-domain score, manually transcribed upper melody; grace ornaments are omitted as identified in the score metadata. |
| classic_hungarian_five | Johannes Brahms, WoO1 No.5, composer's piano arrangement | [IMSLP103981](https://imslp.org/wiki/Special:ReverseLookup/103981), Brahms Werke / Breitkopf, printed p.17. Public-domain edition; A is moved up an octave and B retains the source register, followed by coherent whole-phrase register variations. |
| classic_rondo_turca | Wolfgang Amadeus Mozart, KV331 movementIII | [Mutopia108](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=108), Rune Zedeler and Chris Sawer, 2015, public-domain literal digital edition. Source pickup, pitches and rhythms preserved in the excerpt; new instrumentation, intro, variation, percussion and ending. |

Except the Bach derivative identified below, new arrangement and recording
contributions are Apache-2.0. This does not create copyright in the underlying
public-domain compositions. No claim of endorsement by source editors is made.

## Bach share-alike notice

`classic_bach_minuet.ogg`, `classic_bach_minuet.mid` and its score JSON are adaptations
of Knute Snortum's Mutopia edition and are distributed under
[Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
Changes: four-part instrumentation, register variation, dynamics, articulation,
intro/outro, light percussion, tempo and mastering. Retain attribution and identify
changes when redistributing an adaptation; distribute that adaptation under the same
license. This asset-specific license does not relicense the game's software.

## Production tools and sampled instruments

- FluidSynth2.6.1, [official project](https://github.com/FluidSynth/fluidsynth),
  LGPL-2.1. Used as a separate offline production program; not bundled in the game.
- GeneralUser GS2.0.3 by S. Christian Collins,
  [official repository](https://github.com/mrbumpy409/GeneralUser-GS) and
  [author's site](https://schristiancollins.com/generaluser.php).
  Full upstream license is `licenses/GeneralUser-GS-LICENSE.txt`.
  That license permits private and commercial music creation. Its author explicitly
  states that the historical origin of every sample cannot be completely verified.
  This upstream provenance limitation is retained here, not silently removed.
  The SoundFont itself is a production dependency and is not bundled in the game.
- FFmpeg / libvorbis encodes the distributed 44.1kHz stereo Ogg recordings at q6.
  mido1.3.3 writes the production MIDI. These tools are not game runtime requirements.

Automated score, source-note and signal checks are documented in the source tree.
They do not establish human listening approval or claim that a person listened to
these recordings during production.
