"""Presentation-only playback of already committed turns.

No renderer state is passed to an agent. The replay records the engine's existing
cell-by-cell collision order on copies, including bullets removed by a collision.
The three intermediate frames are visual snapshots, never game/search states.
"""
from dataclasses import dataclass


@dataclass
class BulletClip:
    direction: int
    owner: int
    points: list
    started: float
    step_ms: float = 1
    stopped: bool = False

    def distance(self):
        return sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(self.points,self.points[1:]))

    def finish_time(self):
        return self.started+self.distance()*self.step_ms

    def position(self, now):
        if len(self.points)==1:
            return None if self.stopped else self.points[0]
        distance=max(0.,(now-self.started)/self.step_ms)
        for a,b in zip(self.points,self.points[1:]):
            length=abs(b[0]-a[0])+abs(b[1]-a[1])
            if length and distance<length:
                t=distance/length
                return a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            distance-=length
        return None if self.stopped else self.points[-1]


def trace_cycle(game, state):
    """Record one bullet phase on a private copy, using the engine's priority."""
    s=state.copy()
    bullets=list(s.bullets)
    pos=[(b.r,b.c) for b in bullets]
    paths=[[p] for p in pos]
    alive=[True]*len(bullets)
    effects=[]
    frames=[s.copy()]
    for step in range(1,game.TOC_DO_DAN+1):
        old=list(pos)
        walls,tanks,bases={},[0]*len(s.tanks),[0]*len(s.bases)
        flying=[]
        step_hits=[]
        for i,b in enumerate(bullets):
            if not alive[i]:continue
            dr,dc=game.HUONG[b.d]
            r,c=old[i][0]+dr,old[i][1]+dc
            pos[i]=(r,c)
            paths[i].append((r,c))
            if not s.in_bounds(r,c):
                paths[i][-1]=(old[i][0]+dr*.5,old[i][1]+dc*.5)
                alive[i]=False
                continue
            entity=s.entity_at(r,c)
            if entity is None:
                flying.append(i)
                continue
            kind,key=entity
            paths[i][-1]=(old[i][0]+dr*.5,old[i][1]+dc*.5)
            if kind==game.EntityKind.WALL:walls[(r,c)]=walls.get((r,c),0)+1
            elif kind==game.EntityKind.TANK:tanks[key]+=1
            elif kind==game.EntityKind.BASE:bases[key]+=1
            alive[i]=False
            step_hits.append((i,kind,key,(r,c)))
        cells={}
        for i in flying:cells.setdefault(pos[i],[]).append(i)
        collided=set()
        for group in cells.values():
            if len(group)>1:
                for i in group:alive[i]=False;collided.add(i)
        for x,i in enumerate(flying):
            for j in flying[x+1:]:
                if pos[i]==old[j] and pos[j]==old[i]:
                    alive[i]=alive[j]=False
                    midpoint=((old[i][0]+old[j][0])*.5,(old[i][1]+old[j][1])*.5)
                    paths[i][-1]=paths[j][-1]=midpoint
                    collided.update((i,j))
        for cell,count in walls.items():
            s.walls[cell]-=count
            if s.walls[cell]<=0:del s.walls[cell]
            s._wkey=None
        for i,count in enumerate(tanks):
            if count:s.tanks[i]=s.tanks[i]._replace(hp=max(0,s.tanks[i].hp-count))
        for i,count in enumerate(bases):
            if count:s.bases[i]=s.bases[i]._replace(hp=max(0,s.bases[i].hp-count))
        s._term=None
        for i,kind,key,cell in step_hits:
            destroyed=(kind==game.EntityKind.TANK and s.tanks[key].hp==0 or
                       kind==game.EntityKind.BASE and s.bases[key].hp==0)
            effects.append(dict(step=step,index=i,point=paths[i][-1],kind=str(kind.value),large=destroyed))
        for i in collided:
            effects.append(dict(step=step,index=i,point=paths[i][-1],kind='bullet',large=False))
        s.bullets=[game.Bullet(*pos[i],b.d,b.owner) for i,b in enumerate(bullets) if alive[i]]
        if s.is_terminal():
            s.bullets=[]
            alive=[False]*len(bullets)
            frames.append(s.copy())
            break
        frames.append(s.copy())
    while len(frames)<game.TOC_DO_DAN+1:frames.append(frames[-1].copy())
    return paths,alive,effects,frames


class BulletPlayback:
    def __init__(self,game):
        self.game=game
        self.clips={}
        self.effects=[]
        self.ids=[]
        self.logical=[]
        self.next_id=0
        self.ends=0
        self.started=0
        self.duration=1
        self.frames=[]
        self.frame_times=[]

    def reset(self,state,now=0):
        self.clips={};self.effects=[];self.ids=[];self.next_id=0
        self.logical=list(state.bullets)
        self.frames=[state.copy()]
        self.frame_times=[now]
        self.started=self.ends=now
        self.duration=1
        for b in state.bullets:self.ids.append(self._spawn(b,now))

    def _spawn(self,bullet,now,muzzle=False):
        key=self.next_id;self.next_id+=1
        dr,dc=self.game.HUONG[bullet.d]
        point=(bullet.r+dr*.35,bullet.c+dc*.35) if muzzle else (bullet.r,bullet.c)
        self.clips[key]=BulletClip(bullet.d,bullet.owner,[point],now)
        return key

    def busy(self,now):
        return now<self.ends

    def state_at(self,now):
        if len(self.frames)==1:return self.frames[0]
        index=0
        for i,at in enumerate(self.frame_times):
            if now>=at:index=i
        return self.frames[index]

    def positions(self,now):
        out=[]
        for clip in self.clips.values():
            point=clip.position(now)
            if point is not None:out.append((*point,clip.direction))
        return out

    def observe(self,previous,current,action,now,duration):
        # A reset also handles callers who replace a match state outside the UI.
        if self.logical!=list(previous.bullets):self.reset(previous,now)
        g=self.game
        shadow=previous.copy()
        ids=list(self.ids)
        self.effects=[e for e in self.effects if now-e['at']<240]
        self.clips={i:c for i,c in self.clips.items() if not c.stopped or c.position(now) is not None}
        mover=previous.to_move
        tank=previous.tanks[mover]
        if action in g.HUONG_DI:
            new_tank=current.tanks[mover]
            moved=(tank.r,tank.c)!=(new_tank.r,new_tank.c)
            hits=[i for i,b in enumerate(shadow.bullets) if moved and (b.r,b.c)==(new_tank.r,new_tank.c)]
            for i in hits:
                clip=self.clips[ids[i]];clip.stopped=True;clip.points=[(new_tank.r,new_tank.c)]
                self.effects.append(dict(point=(new_tank.r,new_tank.c),at=now,kind='tank',large=new_tank.hp<=0))
            ids=[key for i,key in enumerate(ids) if i not in hits]
            shadow.bullets=[b for i,b in enumerate(shadow.bullets) if i not in hits]
            shadow.tanks[mover]=new_tank._replace(hp=max(0,tank.hp-len(hits)))
        elif action==g.Action.FIRE:
            b=g.Bullet(tank.r,tank.c,tank.d,mover)
            shadow.bullets.append(b)
            ids.append(self._spawn(b,now,muzzle=True))
        shadow._term=None
        self.started=now;self.duration=max(1,duration)
        self.ends=now
        if shadow.is_terminal():
            for c in self.clips.values():c.stopped=True;c.points=[c.points[-1]]
            self.ids=[];self.frames=[current.copy()];self.ends=now+180
        elif current.cycle!=previous.cycle:
            paths,alive,effects,frames=trace_cycle(g,shadow)
            for i,key in enumerate(ids):
                original=self.clips[key]
                start=original.position(now) or paths[i][0]
                points=[start]+paths[i][1:]
                self.clips[key]=BulletClip(original.direction,original.owner,points,now,
                                          self.duration/g.TOC_DO_DAN,not alive[i])
            self.ids=[key for i,key in enumerate(ids) if alive[i]]
            contacts={}
            for e in effects:
                at=self.clips[ids[e['index']]].finish_time()
                contacts.setdefault(e['step'],[]).append(at)
                self.effects.append(dict(point=e['point'],kind=e['kind'],large=e['large'],at=at))
            self.frame_times=[now]
            for step in range(1,g.TOC_DO_DAN+1):
                at=max(contacts[step]) if step in contacts else now+step*self.duration/g.TOC_DO_DAN
                self.frame_times.append(max(self.frame_times[-1],at))
            self.frames=frames
            for f in self.frames:
                f.cycle=current.cycle;f.to_move=current.to_move
            self.ends=now+self.duration+(140 if current.is_terminal() else 0)
        else:
            self.ids=ids
            self.frames=[current.copy()]
        self.logical=list(current.bullets)
