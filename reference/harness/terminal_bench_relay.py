"""Local-only measured JSON facade over real streaming model APIs; no retries."""
import argparse, json, threading, time, urllib.request, urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from iq3s_stability_replay import StreamEvidence, StopRun
from terminal_bench_stream import TerminalBenchEvidence

ALIASES={'iq4':'qwen3.8-flash-next-ud-iq4_xs-2gpu-256k','iq3':'qwen3.8-flash-next-iq3_s-2gpu-256k','27b':'qwen3.8-27b-thinking'}
PORTS={'iq4':8090,'iq3':8086,'27b':8080}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--model',choices=ALIASES,required=True);p.add_argument('--port',type=int,default=18091);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 root=Path('/opt/benchmark');fault=root/'services/llama-swap/GPU-FAULT';stop=a.out/'STOP';lock=threading.Lock();active=0
 key=next(x.split('=',1)[1].strip().strip('\"\'') for x in (root/'services/llama-swap/credentials.env').read_text().splitlines() if x.startswith('LOCAL_LLM_API_KEY='))
 def save_stop(reason):
  if not stop.exists():stop.write_text(reason)
 def metric_snapshot():
  if a.model!='27b':return None
  try:
   with urllib.request.urlopen('http://127.0.0.1:8080/metrics',timeout=3) as r:
    return '\n'.join(x for x in r.read().decode().splitlines() if not x.startswith('#') and any(k in x for k in ['request_prefill_time_seconds_','request_decode_time_seconds_','prompt_tokens_total','generation_tokens_total','request_queue_time_seconds_']))
  except Exception:return None
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def reply(self,status,obj):
   data=json.dumps(obj,allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  def do_GET(self):
   if self.path=='/status':self.reply(200,{'active':active,'stopped':stop.exists()});return
   self.reply(404,{'error':'not_found'})
  def do_POST(self):
   nonlocal active
   if self.path!='/v1/chat/completions':self.reply(404,{'error':'not_found'});return
   if stop.exists() or fault.exists():self.reply(503,{'error':'benchmark_stopped'});return
   with lock:
    if active:self.reply(429,{'error':'sequential_only'});return
    active+=1
   start=time.monotonic();wall=time.time();rid=str(time.time_ns());e=StreamEvidence(start);row={'id':rid,'start_time':wall,'model':a.model};before=metric_snapshot();content='';reasoning='';finish=None;last={};calls={}
   try:
    req=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));(a.out/(rid+'-client-request.json')).write_text(json.dumps(req,ensure_ascii=False))
    e=TerminalBenchEvidence(start,req)
    assert not req.get('stream'),'Harbor non-stream facade expected'
    req['model']=ALIASES[a.model];req.update(stream=True,stream_options={'include_usage':True},temperature=1.0,top_p=0.95,reasoning_effort='medium')
    req.setdefault('max_tokens',16384);req['chat_template_kwargs']={'enable_thinking':True,'preserve_thinking':True,'reasoning_effort':'medium'}
    req.update(top_k=20,min_p=0.0,repetition_penalty=1.0,presence_penalty=0.0)
    (a.out/(rid+'-upstream-request.json')).write_text(json.dumps(req,ensure_ascii=False))
    request=urllib.request.Request('http://127.0.0.1:18080/v1/chat/completions',data=json.dumps(req).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=1800) as response,(a.out/(rid+'-response.sse')).open('wb') as raw:
     assert response.status==200
     for line in response:
      raw.write(line);raw.flush()
      if not line.startswith(b'data:'):continue
      val=line[5:].strip().decode();e.event(val,time.monotonic())
      if val=='[DONE]':continue
      obj=json.loads(val,parse_constant=lambda _:(_ for _ in ()).throw(StopRun('nonfinite_json')));last=obj
      for c in obj.get('choices',[]):
       d=c.get('delta',{});content+=d.get('content') or '';reasoning+=d.get('reasoning_content') or d.get('reasoning') or ''
       if c.get('finish_reason'):finish=c['finish_reason']
       for tc in d.get('tool_calls',[]):
        t=calls.setdefault(tc.get('index',0),{'id':'','type':'function','function':{'name':'','arguments':''}})
        if tc.get('id'):t['id']=tc['id']
        for k,v in tc.get('function',{}).items():t['function'][k]+=v
    if a.model!='27b':e.validate()
    else:assert e.done and e.finishes and e.usage,'incomplete_vllm_SSE'
    msg={'role':'assistant','content':content}
    if reasoning:msg['reasoning_content']=reasoning
    if calls:msg['tool_calls']=[calls[k] for k in sorted(calls)]
    answer={'id':last.get('id',rid),'object':'chat.completion','created':int(wall),'model':ALIASES[a.model],'choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':e.usage}
    if e.timings:answer['timings']=e.timings
    (a.out/(rid+'-response.json')).write_text(json.dumps(answer,ensure_ascii=False,allow_nan=False));row.update(status=200,error=None)
    try:self.reply(200,answer)
    except (BrokenPipeError,ConnectionResetError):row['client_disconnected']=True # Official task timeout may cancel Harbor; preserve/drain upstream.
   except BaseException as exc:
    row.update(status=502,error=type(exc).__name__+': '+str(exc));save_stop(row['error'])
    if isinstance(exc,urllib.error.HTTPError):(a.out/(rid+'-error.bin')).write_bytes(exc.read())
    try:self.reply(502,{'error':row['error']})
    except (BrokenPipeError,ConnectionResetError):pass
   finally:
    row.update(e.metrics());row.update(duration_s=time.monotonic()-start,end_time=time.time(),vllm_metrics_before=before,vllm_metrics_after=metric_snapshot())
    with lock:
     with (a.out/'requests.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
     active-=1
 ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()
