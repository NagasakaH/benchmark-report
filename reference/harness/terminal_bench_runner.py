"""Sequential official TB subset; persistent evidence, no infrastructure retries."""
import argparse,datetime,fcntl,glob,json,os,signal,subprocess,sys,time,urllib.request,shutil
from pathlib import Path
R=Path('/opt/benchmark');O=R/'results/terminal-bench-20261007';T=R/'tools/terminal-bench-20261007';H=T/'venv/bin/harbor';FAULT=R/'services/llama-swap/GPU-FAULT'
ALIASES={'iq4':'qwen3.8-flash-next-ud-iq4_xs-2gpu-256k','iq3':'qwen3.8-flash-next-iq3_s-2gpu-256k','27b':'qwen3.8-27b-thinking'}
CONTAINERS={'iq4':'llm-bench-iq4-dual256-production-20261007','iq3':'llm-bench-iq3s-dual256-20261004-no-mid-checkpoints-replica2','27b':'llm-bench-vllm'}
PORTS={'iq4':8090,'iq3':8086,'27b':8080}
def dump(p,d):
 q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');q.replace(p)
def run(*args,timeout=15):return subprocess.check_output(args,text=True,timeout=timeout).strip()
def get(url):
 with urllib.request.urlopen(url,timeout=4) as r:return json.load(r)
def resources():
 m={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()};g=[]
 for bus in ('0000:03:00.0','0000:07:00.0'):
  p=Path('/sys/bus/pci/devices')/bus;hw=next((p/'hwmon').glob('hwmon*'))
  g.append({'pci':bus,**{n:int((p/n).read_text()) for n in ('mem_info_vram_used','gpu_busy_percent')},**{n:int((hw/n).read_text()) for n in ('power1_average','power1_cap','temp1_input')}})
 return {'at':time.time(),'mem_available':m['MemAvailable'],'mem_free':m['MemFree'],'cached':m['Cached'],'mlocked':m['Mlocked'],'swap_used':m['SwapTotal']-m['SwapFree'],'disk_free':shutil.disk_usage(R).free,'model_disk_free':shutil.disk_usage('/srv/llm-models').free,'gpus':g,'fault':FAULT.exists()}
def check_resources(d):
 assert not d['fault'],'GPU fault latch set'
 assert d['mem_available']>=8*2**30,'host RAM below 8GiB'
 assert d['swap_used']<=512*2**20,'host swap above 512MiB'
 assert min(d['disk_free'],d['model_disk_free'])>=5*2**30,'disk below 5GiB'
 assert run('systemctl','is-active','llama-swap-gpu-watch.service')=='active','watcher inactive'
def stopchild(p):
 if p and p.poll() is None:
  os.killpg(p.pid,signal.SIGINT)
  try:p.wait(timeout=30)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
def identity(p):
 if not p or p.poll() is not None:return None
 try:return {'pid':p.pid,'start':Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[19]}
 except FileNotFoundError:return None
def idle(model):
 if model!='27b':return get(f'http://127.0.0.1:{PORTS[model]}/v1/status')['activity']['in_flight']==0
 with urllib.request.urlopen('http://127.0.0.1:8080/metrics',timeout=4) as r:lines=r.read().decode().splitlines()
 names=('vllm:num_requests_running','vllm:num_requests_waiting')
 values={n:[float(x.split()[-1]) for x in lines if x.startswith(n+'{') or x.startswith(n+' ')] for n in names}
 return all(v and all(x==0 for x in v) for v in values.values())
def prepare_iq3_cache(out):
 # Startup-only workaround under investigation. No files are deleted or rewritten.
 assert CONTAINERS['iq3'] not in run('docker','ps','--format','{{.Names}}').splitlines(),'IQ3 already running; cannot control its startup cache'
 evidence={'at':time.time(),'operation':'POSIX_FADV_DONTNEED stopped IQ3 pack/GGUF','before':resources(),'files':[]}
 for folder in (R/'strata-data/packs/iq3_s',R/'strata-data/models/IQ3_S'):
  for path in folder.rglob('*'):
   if path.is_file() and path.stat().st_size>2**20:
    with path.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    evidence['files'].append({'path':str(path.resolve()),'bytes':path.stat().st_size})
 assert len(evidence['files'])==5,'Unexpected IQ3 model files; review before load'
 evidence['after']=resources();dump(out/'cache-advice.json',evidence)
def prepare_cold_boundary(out,previous_model,save):
 evidence={'at':time.time(),'condition':'unload_then_targeted_fadvise_v1','before':resources(),'files':[]}
 try:
  active=[n for n in run('docker','ps','--format','{{.Names}}').splitlines() if n.startswith('llm-bench-')]
  if active:
   assert previous_model and active==[CONTAINERS[previous_model]],'Unexpected active model; preserve user work'
   assert idle(previous_model),'Previous model is busy; preserve user work'
   key=next(x.split('=',1)[1].strip().strip('\"\'') for x in (R/'services/llama-swap/credentials.env').read_text().splitlines() if x.startswith('LOCAL_LLM_API_KEY='))
   req=urllib.request.Request('http://127.0.0.1:18080/api/models/unload/'+ALIASES[previous_model],data=b'',method='POST',headers={'Authorization':'Bearer '+key})
   with urllib.request.urlopen(req,timeout=30) as response:evidence['unload']={'model':previous_model,'status':response.status,'body':response.read(4000).decode()}
  deadline=time.time()+45;stable=0
  while stable<2:
   d=resources();check_resources(d);save()
   active=[n for n in run('docker','ps','--format','{{.Names}}').splitlines() if n.startswith('llm-bench-')]
   stable=stable+1 if not active and all(g['mem_info_vram_used']<100*2**20 and g['gpu_busy_percent']<=1 for g in d['gpus']) else 0
   assert time.time()<deadline,'Model release not confirmed'
   time.sleep(1)
  evidence['released']=resources()
  folders=[R/'strata-data/packs/iq3_s',R/'strata-data/models/IQ3_S',R/'strata-data/packs/ud-iq4_xs-040-20261007',R/'strata-data/models/UD-IQ4_XS',R/'models/Qwen3.8-27B-MXFP4-mtpfp8',R/'models/Qwen3.8-27B-DFlash2-FP8']
  for folder in folders:
   assert folder.is_dir(),'Missing model cache folder: '+str(folder)
   for path in folder.rglob('*'):
    if path.is_file() and path.stat().st_size>2**20:
     with path.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
     evidence['files'].append({'path':str(path.resolve()),'bytes':path.stat().st_size})
   save()
  evidence['after']=resources();check_resources(evidence['after'])
  assert evidence['after']['mem_free']>=70*2**30,'Cold memory preparation below 70GiB free; review instead of load'
  assert not any(n.startswith('llm-bench-') for n in run('docker','ps','--format','{{.Names}}').splitlines()),'User model started during preparation'
 finally:dump(out/'memory-preparation.json',evidence)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pilot-only',action='store_true');ap.add_argument('--cache-recovery-probe',action='store_true');ap.add_argument('--memory-recovery-probe',action='store_true');ap.add_argument('--resume-reviewed-oracle-block',action='store_true');ap.add_argument('--guard-recovery-probe',action='store_true');ap.add_argument('--guard-recovery-probe-02',action='store_true');ap.add_argument('--setup-recovery-probe',action='store_true');ap.add_argument('--setup-recovery-probe-02',action='store_true');a=ap.parse_args();lock=(O/'runner.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 state={'state':'starting','pid':os.getpid(),'started_at':time.time(),'completed':[],'pilot_only':a.pilot_only};old=O/'status.json';prior=None
 if old.exists():
  prior=json.loads(old.read_text())
  state['blocked_tasks']=prior.get('blocked_tasks',{})
  if a.guard_recovery_probe_02:
   assert prior['state']=='needs_analysis' and prior.get('label')=='sqlite-db-truncate-27b-r3' and prior.get('error')=='AssertionError: StopRun: repeated_character_128:0:reasoning','Only reviewed wrapped hex interruption can be probed'
   review=json.loads((O/'guard-interruption-02/offline-review.json').read_text());assert review['passed'] and review['preserved_incomplete_detection'] and review['hard_cap']==512,'Offline wrapped hex review required'
   state['recovery_probe']='guard02';state['interrupted_label']=prior['label']
  elif a.setup_recovery_probe_02:
   assert prior['state']=='needs_analysis' and prior.get('label')=='query-optimize-iq4-r1' and prior.get('error')=='RuntimeError: Trial infrastructure/agent compatibility error: RuntimeError','Only reviewed query agent setup interruption can be probed'
   review=json.loads((O/'agent-setup-interruption-02/offline-review.json').read_text());assert review['passed'] and review['api_requests']==0,'CPU preparation review required'
   state['recovery_probe']='setup02';state['interrupted_label']=prior['label']
  elif a.setup_recovery_probe:
   assert prior['state']=='needs_analysis' and prior.get('label')=='polyglot-c-py-iq4-r1' and prior.get('error')=='RuntimeError: Trial infrastructure/agent compatibility error: RuntimeError','Only reviewed agent setup interruption can be probed'
   review=json.loads((O/'agent-setup-interruption-01/offline-review.json').read_text());assert review['passed'] and review['api_requests']==0,'CPU preparation review required'
   state['recovery_probe']='setup01';state['interrupted_label']=prior['label']
  elif a.guard_recovery_probe:
   assert prior['state']=='needs_analysis' and prior.get('label')=='db-wal-recovery-iq4-r1' and prior.get('error')=='AssertionError: StopRun: repeated_character_128:0:reasoning','Only reviewed hex quotation interruption can be probed'
   review=json.loads((O/'guard-interruption-01/offline-review.json').read_text());assert review['passed'] and review['preserved_incomplete_detection'],'Offline evidence required'
   state['recovery_probe']='guard01';state['interrupted_label']=prior['label']
  elif a.resume_reviewed_oracle_block:
   assert prior['state']=='needs_analysis' and prior.get('error')=='AssertionError: Oracle did not pass','Only reviewed oracle failure may be held'
   blocks=json.loads((O/'blocked-tasks.json').read_text());assert blocks[prior['task']]['disposition']=='hold_without_score','Explicit task hold missing'
   state['blocked_tasks']=blocks
  elif a.memory_recovery_probe:
   assert prior['state']=='needs_analysis' and prior.get('label')=='openssl-selfsigned-cert-iq3-r3' and prior.get('error')=='AssertionError: host swap above 512MiB','Only reviewed second swap interruption can be probed'
   assert (O/'memory-recovery-02/swap-return.json').exists(),'Memory preparation evidence required'
   state['recovery_probe']='memory02';state['interrupted_label']=prior['label']
  elif a.cache_recovery_probe:
   assert prior['state']=='needs_analysis' and prior.get('error')=='AssertionError: host swap above 512MiB','Only reviewed swap interruption can be probed'
   assert (O/'swap-interruption/cache-advice.json').exists(),'Cache intervention evidence required'
   state['recovery_probe']=True;state['interrupted_label']=prior['label']
  else:assert prior['state']=='pilot_complete','Existing run must be reviewed; no blind resume'
  state['completed']=prior['completed']
 child=relay=None;current=None;phase=None;watchdog=None
 def save():
  if watchdog is not None and state['state']!='needs_analysis':assert watchdog.poll() is None,'Independent watchdog exited'
  state.update(updated_at=time.time(),child=identity(child),relay=identity(relay));dump(old,state)
 env=os.environ.copy();env.update(HARBOR_TELEMETRY='0',OPENAI_API_KEY='local-benchmark-placeholder',TOKENIZERS_PARALLELISM='false',LITELLM_LOCAL_MODEL_COST_MAP='True')
 manifests=json.loads((O/'tasks-manifest.json').read_text());names=[x['name'] for x in manifests['tasks']];names.remove('openssl-selfsigned-cert');names.insert(0,'openssl-selfsigned-cert')
 schedule=[(task,rep,model) for task in names for rep in range(3) for model in ['iq4','iq3','27b'][rep:]+['iq4','iq3','27b'][:rep]]
 if a.pilot_only:schedule=schedule[:3]
 if a.cache_recovery_probe:schedule=[(prior['task'],prior['repetition']-1,prior['model'])]
 if a.setup_recovery_probe_02:schedule=[(prior['task'],prior['repetition']-1,prior['model'])]
 if a.setup_recovery_probe:schedule=[(prior['task'],prior['repetition']-1,prior['model'])]
 if a.guard_recovery_probe_02:schedule=[(prior['task'],prior['repetition']-1,prior['model'])]
 if a.guard_recovery_probe:schedule=[(prior['task'],prior['repetition']-1,prior['model'])]
 if a.memory_recovery_probe:schedule=[(prior['task'],prior['repetition']-1,prior['model'])]
 try:
  save()
  watchdog=subprocess.Popen([sys.executable,str(T/'terminal_bench_watchdog.py'),'--pid',str(os.getpid())],start_new_session=True)
  # Reuse an idle pilot-owned model after two zero-activity observations.
  # All other active models wait for normal TTL; do not stop user work.
  pilot_model=prior['completed'][-1]['model'] if prior and prior.get('completed') else None;idle_count=0
  while any(n.startswith('llm-bench-') for n in run('docker','ps','--format','{{.Names}}').splitlines()):
   state.update(state='waiting_idle',phase='waiting_idle');check_resources(resources());save();time.sleep(3)
   active=[n for n in run('docker','ps','--format','{{.Names}}').splitlines() if n.startswith('llm-bench-')]
   try:verified=pilot_model is not None and active==[CONTAINERS[pilot_model]] and idle(pilot_model)
   except Exception:verified=False
   idle_count=idle_count+1 if verified else 0
   if idle_count>=2:state['pilot_idle_reused']=pilot_model;break
  for task,rep,model in schedule:
   if task in state.get('blocked_tasks',{}):continue
   schedule_label=f'{task}-{model}-r{rep+1}';label=schedule_label+('-guard-recovery02' if a.guard_recovery_probe_02 else '-setup-recovery02' if a.setup_recovery_probe_02 else '-setup-recovery01' if a.setup_recovery_probe else '-guard-recovery01' if a.guard_recovery_probe else '-memory-recovery02' if a.memory_recovery_probe else '-cache-recovery01' if a.cache_recovery_probe else '')
   if any(x.get('schedule_label',x['label'])==schedule_label for x in state['completed']):continue
   current=model;check_resources(resources());out=O/'runs'/label;out.mkdir(parents=True,exist_ok=False);state.update(state='running',task=task,model=model,repetition=rep+1,label=label);save()
   # Validate each environment/scorer before measuring a model. Fixed failures are not replaced with easier tasks.
   oracle_job='oracle-pilot-01' if task=='openssl-selfsigned-cert' else 'oracle-'+task
   oracle_result=O/'oracle'/oracle_job/'result.json'
   if not oracle_result.exists():
    phase='oracle';state['phase']=phase;save()
    cmd=[str(H),'run','-p',str(T/'tasks'/task),'-a','oracle','-n','1','-k','1','-r','0','-o',str(O/'oracle'),'--job-name',oracle_job]
    with (out/'oracle.log').open('w') as log:
     child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
     save()
     while child.poll() is None:
      check_resources(resources());save();time.sleep(3)
    assert child.returncode==0,'Oracle infrastructure failure'
   oracle_trials=list(oracle_result.parent.glob('*/result.json'));assert len(oracle_trials)==1,'Oracle result missing'
   od=json.loads(oracle_trials[0].read_text());assert not od.get('exception_info') and od.get('verifier_result',{}).get('rewards',{}).get('reward')==1,'Oracle did not pass'
   phase='memory_preparation';state['phase']=phase;save()
   previous_model=state['completed'][-1]['model'] if state['completed'] else None
   prep_started=time.time();prepare_cold_boundary(out,previous_model,save);preparation_s=time.time()-prep_started
   api=out/'api';api.mkdir();relaylog=(out/'relay.log').open('w');relay=subprocess.Popen([sys.executable,str(T/'terminal_bench_relay.py'),'--out',str(api),'--model',model],stdout=relaylog,stderr=subprocess.STDOUT,start_new_session=True)
   save();time.sleep(1);assert relay.poll() is None and get('http://127.0.0.1:18091/status')['active']==0
   cfg={'job_name':label,'jobs_dir':str(O/'jobs'),'n_concurrent_trials':1,'n_attempts':1,'retry':{'max_retries':0},'agents':[{'name':'terminus-2','model_name':'openai/'+ALIASES[model],'kwargs':{'api_base':'http://127.0.0.1:18091/v1','temperature':1.0,'reasoning_effort':'medium','interleaved_thinking':True,'model_info':{'max_input_tokens':262144,'max_tokens':262144,'max_output_tokens':16384,'input_cost_per_token':0,'output_cost_per_token':0,'litellm_provider':'openai','mode':'chat','supports_reasoning':True},'llm_kwargs':{'num_retries':0,'timeout':1800},'llm_call_kwargs':{'max_tokens':16384}}}],'tasks':[{'path':str(T/'tasks'/task)}]}
   dump(out/'config.json',cfg);phase='agent';state['phase']=phase;save();started=time.time()
   with (out/'harbor.log').open('w') as log,(out/'telemetry.jsonl').open('a') as tele:
    agent_env=env.copy()
    if task in ('polyglot-c-py','query-optimize'):agent_env.update(TB_AGENT_APT_HTTPS='1',PYTHONPATH=str(T))
    child=subprocess.Popen([str(H),'run','-c',str(out/'config.json')],stdout=log,stderr=subprocess.STDOUT,env=agent_env,start_new_session=True)
    save()
    lastcheck=0
    while child.poll() is None:
     d=resources();tele.write(json.dumps(d)+'\n');tele.flush()
     if time.time()-lastcheck>=3:check_resources(d);lastcheck=time.time();save()
     assert relay.poll() is None,'relay exited'
     assert not (api/'STOP').exists(),(api/'STOP').read_text() if (api/'STOP').exists() else ''
     time.sleep(1)
   # If official task timeout cancelled the client, preserve and finish its in-flight request before next load.
   phase='draining';state['phase']=phase;save();until=time.time()+1900
   while get('http://127.0.0.1:18091/status')['active']:
    check_resources(resources());assert not (api/'STOP').exists(),'Relay stopped during drain';assert time.time()<until,'Drain timeout';save();time.sleep(2)
   assert not (api/'STOP').exists(),'Relay API failure'
   stopchild(relay);relaylog.close();relay=None
   trials=list((O/'jobs'/label).glob('*/result.json'));assert len(trials)==1,'Trial result missing'
   result=json.loads(trials[0].read_text());exception=result.get('exception_info');etype=exception.get('exception_type','') if exception else ''
   allowed=('AgentTimeoutError','AgentTimeoutException','OutputLengthExceededError','ContextLengthExceededError')
   if exception and etype not in allowed:raise RuntimeError('Trial infrastructure/agent compatibility error: '+etype)
   reward=(result.get('verifier_result') or {}).get('rewards')
   elapsed_s=time.time()-started
   state['completed'].append({'label':label,'schedule_label':schedule_label,'task':task,'model':model,'repetition':rep+1,'reward':reward,'exception_type':etype or None,'elapsed_s':elapsed_s,'preparation_s':preparation_s,'elapsed_with_preparation_s':elapsed_s+preparation_s,'memory_condition':'unload_then_targeted_fadvise_v1','agent_setup_transport':'ubuntu_https_public_ca_v1' if task in ('polyglot-c-py','query-optimize') else 'original','result':str(trials[0])});save();child=None
  state['state']='pilot_complete' if a.pilot_only or a.cache_recovery_probe or a.memory_recovery_probe or a.guard_recovery_probe or a.guard_recovery_probe_02 or a.setup_recovery_probe or a.setup_recovery_probe_02 else 'awaiting_review';state['ended_at']=time.time();state['held_trials']=len(state.get('blocked_tasks',{}))*9;save()
 except BaseException as e:
  state.update(state='needs_analysis',error=type(e).__name__+': '+str(e),failed_phase=phase);save()
  # Inference fault requests are not retried; stop only the active benchmark model if still owned.
  active_request=False
  if relay and relay.poll() is None:
   try:active_request=get('http://127.0.0.1:18091/status')['active']>0
   except Exception:active_request=True
  if current and phase in ('agent','draining') and (active_request or (O/'runs'/state['label']/'api/STOP').exists() or FAULT.exists()):
   if CONTAINERS[current] in run('docker','ps','--format','{{.Names}}').splitlines():subprocess.run(['docker','stop','-t','10',CONTAINERS[current]],timeout=20)
  stopchild(child)
  raise
 finally:
  stopchild(relay)
  state['updated_at']=time.time();dump(old,state)
  stopchild(watchdog)
if __name__=='__main__':main()
