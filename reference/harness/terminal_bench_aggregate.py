#!/usr/bin/env python3
"""Read-only evidence audit; writes derived review files only. No model calls."""
import argparse, collections, datetime, hashlib, json, statistics, time
from pathlib import Path

def read(p): return json.loads(p.read_text())
def lines(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def ts(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def duration(d): return ts(d['finished_at'])-ts(d['started_at']) if d and d.get('finished_at') else None
def stats(v):
    v=sorted(x for x in v if x is not None)
    return dict(n=len(v),sum=sum(v),mean=statistics.mean(v),median=statistics.median(v),p95=v[min(len(v)-1,int(.95*len(v)))],min=v[0],max=v[-1]) if v else dict(n=0)
def metric(s,name):
    vals=[float(x.split()[-1]) for x in (s or '').splitlines() if x.startswith(name+'{') or x.startswith(name+' ')]
    return sum(vals) if vals else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args();root=a.root
    state=read(root/'status.json');assert state['state']=='awaiting_review'
    completed=state['completed'];assert len(completed)==171 and state['held_trials']==9
    schedules=[x.get('schedule_label',x['label']) for x in completed];assert len(set(schedules))==171
    tasks=sorted({x['task'] for x in completed});assert len(tasks)==19
    assert collections.Counter((x['task'],x['model']) for x in completed)=={(t,m):3 for t in tasks for m in ('iq4','iq3','27b')}
    out=root/'final-review';out.mkdir(exist_ok=True)
    hashes={};calls=[];rows=[];errors=[]
    def capture(p):
        data=p.read_bytes();hashes[str(p.relative_to(root))]=hashlib.sha256(data).hexdigest();return data
    capture(root/'status.json')
    oracles={}
    for t in tasks:
        name='oracle-pilot-01' if t=='openssl-selfsigned-cert' else 'oracle-'+t
        ps=list((root/'oracle'/name).glob('*/result.json'));assert len(ps)==1
        d=json.loads(capture(ps[0]));assert not d.get('exception_info') and d['verifier_result']['rewards']['reward']==1
        oracles[t]=str(ps[0].relative_to(root))
    for ix,x in enumerate(completed):
        run=root/'runs'/x['label'];api=run/'api';result=json.loads(capture(Path(x['result'])))
        assert result['verifier_result']['rewards']==x['reward']
        assert result['agent_info']['name']=='terminus-2' and result['agent_info']['version']=='2.0.0'
        assert (result.get('exception_info') or {}).get('exception_type')==x.get('exception_type')
        reqs=[json.loads(z) for z in capture(api/'requests.jsonl').splitlines() if z.strip()]
        assert reqs and not (api/'STOP').exists()
        prep=x.get('preparation_s');prep_source='completed' if prep is not None else 'unrecorded'
        if prep is None and (run/'memory-preparation.json').exists():
            pd=json.loads(capture(run/'memory-preparation.json'));prep=pd['after']['at']-pd['at'];prep_source='memory-preparation timestamps'
        row={**x,'schedule_label':schedules[ix],'score':x['reward']['reward'],'preparation_s':prep,'preparation_source':prep_source,
             'elapsed_with_preparation_s':x['elapsed_s']+prep if prep is not None else None,
             'harbor_s':duration(result),'started_at':ts(result['started_at']),
             'phases_s':{k:duration(result.get(k)) for k in ('environment_setup','agent_setup','agent_execution','verifier')},
             'harbor_usage':{k:(result.get('agent_result') or {}).get(k) for k in ('n_input_tokens','n_cache_tokens','n_output_tokens')}}
        for j,c in enumerate(reqs):
            assert c['status']==200 and not c.get('error') and c['done'] and c['finish_reasons'] and c['usage'], (x['label'],c['id'])
            rid=c['id'];u=json.loads(capture(api/(rid+'-upstream-request.json')))
            expected={'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0,'repetition_penalty':1,'presence_penalty':0,'max_tokens':16384,'reasoning_effort':'medium','stream':True}
            assert all(u.get(k)==v for k,v in expected.items()), (x['label'],rid,'parameters')
            assert u['chat_template_kwargs']=={'enable_thinking':True,'preserve_thinking':True,'reasoning_effort':'medium'}
            done=False;fin=[];usage=None;timings=None;events=0
            for raw in capture(api/(rid+'-response.sse')).splitlines():
                if not raw.startswith(b'data:'):continue
                p=raw[5:].strip()
                if p==b'[DONE]':assert not done;done=True;continue
                assert not done
                d=json.loads(p);assert not d.get('error');events+=1
                if d.get('usage') is not None:usage=d['usage']
                if d.get('timings') is not None:timings=d['timings']
                fin += [z['finish_reason'] for z in d.get('choices',[]) if z.get('finish_reason') is not None]
            assert done and fin and usage and usage==c['usage'] and fin==c['finish_reasons']
            if x['model']!='27b':assert timings and timings==c['timings']
            vdelta={}
            if x['model']=='27b':
                for name in ('request_prefill_time_seconds_sum','request_decode_time_seconds_sum','prompt_tokens_total','generation_tokens_total'):
                    before=metric(c.get('vllm_metrics_before'),'vllm:'+name);after=metric(c.get('vllm_metrics_after'),'vllm:'+name)
                    if before is not None and after is not None:
                        assert after>=before;vdelta[name]=after-before
            calls.append({k:v for k,v in c.items() if not k.startswith('vllm_metrics_')} | {'label':x['label'],'task':x['task'],'first_api':j==0,'vllm_deltas':vdelta,'sse_events':events})
        tele=[json.loads(z) for z in capture(run/'telemetry.jsonl').splitlines() if z.strip()];assert len(tele)>1
        gaps=[b['at']-a['at'] for a,b in zip(tele,tele[1:])];assert all(v>0 for v in gaps)
        wh=sum((sum(g['power1_average'] for g in a['gpus'])+sum(g['power1_average'] for g in b['gpus']))/2/1e6*dt/3600 for a,b,dt in zip(tele,tele[1:],gaps))
        row['telemetry']={'n':len(tele),'span_s':tele[-1]['at']-tele[0]['at'],'max_gap_s':max(gaps),'sampled_gpu_wh':wh,
            'unsampled_elapsed_s':max(0,x['elapsed_s']-(tele[-1]['at']-tele[0]['at'])),
            'post_telemetry_api_s':max(0,max(c['end_time'] for c in reqs)-tele[-1]['at']),
            'peak_vram_bytes_each':[max(d['gpus'][i]['mem_info_vram_used'] for d in tele) for i in range(2)],
            'peak_two_gpu_w':max(sum(g['power1_average'] for g in d['gpus'])/1e6 for d in tele),
            'max_temp_c':max(g['temp1_input']/1000 for d in tele for g in d['gpus']),
            'min_mem_available':min(d['mem_available'] for d in tele),'max_swap_used':max(d['swap_used'] for d in tele),
            'min_disk_free':min(d['disk_free'] for d in tele),'fault_samples':sum(bool(d['fault']) for d in tele)}
        assert row['telemetry']['fault_samples']==0 and row['telemetry']['max_swap_used']<=512*2**20 and row['telemetry']['min_mem_available']>=8*2**30 and row['telemetry']['min_disk_free']>=5*2**30
        rows.append(row)
        if (ix+1)%20==0:print('audited',ix+1,flush=True)
    models={}
    for m in ('iq4','iq3','27b'):
        rs=[r for r in rows if r['model']==m];cs=[c for c in calls if c['model']==m]
        task_scores={t:[int(r['score']) for r in sorted(rs,key=lambda r:r['repetition']) if r['task']==t] for t in tasks}
        timing=[c['timings'] for c in cs if c.get('timings')]
        vd=[c for c in cs if len(c['vllm_deltas'])==4]
        def total(key):return sum(t.get(key,0) for t in timing)
        mm={'trials':len(rs),'passed':sum(r['score'] for r in rs),'task_scores':task_scores,
            'tasks_3of3':sum(sum(v)==3 for v in task_scores.values()),'tasks_1plus':sum(sum(v)>0 for v in task_scores.values()),
            'tasks_mixed':sum(0<sum(v)<3 for v in task_scores.values()),
            'repetition_passes':{str(i):sum(r['score'] for r in rs if r['repetition']==i) for i in (1,2,3)},
            'exceptions':dict(collections.Counter(r['exception_type'] for r in rs if r['exception_type'])),
            'timeout_passed':sum(r['score']==1 and r['exception_type']=='AgentTimeoutError' for r in rs),
            'elapsed_s':stats([r['elapsed_s'] for r in rs]),'preparation_s':stats([r['preparation_s'] for r in rs]),
            'elapsed_plus_known_preparation_s':sum(r['elapsed_s']+(r['preparation_s'] or 0) for r in rs),
            'success_elapsed_s':stats([r['elapsed_s'] for r in rs if r['score']==1]),'failure_elapsed_s':stats([r['elapsed_s'] for r in rs if r['score']==0]),
            'apis':len(cs),'client_disconnected':sum(bool(c.get('client_disconnected')) for c in cs),
            'upstream_tokens':{k:sum(c['usage'].get(k,0) for c in cs) for k in ('prompt_tokens','completion_tokens')},
            'cached_tokens_reported':sum(c['usage'].get('prompt_tokens_details',{}).get('cached_tokens',0) for c in cs),
            'cache_field_requests':sum('cached_tokens' in c['usage'].get('prompt_tokens_details',{}) for c in cs),
            'harbor_tokens':{k:sum(r['harbor_usage'][k] or 0 for r in rs) for k in ('n_input_tokens','n_cache_tokens','n_output_tokens')},
            'ttft_first_s':stats([c['ttft_s'] for c in cs if c['first_api']]),'ttft_later_s':stats([c['ttft_s'] for c in cs if not c['first_api']]),
            'ttft_cold_first_s':stats([c['ttft_s'] for c in cs if c['first_api'] and next(r for r in rs if r['label']==c['label'])['preparation_s'] is not None]),
            'observed_output_tps':sum(c['usage']['completion_tokens'] for c in cs)/sum(c['output_span_s'] for c in cs),
            'strata_prefill_tps':total('prompt_n')/(total('prompt_ms')/1000) if timing else None,
            'strata_decode_tps':total('predicted_n')/(total('predicted_ms')/1000) if timing else None,
            'vllm_paired_requests':len(vd),'vllm_deltas':{k:sum(c['vllm_deltas'][k] for c in vd) for k in ('request_prefill_time_seconds_sum','request_decode_time_seconds_sum','prompt_tokens_total','generation_tokens_total')},
            'sampled_gpu_wh':sum(r['telemetry']['sampled_gpu_wh'] for r in rs),'telemetry_span_s':sum(r['telemetry']['span_s'] for r in rs),
            'unsampled_elapsed_s':sum(r['telemetry']['unsampled_elapsed_s'] for r in rs),'post_telemetry_api_s':sum(r['telemetry']['post_telemetry_api_s'] for r in rs),
            'drain_unsampled_trials':sum(r['telemetry']['post_telemetry_api_s']>2 for r in rs),
            'max_telemetry_gap_s':max(r['telemetry']['max_gap_s'] for r in rs),
            'peak_vram_gib_each':[max(r['telemetry']['peak_vram_bytes_each'][i] for r in rs)/2**30 for i in range(2)],
            'peak_two_gpu_w':max(r['telemetry']['peak_two_gpu_w'] for r in rs),'max_temp_c':max(r['telemetry']['max_temp_c'] for r in rs),
            'min_mem_available_gib':min(r['telemetry']['min_mem_available'] for r in rs)/2**30,'max_swap_mib':max(r['telemetry']['max_swap_used'] for r in rs)/2**20,
            'guard_policies':dict(collections.Counter(c.get('repetition_policy','original') for c in cs)),
            'quote_exemption_requests':sum(bool(c.get('zero_quote_exemptions')) for c in cs)}
        models[m]=mm
    summary={'created_at':time.time(),'planned':180,'completed':171,'held':9,'tasks':19,'models':models,'blocked_tasks':state['blocked_tasks'],
        'replacements':[{'label':r['label'],'schedule_label':r['schedule_label']} for r in rows if r['label']!=r['schedule_label']],
        'earliest_harbor_start':min(r['started_at'] for r in rows),'runner_ended_at':state['ended_at'],
        'audit':{'passed':True,'raw_sse_requests':len(calls),'raw_sse_validation':'JSON/error/DONE/finish/usage; Strata timings; stored metric equality. Does not rerun historical repetition policy.', 'oracle_passes':oracles,'upstream_common_parameters_verified':True,'hashed_files':len(hashes)},
        'caveats':['First eight trials have different cache preparation; missing preparation is unknown, not zero.','GPU Wh excludes preparation, oracle, interruptions, gaps between trials and unsampled API drain.','vLLM missing cache token fields mean unavailable, not zero cache hits.']}
    for name,data in [('aggregate.json',summary),('trials.json',rows),('api-audit.json',calls),('source-sha256.json',hashes)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
