"""시각 테마와 배포된 음악 모음의 명시적 연결. 기존 ID 순서를 유지한다."""
MUSIC_THEMES=('cathedral','cyberpunk','space','fire','crt','mono')
THEMES=MUSIC_THEMES+('abyss','aurora')
MUSIC_SOURCE={'abyss':'space','aurora':'mono'}


def music_theme(theme):
    """원곡의 분류를 바꾸지 않고 시각 테마에 맞는 기존 모음을 선택한다."""
    return MUSIC_SOURCE.get(theme,theme)
