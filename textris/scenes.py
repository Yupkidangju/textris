"""문자 장면 카탈로그와 작은 캔버스의 절차적/입체 배경."""
import math

BACKGROUNDS=('rain','plasma','tunnel','grid','braille','cube','tetromino','torus',
             'mandelbrot','julia','aurora','fluid','metaball','space','warp','city','logo','reflection','cathedral')
EFFECTS=('impact','elastic','echoes','cracks','shatter','ricochet','chain','lightning',
         'blackhole','glitch','smoke','fire','braille','laser','gold','vortex','electric',
         'ice','embers','typewriter','assemble','odometer','victory','collapse','ripple')
THEMES=('cathedral','cyberpunk','space','fire','crt','mono')
PROFILES=('theme','fx_intensity','fx_speed','fx_density','shake','flash','braille')


def project(x,y,z,t):
    a=t*.6; b=t*.37
    x,z=x*math.cos(a)-z*math.sin(a),x*math.sin(a)+z*math.cos(a)
    y,z=y*math.cos(b)-z*math.sin(b),y*math.sin(b)+z*math.cos(b)
    depth=4+z
    return x/depth,y/depth,z


def _line(canvas,a,b,ink):
    x0,y0=a; x1,y1=b
    count=max(abs(x1-x0),abs(y1-y0),1)
    for i in range(count+1):
        x=round(x0+(x1-x0)*i/count); y=round(y0+(y1-y0)*i/count)
        if 0<=y<len(canvas) and 0<=x<len(canvas[0]): canvas[y][x]=ink


def render(name,cols,rows,t,ascii_mode=False):
    cols=max(8,cols); rows=max(6,rows)
    canvas=[[' ']*cols for _ in range(rows)]
    shades=' .:-=+*#%@' if ascii_mode else ' ·░▒▓█'
    if name=='reflection':
        from .effects import art
        lettering=art('TEXTRIS',ascii_mode)
        for i,row in enumerate(lettering):
            left=(cols-len(row))//2
            for x,c in enumerate(row):
                sx=left+x
                top=rows//2-6+i
                bottom=rows//2+6-i
                if 0<=sx<cols and 0<=top<rows: canvas[top][sx]=c
                sx+=round(math.sin(t*3+i)*2)
                if 0<=sx<cols and 0<=bottom<rows: canvas[bottom][sx]='.' if ascii_mode and c!=' ' else '░' if c!=' ' else ' '
        return [''.join(row) for row in canvas]
    if name in ('cube','tetromino','torus','logo'):
        if name=='torus':
            depth={}
            for i in range(40):
                a=i*math.tau/40
                for j in range(20):
                    b=j*math.tau/20
                    px,py,z=project((1+.4*math.cos(b))*math.cos(a),.4*math.sin(b),(1+.4*math.cos(b))*math.sin(a),t)
                    x=round(cols/2+px*cols*.95); y=round(rows/2+py*rows*1.7)
                    if 0<=x<cols and 0<=y<rows and z<depth.get((x,y),99):
                        depth[x,y]=z
                        canvas[y][x]=shades[min(len(shades)-1,max(1,int((math.sin(a+b+t)+1)/2*(len(shades)-2))+1))]
        elif name=='logo':
            from .effects import art
            for y,row in enumerate(art('TEXTRIS',True)):
                for x,c in enumerate(row):
                    if c==' ' : continue
                    px,py,_=project((x-len(row)/2)/8,(y-2)/3,math.sin(x*.4+t)*.4,t)
                    sx=round(cols/2+px*cols*.8); sy=round(rows/2+py*rows*1.6)
                    if 0<=sx<cols and 0<=sy<rows: canvas[sy][sx]='#' if ascii_mode else '█'
        else:
            offsets=((0,0,0),) if name=='cube' else ((-1,0,0),(0,0,0),(1,0,0),(0,-1,0))
            edge=.8 if name=='cube' else .45
            for ox,oy,oz in offsets:
                vertices=[project(ox+sx*edge,oy+sy*edge,oz+sz*edge,t) for sx in (-1,1) for sy in (-1,1) for sz in (-1,1)]
                points=[(round(cols/2+x*cols*.7),round(rows/2+y*rows*1.2)) for x,y,z in vertices]
                for i in range(8):
                    for bit in (1,2,4):
                        j=i^bit
                        if i<j: _line(canvas,points[i],points[j],'#' if ascii_mode else '◆')
        return [''.join(row) for row in canvas]
    for y in range(rows):
        ny=(y-rows/2)/(rows/2)
        for x in range(cols):
            nx=(x-cols/2)/(cols/2); r=math.hypot(nx,ny); value=0
            if name=='rain':
                distance=(t*(2+x%5)+x*11-y)%rows
                canvas[y][x]='01{}<>/\\'[(x+y+int(t*3))%8] if distance<5 else ' '
                continue
            if name=='plasma': value=(math.sin(nx*6+t)+math.sin(ny*5-t)+math.sin((nx+ny)*4+t)+3)/6
            elif name=='tunnel': value=max(0,1-((r*8-t*3)%3))
            elif name=='grid':
                if ny<-.35: continue
                depth=max(.1,ny+.4)
                value=.8 if (int((nx/depth)*7)%6==0 or (1/depth+t)%1<.16) else .05
            elif name=='braille':
                mask=0
                for bit in range(8):
                    if math.sin(nx*8+bit*.7+t*2)+math.cos(ny*7-bit+t)>.5: mask|=1<<bit
                canvas[y][x]=shades[mask%len(shades)] if ascii_mode else chr(0x2800+mask)
                continue
            elif name in ('mandelbrot','julia'):
                zoom=1.8/(1+(t%18)*.4)
                c=complex(-.72+nx*zoom,ny*zoom)
                z=0j
                if name=='julia': z=c; c=complex(-.72,.2+math.sin(t*.2)*.12)
                count=0
                while abs(z)<2 and count<22: z=z*z+c; count+=1
                value=count/22
            elif name=='aurora':
                curtain=math.sin(nx*4+t*.7)*.5+math.sin(nx*9-t)*.15
                value=max(0,1-abs(ny-curtain)*2)*(math.sin(nx*12+t)*.3+.7)
            elif name=='fluid':
                angle=math.atan2(ny,nx)
                value=(math.sin(angle*4-r*10+t*2)+math.sin(nx*5+ny*7-t)+2)/4
            elif name=='metaball':
                field=sum(.16/(.08+(nx-math.sin(t*.6+i*2)*.7)**2+(ny-math.cos(t*.4+i*3)*.6)**2) for i in range(3))
                value=min(1,field*.4)
            elif name in ('space','warp'):
                angle=math.atan2(ny,nx)
                value=.08*(math.sin(nx*7+t*.1)+math.sin(ny*9-t*.2)+2)
                radial=(r*(18 if name=='space' else 9)-t*(.8 if name=='space' else 6))%4
                if int(angle*37)%7==0 and radial<(.25 if name=='space' else 1): value=.95
            elif name=='city':
                layer=max(0,int((ny+1)*3))
                building=(x+int(t*(.6+layer*.4)))//3
                height=((building*73+layer*19)%9)/7
                if ny>1-height:
                    value=.15 if (x+int(t))%3==0 else .8 if (x+y+building)%5==0 else .4
            elif name=='reflection':
                value=(math.sin(nx*11+ny*6+t*2)+math.cos(ny*16-t)+2)/4
                if ny<0: value*=.35
            canvas[y][x]=shades[max(0,min(len(shades)-1,int(value*(len(shades)-1))))]
    return [''.join(row) for row in canvas]
