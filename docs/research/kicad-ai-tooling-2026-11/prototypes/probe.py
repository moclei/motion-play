import sys, collections, math, json
from kiutils.utils.sexpr import parse_sexp
PAPER={'A4':(297,210),'A3':(420,297),'A2':(594,420)}
def kids(e,name): return [x for x in e if isinstance(x,list) and x and x[0]==name]
def kid(e,name):
    k=kids(e,name); return k[0] if k else None
def is_hidden(prop):
    if kid(prop,'hide') and kid(prop,'hide')[1:2]==['yes']: return True
    eff=kid(prop,'effects')
    if eff is None: return False
    if 'hide' in eff: return True
    h=kid(eff,'hide')
    return bool(h and (len(h)==1 or h[1]=='yes'))
def fsize(e):
    eff=kid(e,'effects')
    if eff is not None:
        f=kid(eff,'font')
        if f is not None and kid(f,'size'): return float(kid(f,'size')[1])
    return 1.27
def justify(e):
    eff=kid(e,'effects'); 
    j=kid(eff,'justify') if eff is not None else None
    return j[1:] if j else []
def bbox_text(x,y,ang,text,h,just,kind):
    w=max(1,len(text))*h*0.72; hh=h*1.1
    vert = round(ang)%180==90
    if kind=='label':  # anchor at start
        if round(ang)%360==0: box=(x,y-hh,x+w,y)
        elif round(ang)%360==180: box=(x-w,y-hh,x,y)
        elif round(ang)%360==90: box=(x-hh,y-w,x,y)
        else: box=(x-hh,y,x,y+w)
        return box
    if kind=='hlabel' or kind=='glabel':
        w+=h*1.5
        a=round(ang)%360
        if a==0: return (x,y-hh/2,x+w,y+hh/2)
        if a==180: return (x-w,y-hh/2,x,y+hh/2)
        if a==90: return (x-hh/2,y-w,x+hh/2,y)
        return (x-hh/2,y,x+hh/2,y+w)
    # field: centered unless justify
    L,Lh=(w,hh) if not vert else (hh,w)
    x0=x-L/2; y0=y-Lh/2
    if 'left' in just and not vert: x0=x
    if 'right' in just and not vert: x0=x-L
    return (x0,y0,x0+L,y0+Lh)
def ov(a,b):
    ix=min(a[2],b[2])-max(a[0],b[0]); iy=min(a[3],b[3])-max(a[1],b[1])
    if ix<=0 or iy<=0: return 0
    sa=(a[2]-a[0])*(a[3]-a[1]); sb=(b[2]-b[0])*(b[3]-b[1])
    return ix*iy/min(sa,sb)
def libbox(lib):
    pts=[]
    def walk(e):
        for x in e:
            if not isinstance(x,list) or not x: continue
            if x[0]=='rectangle':
                for k in ('start','end'):
                    p=kid(x,k); pts.append((float(p[1]),float(p[2])))
            elif x[0]=='pin':
                a=kid(x,'at'); L=kid(x,'length'); ln=float(L[1]) if L else 0
                px,py,pa=float(a[1]),float(a[2]),float(a[3]) if len(a)>3 else 0
                pts.append((px,py)); pts.append((px+ln*math.cos(math.radians(pa)),py+ln*math.sin(math.radians(pa))))
            elif x[0] in ('polyline',):
                for p in kids(kid(x,'pts') or [],'xy'): pts.append((float(p[1]),float(p[2])))
            elif x[0]=='circle':
                c=kid(x,'center'); r=float(kid(x,'radius')[1]); pts.extend([(float(c[1])-r,float(c[2])-r),(float(c[1])+r,float(c[2])+r)])
            elif x[0]=='symbol': walk(x)
    walk(lib)
    return pts
def analyse(path):
    t=parse_sexp(open(path).read())
    paper=kid(t,'paper')[1]; PW,PH=PAPER.get(paper,(297,210))
    libs={l[1]:libbox(l) for l in kids(kid(t,'lib_symbols'),'symbol')}
    syms=kids(t,'symbol')
    texts=[]; vis=collections.Counter(); hidden=collections.Counter(); offsheet_txt=0; at_origin=0
    symboxes=[]; offsym=[]
    for s in syms:
        lid=kid(s,'lib_id')[1]; a=kid(s,'at'); sx,sy,sa=float(a[1]),float(a[2]),float(a[3]) if len(a)>3 else 0
        ref=[p[2] for p in kids(s,'property') if p[1]=='Reference'][0]
        if not(0<sx<PW and 0<sy<PH): offsym.append(ref)
        if not ref.startswith('#'):
            pts=libs.get(lid,[])
            if pts:
                c,sn=math.cos(math.radians(-sa)),math.sin(math.radians(-sa))
                tp=[(sx+px*c-(-py)*sn*-1 if False else sx+(px*c+py*sn), sy+(px*sn*-1+py*c)) for px,py in pts]
                # lib y is up; sch y down
                tp=[]
                for px,py in pts:
                    py=-py
                    r=math.radians(-sa)  # sch rotation ccw visually
                    tp.append((sx+px*math.cos(r)-py*math.sin(r), sy+px*math.sin(r)+py*math.cos(r)))
                xs=[p[0] for p in tp]; ys=[p[1] for p in tp]
                symboxes.append((ref,(min(xs),min(ys),max(xs),max(ys))))
        for p in kids(s,'property'):
            key,val=p[1],p[2]
            pa=kid(p,'at'); px,py=float(pa[1]),float(pa[2]); pang=float(pa[3]) if len(pa)>3 else 0
            if is_hidden(p) or val in ('','~'):
                hidden[key]+=1; continue
            if ref.startswith('#') and key=='Reference': hidden[key]+=1; continue
            k2 = 'ai_*' if key.startswith('ai_') else key
            vis[k2]+=1
            if px==0 and py==0: at_origin+=1
            if not(0<=px<=PW and 0<=py<=PH): offsheet_txt+=1
            ang=(pang)  # field angle stored absolute-ish
            texts.append(('field:'+k2, ref, val, bbox_text(px,py,ang,val,fsize(p),justify(p),'field')))
    labs=collections.Counter()
    for kind,tag in (('label','label'),('glabel','global_label'),('hlabel','hierarchical_label')):
        for l in kids(t,tag):
            a=kid(l,'at'); x,y,an=float(a[1]),float(a[2]),float(a[3]) if len(a)>3 else 0
            labs[kind]+=1
            texts.append((kind,'',l[1],bbox_text(x,y,an,l[1],fsize(l),justify(l),kind)))
    for l in kids(t,'text'):
        a=kid(l,'at'); texts.append(('text','',l[1],bbox_text(float(a[1]),float(a[2]),float(a[3]) if len(a)>3 else 0,l[1].split('\n')[0],fsize(l),justify(l),'field')))
    # overlaps
    pairs=collections.Counter(); bad=set(); examples=[]
    n=len(texts)
    for i in range(n):
        for j in range(i+1,n):
            if ov(texts[i][3],texts[j][3])>0.25:
                ki=texts[i][0]; kj=texts[j][0]
                pairs[tuple(sorted((ki.split(':')[0] if not ki.startswith('field:Ref') and not ki.startswith('field:Val') else ki, kj.split(':')[0] if not kj.startswith('field:Ref') and not kj.startswith('field:Val') else kj)))]+=1
                bad.add(i); bad.add(j)
                if len(examples)<400: examples.append((texts[i][:3],texts[j][:3],texts[i][3]))
    # overlaps excluding non-default fields (i.e. after hiding)
    keep=[k for k,x in enumerate(texts) if not x[0].startswith('field:') or x[0] in ('field:Reference','field:Value')]
    bad2=set(); np2=0
    for a_ in range(len(keep)):
        for b_ in range(a_+1,len(keep)):
            i,j=keep[a_],keep[b_]
            if ov(texts[i][3],texts[j][3])>0.25: np2+=1; bad2.add(i); bad2.add(j)
    sov=[]
    for i in range(len(symboxes)):
        for j in range(i+1,len(symboxes)):
            if ov(symboxes[i][1],symboxes[j][1])>0.3: sov.append((symboxes[i][0],symboxes[j][0]))
    # labels by region grid (A..)
    return dict(paper=paper,symbols=len([s for s in syms]),parts=len(symboxes),labels=dict(labs),texts=len(texts),
        visible=dict(vis),hidden_count=sum(hidden.values()),off_sheet_text=offsheet_txt,fields_at_origin=at_origin,
        off_sheet_symbols=offsym,overlap_pairs=sum(pairs.values()),items_in_overlap=len(bad),pair_kinds={"+".join(k):v for k,v in pairs.most_common(8)},
        overlap_pairs_after_hiding=np2,items_after_hiding=len(bad2),symbol_overlaps=sov,examples=examples)
if __name__=='__main__':
    out={}
    for p in sys.argv[2:]:
        r=analyse(p); out[p]=r
        ex=r.pop('examples')
        print('==',p.split('/')[-1]); print(json.dumps(r,indent=None))
        if sys.argv[1]=='ex':
            for e in ex[:25]: print('   ',e)

def after(path):
    import probe
