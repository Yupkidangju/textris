"""게임 사건을 표현용 효과음으로 변환한다. 게임/RNG/리플레이는 수정하지 않는다."""


class AudioEvents:
    def __init__(self,audio):
        self.audio=audio
        self.reset()

    def reset(self,*,b2b=False,danger=False,fever=False):
        self.difficult=b2b; self.danger=danger; self.fever=fever

    def process(self,events,*,danger,fever):
        peak=any(event.name in ('clear','win','gameover','boss_break') for event in events)
        for event in events:
            name,data=event.name,event.data
            if name=='clear':
                count=data['count']; difficult=count>0 and (count==4 or data['spin'])
                cue=('all_clear' if data['perfect'] else 'tspin' if data['spin'] else
                     {1:'clear_single',2:'clear_double',3:'clear_triple',4:'tetris'}.get(count))
                if cue: self.audio.play(cue)
                if data['combo']>0: self.audio.play('combo')
                # 기존 clear.b2b는 첫 difficult clear에서도 True이므로 직전 체인을 관측한다.
                if difficult and self.difficult: self.audio.play('b2b')
                if count: self.difficult=difficult
            elif name in ('move','rotate','hold','drop','lock','level','gameover','win','boss_hit','boss_break'):
                if not (peak and name in ('drop','lock','rotate','hold')):
                    self.audio.play(name)
        if danger and not self.danger: self.audio.play('danger')
        if fever!=self.fever: self.audio.play('fever_start' if fever else 'fever_end')
        self.danger,self.fever=danger,fever
