"""코드페이지/폰트 차이를 분리한 보수적 문자 출력 경계."""
import codecs
import unicodedata


def needs_ascii(platform,encoding,unicode_requested=False):
    if unicode_requested or platform=='win32':
        # windows-curses의 wide-character 출력은 ANSI 코드페이지를 우회한다.
        return False
    try:
        return codecs.lookup(encoding or 'ascii').name!='utf-8'
    except LookupError:
        return True


ASCII_MAP=str.maketrans({'·':'.','×':'x','─':'-','━':'-','│':'|','║':'|','╎':'|',
    '╭':'+','╮':'+','╰':'+','╯':'+','┌':'+','┐':'+','└':'+','┘':'+',
    '╱':'/','╲':'\\','◆':'+','◇':'+','✦':'*','✧':'+','█':'#','▓':'#','▒':':',
    '░':'.','▀':'=','▄':'=','▂':'_','↑':'^','↓':'v','←':'<','→':'>','▶':'>'})


def safe_ascii(text):
    result=[]
    for char in str(text):
        if 32<=ord(char)<127:
            result.append(char)
        elif ord(char)<32 or ord(char)==127:
            continue
        elif ord(char) in ASCII_MAP:
            result.append(ASCII_MAP[ord(char)])
        elif 0x2800<=ord(char)<=0x28ff:
            result.append(':' if ord(char)!=0x2800 else ' ')
        elif not unicodedata.combining(char):
            result.append('??' if unicodedata.east_asian_width(char) in ('W','F') else '?')
    return ''.join(result)
