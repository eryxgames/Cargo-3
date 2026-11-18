"""List self.X reads that no method or assignment in the class defines (wrong-object bugs).

usage: attrlint.py cargo.py   (or game/world.py: the whole package)
"""
import ast,collections,sys
import os
# a file inside a package (game/world.py) means the whole package: classes and their
# mixins live in different modules
path=sys.argv[1]; folder=os.path.dirname(os.path.abspath(path))
files=[os.path.join(folder,f) for f in sorted(os.listdir(folder)) if f.endswith('.py')] if os.path.exists(os.path.join(folder,'__init__.py')) else [path]
classes={}
for f in files:
    for n in ast.parse(open(f,encoding='utf-8').read()).body:
        if isinstance(n,ast.ClassDef): classes[n.name]=n
def info(c):
    d=set()
    for m in c.body:
        if isinstance(m,ast.FunctionDef): d.add(m.name)
        elif isinstance(m,ast.Assign):
            for tg in m.targets:
                if isinstance(tg,ast.Name): d.add(tg.id)
    for x in ast.walk(c):
        if isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='self' and isinstance(x.ctx,ast.Store): d.add(x.attr)
    for b in c.bases:
        if isinstance(b,ast.Name) and b.id in classes: d|=info(classes[b.id])
    return d
n=0
for c in classes.values():
    d=info(c); miss=collections.defaultdict(list)
    for sub in classes.values():      # a mixin's self is the class that inherits it (Game)
        if any(isinstance(b,ast.Name) and b.id==c.name for b in sub.bases): d|=info(sub)
    for x in ast.walk(c):
        if isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='self' and isinstance(x.ctx,ast.Load) and x.attr not in d and not x.attr.startswith('__'):
            miss[x.attr].append(x.lineno)
    for k,v in sorted(miss.items()): print(f"{c.name}.{k}: lines {v[:6]}"); n+=1
print("broken self references:",n)
