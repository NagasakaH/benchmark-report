"""Independent fail-closed supervisor for this benchmark's processes only."""
import argparse,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
from terminal_bench_runner import O,CONTAINERS,dump

def signature(pid):
 try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
 except FileNotFoundError:return None

def matches(record):
 return bool(record and signature(record['pid'])==record['start'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);a=p.parse_args()
 owner={'pid':a.pid,'start':signature(a.pid)};last={}
 while True:
  try:
   last=json.loads((O/'status.json').read_text())
   if last.get('pid')!=a.pid:return
   if last['state'] in ('pilot_complete','awaiting_review'):return
   # Allow runner's own failure cleanup to finish before intervening.
   stale=time.time()-last['updated_at']>90
   if not matches(owner) or stale:break
  except (OSError,ValueError):
   if not matches(owner) or (last and time.time()-last.get('updated_at',0)>90):break
  time.sleep(2)
 evidence={'at':time.time(),'reason':'runner died or heartbeat stale','runner':owner,'state':last}
 label=last.get('label');api=O/'runs'/label/'api' if label else None
 if api and api.exists() and not (api/'STOP').exists():(api/'STOP').write_text('Independent watchdog: runner unavailable')
 active=False
 if matches(last.get('relay')):
  try:
   with urllib.request.urlopen('http://127.0.0.1:18091/status',timeout=3) as r:active=json.load(r)['active']>0
  except Exception:pass
 for proc in (last.get('child'),last.get('relay'),owner):
  if matches(proc):
   try:os.killpg(proc['pid'],signal.SIGTERM)
   except ProcessLookupError:pass
 # Stop inference only when our measured request was active, never an idle user model.
 if active and last.get('model') in CONTAINERS:
  q=subprocess.run(['docker','stop','-t','10',CONTAINERS[last['model']]],capture_output=True,text=True,timeout=25)
  evidence['stop_model']={'returncode':q.returncode,'stdout':q.stdout,'stderr':q.stderr}
 time.sleep(5)
 for proc in (last.get('child'),last.get('relay'),owner):
  if matches(proc):
   try:os.killpg(proc['pid'],signal.SIGKILL)
   except ProcessLookupError:pass
 dump(O/f'watchdog-event-{time.time_ns()}.json',evidence)
 last.update(state='needs_analysis',error='Independent watchdog: runner died or heartbeat stale',updated_at=time.time())
 dump(O/'status.json',last)

if __name__=='__main__':main()
