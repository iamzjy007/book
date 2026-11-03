"""Persistent, locked work claiming. No API calls; workers translate manually."""
from pathlib import Path
import contextlib,fcntl,json,sys,datetime
import pipeline as p
Q=p.ROOT/'work-queue.json'
@contextlib.contextmanager
def locked():
 with (p.ROOT/'.queue.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  yield
  fcntl.flock(lock,fcntl.LOCK_UN)
def reconcile(q,m):
 books={b['id']:b for b in m['sections']}
 for task in q['tasks']:
  if task['status']=='complete':continue
  units={(b['id'],u['id']):(b,u) for b in [books[task['book_id']]] for u in b['units']}
  remaining=[uid for uid in task['units'] if p.validate(*units[(task['book_id'],uid)])[0]!='complete']
  if not remaining:task['status']='complete'
 return q
def main():
 command=sys.argv[1];worker=sys.argv[2] if len(sys.argv)>2 else None
 m=p.manifest()
 with locked():
  q=reconcile(p.read(Q),m)
  if command=='claim':
   assert worker,'worker required'
   task=next((t for t in q['tasks'] if t['status']=='claimed' and t.get('worker')==worker),None)
   if task is None:task=next((t for t in q['tasks'] if t['status']=='pending'),None)
   if task:
    task['status']='claimed';task['worker']=worker;task['claimed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   p.save(Q,q);print(json.dumps(task,ensure_ascii=False,indent=2))
  elif command=='release':
   assert worker,'worker name or all required'
   released=[]
   for task in q['tasks']:
    if task['status']=='claimed' and (worker=='all' or task.get('worker')==worker):
     task['status']='pending';task['worker']=None;released.append(task['id'])
   p.save(Q,q);print(json.dumps({'released':released}))
  elif command=='status':
   p.save(Q,q)
   from collections import Counter
   print(json.dumps({'counts':dict(Counter(t['status'] for t in q['tasks'])),'active':[t for t in q['tasks'] if t['status']=='claimed']},ensure_ascii=False,indent=2))
  else:raise ValueError(command)
if __name__=='__main__':main()
