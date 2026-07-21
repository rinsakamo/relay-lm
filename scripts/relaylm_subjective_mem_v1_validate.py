#!/usr/bin/env python3
"""Validate Shared Assessment / Subjective MEM v1 fixtures."""
import argparse,copy,hashlib,importlib.util,json,sys
from datetime import datetime
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
R=Path(__file__).resolve().parents[1]
S=R/'docs/contracts/schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json'; C=R/'docs/contracts/schemas/subjective-mem-v1/schema-catalog.json'
V=R/'docs/contracts/fixtures/subjective-mem-v1/valid'; I=R/'docs/contracts/fixtures/subjective-mem-v1/invalid'
SCHEMA_TO_DEF={'relaylm.shared_assessment_revision.v1':'SharedAssessmentRevision','relaylm.shared_assessment_current_state.v1':'SharedAssessmentCurrentState','relaylm.subjective_mem_decision.v1':'SubjectiveMemDecision','relaylm.subjective_mem_revision.v1':'SubjectiveMemRevision','relaylm.subjective_mem_current_state.v1':'SubjectiveMemCurrentState','relaylm.subjective_mem_relation.v1':'SubjectiveMemRelation','relaylm.subjective_mem_lifecycle_transition.v1':'SubjectiveMemLifecycleTransition'}
ALL_ERROR_IDS=set('''SUBJ_MEM_E_SCHEMA_INVALID SUBJ_MEM_E_DUPLICATE_TOP_LEVEL_ID SUBJ_MEM_E_DUPLICATE_ASSESSMENT_CURRENT_STATE SUBJ_MEM_E_DUPLICATE_MEMORY_CURRENT_STATE SUBJ_MEM_E_ASSESSMENT_DIGEST_MISMATCH SUBJ_MEM_E_ASSESSMENT_REVISION_DANGLING SUBJ_MEM_E_ASSESSMENT_CURRENT_MISSING SUBJ_MEM_E_ASSESSMENT_AUTHORIZATION_NOT_CURRENT SUBJ_MEM_E_ASSESSMENT_CURRENT_MISMATCH SUBJ_MEM_E_ASSESSMENT_SUPERSESSION_INVALID SUBJ_MEM_E_DECISION_ASSESSMENT_DANGLING SUBJ_MEM_E_DECISION_ASSESSMENT_RECEIPT_INVALID SUBJ_MEM_E_DECISION_TARGET_REQUIRED SUBJ_MEM_E_DECISION_TARGET_FORBIDDEN SUBJ_MEM_E_DECISION_RESULT_MEMORY_REQUIRED SUBJ_MEM_E_DECISION_RESULT_RELATION_REQUIRED SUBJ_MEM_E_DECISION_RESULT_FORBIDDEN SUBJ_MEM_E_DECISION_HOLD_REASON_REQUIRED SUBJ_MEM_E_DECISION_HOLD_REASON_FORBIDDEN SUBJ_MEM_E_DECISION_TARGET_DANGLING SUBJ_MEM_E_DECISION_TARGET_NOT_CURRENT SUBJ_MEM_E_DECISION_TARGET_CHARACTER_MISMATCH SUBJ_MEM_E_DECISION_TARGET_SCOPE_MISMATCH SUBJ_MEM_E_DECISION_CANDIDATE_DANGLING SUBJ_MEM_E_DECISION_RESULT_MEMORY_DANGLING SUBJ_MEM_E_DECISION_RESULT_CHARACTER_MISMATCH SUBJ_MEM_E_DECISION_RESULT_SCOPE_MISMATCH SUBJ_MEM_E_DECISION_RESULT_LINK_INVALID SUBJ_MEM_E_DECISION_RELATION_LINK_INVALID SUBJ_MEM_E_SCOPE_IDENTITY_UNTRUSTED SUBJ_MEM_E_SCOPE_BINDING_INCONSISTENT SUBJ_MEM_E_SCOPE_SNAPSHOT_MISMATCH SUBJ_MEM_E_MEM_ASSESSMENT_DANGLING SUBJ_MEM_E_GROUNDED_DIGEST_MISMATCH SUBJ_MEM_E_MEM_PREDECESSOR_INVALID SUBJ_MEM_E_MEM_AUTHORIZATION_INVALID SUBJ_MEM_E_MEM_RETRIEVAL_VISIBILITY_INVALID SUBJ_MEM_E_MEM_CURRENT_MISSING SUBJ_MEM_E_MEM_CURRENT_DANGLING SUBJ_MEM_E_MEM_CURRENT_MISMATCH SUBJ_MEM_E_MEM_RETRIEVAL_ELIGIBILITY_INVALID SUBJ_MEM_E_RELATION_SOURCE_DANGLING SUBJ_MEM_E_RELATION_TARGET_DANGLING SUBJ_MEM_E_RELATION_SELF_REFERENCE SUBJ_MEM_E_RELATION_CHARACTER_MISMATCH SUBJ_MEM_E_RELATION_SCOPE_MISMATCH SUBJ_MEM_E_RELATION_AUTHORIZATION_INVALID SUBJ_MEM_E_RELATION_CYCLE SUBJ_MEM_E_TRANSITION_FROM_DANGLING SUBJ_MEM_E_TRANSITION_TO_DANGLING SUBJ_MEM_E_TRANSITION_REVISION_INVALID SUBJ_MEM_E_TRANSITION_CHARACTER_MISMATCH SUBJ_MEM_E_TRANSITION_STATE_INVALID SUBJ_MEM_E_TRANSITION_STAGE_INVALID SUBJ_MEM_E_TRANSITION_AUTHORITY_INVALID SUBJ_MEM_E_TRANSITION_PAYLOAD_MUTATION SUBJ_MEM_E_TIME_ORDER_INVALID'''.split())
TR={'reinforce','refine','reinterpret','supersede','contradict','relate'}; TF={'create','hold','abstain','leave_as_evidence'}; MR={'create','reinforce','refine','reinterpret','supersede','contradict'}; NR={'hold','abstain','leave_as_evidence'}; VIS={'active','pinned'}; SR={'supersedes','reinterprets'}
def load(p): return json.loads(p.read_text())
def dt(x): return datetime.fromisoformat(x.replace('Z','+00:00'))
def sha(x): return hashlib.sha256(x.encode()).hexdigest() if isinstance(x,str) else None
def mk(r): r=r or {}; return r.get('memory_id'),r.get('memory_revision')
def setp(x,p,v):
 c=x
 for k in p[:-1]: c=c[k]
 c[p[-1]]=v
def mutate(rs,ms):
 rs=copy.deepcopy(rs)
 for m in ms:
  o=m['op']
  if o=='set': setp(rs[m['record_index']],m['path'],copy.deepcopy(m['value']))
  elif o=='append_copy': rs.append(copy.deepcopy(rs[m['record_index']]))
  elif o=='append_record': rs.append(copy.deepcopy(m['record']))
  elif o=='delete': del rs[m['record_index']]
  else: raise ValueError(o)
 return rs
def base(p,path):
 if 'base_records' in p:return copy.deepcopy(p['base_records'])
 q=load((path.parent/p['base_fixture']).resolve()); return copy.deepcopy(q['base_records'])
def materialize(p,c,path):
 rs=copy.deepcopy(c['records']) if 'records' in c else base(p,path)
 if 'record_indices' in c: rs=[rs[i] for i in c['record_indices']]
 return mutate(rs,c.get('mutations',[]))
def scopeok(s):
 k=s.get('scope_kind'); p=s.get('participant_id_or_null'); r=s.get('relationship_id_or_null'); n=s.get('scene_id_or_null'); a=s.get('audience_class')
 return (k=='character_private' and p is None and r is None and n is None and a=='private') or (k=='participant' and p is not None and r is None and n is None and a=='trusted_participant') or (k=='relationship' and p is not None and r is not None and n is None and a=='relationship_bounded') or (k=='scene' and r is None and n is not None and a=='scene_bounded')
def snapok(m):
 k=m['scope_binding']['scope_kind']; s=m['formation_snapshot']; return not(k=='relationship' and s['relationship_revision_or_null'] is None or k=='scene' and s['scene_policy_revision_or_null'] is None)
def ident(r):
 s=r.get('schema')
 if s=='relaylm.shared_assessment_revision.v1': return s,r.get('assessment_id'),r.get('assessment_revision')
 if s=='relaylm.shared_assessment_current_state.v1': return s,r.get('assessment_state_id')
 if s=='relaylm.subjective_mem_decision.v1': return s,r.get('decision_id')
 if s=='relaylm.subjective_mem_revision.v1': return s,r.get('memory_id'),r.get('memory_revision')
 if s=='relaylm.subjective_mem_current_state.v1': return s,r.get('memory_state_id')
 if s=='relaylm.subjective_mem_relation.v1': return s,r.get('relation_id')
 if s=='relaylm.subjective_mem_lifecycle_transition.v1': return s,r.get('transition_id')
def cycle(edges):
 g={}
 for a,b in edges:g.setdefault(a,set()).add(b)
 seen=set(); active=set()
 def f(x):
  if x in active:return True
  if x in seen:return False
  active.add(x)
  if any(f(y) for y in g.get(x,())):return True
  active.remove(x);seen.add(x);return False
 return any(f(x) for x in list(g))
def validate_records(rs,schema=None):
 schema=schema or load(S); fc=FormatChecker()
 for r in rs:
  d=SCHEMA_TO_DEF.get(r.get('schema'))
  if not d or next(Draft202012Validator({'$ref':f'#/$defs/{d}','$defs':schema['$defs']},format_checker=fc).iter_errors(r),None): return {'SUBJ_MEM_E_SCHEMA_INVALID'}
 e=set(); seen=set(); ac={}; mc={}
 for r in rs:
  i=ident(r)
  if i in seen:e.add('SUBJ_MEM_E_DUPLICATE_TOP_LEVEL_ID')
  seen.add(i)
  if r['schema']=='relaylm.shared_assessment_current_state.v1': ac[r['assessment_id']]=ac.get(r['assessment_id'],0)+1
  if r['schema']=='relaylm.subjective_mem_current_state.v1': k=(r['character_id'],r['memory_id']);mc[k]=mc.get(k,0)+1
 if any(x>1 for x in ac.values()):e.add('SUBJ_MEM_E_DUPLICATE_ASSESSMENT_CURRENT_STATE')
 if any(x>1 for x in mc.values()):e.add('SUBJ_MEM_E_DUPLICATE_MEMORY_CURRENT_STATE')
 A={};AS={};D={};M={};MS={};L={};T={}
 for r in rs:
  s=r['schema']
  if s=='relaylm.shared_assessment_revision.v1':A.setdefault((r['assessment_id'],r['assessment_revision']),r)
  elif s=='relaylm.shared_assessment_current_state.v1':AS.setdefault(r['assessment_id'],r)
  elif s=='relaylm.subjective_mem_decision.v1':D.setdefault(r['decision_id'],r)
  elif s=='relaylm.subjective_mem_revision.v1':M.setdefault((r['memory_id'],r['memory_revision']),r)
  elif s=='relaylm.subjective_mem_current_state.v1':MS.setdefault((r['character_id'],r['memory_id']),r)
  elif s=='relaylm.subjective_mem_relation.v1':L.setdefault(r['relation_id'],r)
  elif s=='relaylm.subjective_mem_lifecycle_transition.v1':T.setdefault(r['transition_id'],r)
 ar={}
 for (a,v),r in A.items():
  ar.setdefault(a,[]).append(v)
  if sha(r['supported_content'])!=r['supported_content_digest']:e.add('SUBJ_MEM_E_ASSESSMENT_DIGEST_MISMATCH')
  p=r['supersedes_assessment_revision_or_null']
  if v==1 and p is not None or v>1 and (p!=v-1 or (a,p) not in A):e.add('SUBJ_MEM_E_ASSESSMENT_SUPERSESSION_INVALID')
  if p and dt(r['created_at'])<=dt(A[(a,p)]['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
 for a in ar:
  if a not in AS:e.add('SUBJ_MEM_E_ASSESSMENT_CURRENT_MISSING')
 for a,s in AS.items():
  r=A.get((a,s['current_revision']))
  if not r:e.add('SUBJ_MEM_E_ASSESSMENT_REVISION_DANGLING')
  want={'active':'current_admitted','restricted':'restricted','superseded':'restricted','purged':'purged'}.get(s['lifecycle_state'])
  if s['authorization_state']!=want:e.add('SUBJ_MEM_E_ASSESSMENT_AUTHORIZATION_NOT_CURRENT' if s['lifecycle_state']=='active' else 'SUBJ_MEM_E_ASSESSMENT_CURRENT_MISMATCH')
  if r and s['current_revision']!=max(ar.get(a,[])):e.add('SUBJ_MEM_E_ASSESSMENT_CURRENT_MISMATCH')
  if r and dt(s['updated_at'])<dt(r['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
 def alat(a,w):
  z=[v for (x,v),r in A.items() if x==a and dt(r['created_at'])<=w];return max(z) if z else None
 mr={}
 for (m,v),r in M.items():mr.setdefault((r['character_id'],m),[]).append(v)
 def mlat(c,m,w):
  z=[v for (x,v),r in M.items() if x==m and r['character_id']==c and dt(r['created_at'])<=w];return max(z) if z else None
 for d in D.values():
  q=d['assessment_ref'];a=A.get((q['assessment_id'],q['assessment_revision']));w=dt(d['decided_at'])
  if not a:e.add('SUBJ_MEM_E_DECISION_ASSESSMENT_DANGLING')
  else:
   p=d['assessment_authorization_receipt']
   if q['supported_content_digest']!=a['supported_content_digest'] or p['current_revision_at_decision']!=q['assessment_revision'] or alat(q['assessment_id'],w)!=q['assessment_revision']:e.add('SUBJ_MEM_E_DECISION_ASSESSMENT_RECEIPT_INVALID')
   if w<dt(a['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
  o=d['outcome'];t=d['target_memory_ref_or_null'];r=d['result_memory_ref_or_null'];x=d['result_relation_id_or_null'];h=d['hold_reason_or_null']
  if o in TR and t is None:e.add('SUBJ_MEM_E_DECISION_TARGET_REQUIRED')
  if o in TF and t is not None:e.add('SUBJ_MEM_E_DECISION_TARGET_FORBIDDEN')
  if o in MR and r is None:e.add('SUBJ_MEM_E_DECISION_RESULT_MEMORY_REQUIRED')
  if o=='relate' and x is None:e.add('SUBJ_MEM_E_DECISION_RESULT_RELATION_REQUIRED')
  if o in MR and x is not None or o=='relate' and r is not None or o in NR and (r is not None or x is not None):e.add('SUBJ_MEM_E_DECISION_RESULT_FORBIDDEN')
  if o=='hold' and h is None:e.add('SUBJ_MEM_E_DECISION_HOLD_REASON_REQUIRED')
  if o!='hold' and h is not None:e.add('SUBJ_MEM_E_DECISION_HOLD_REASON_FORBIDDEN')
  tm=M.get(mk(t)) if t else None
  if t:
   if not tm:e.add('SUBJ_MEM_E_DECISION_TARGET_DANGLING')
   else:
    if mlat(d['character_id'],tm['memory_id'],w)!=tm['memory_revision'] or tm['lifecycle_state'] not in VIS:e.add('SUBJ_MEM_E_DECISION_TARGET_NOT_CURRENT')
    if tm['character_id']!=d['character_id']:e.add('SUBJ_MEM_E_DECISION_TARGET_CHARACTER_MISMATCH')
    if tm['scope_binding']!=d['scope_binding']:e.add('SUBJ_MEM_E_DECISION_TARGET_SCOPE_MISMATCH')
  for z in d['candidate_memory_refs']:
   if mk(z) not in M:e.add('SUBJ_MEM_E_DECISION_CANDIDATE_DANGLING')
  rm=M.get(mk(r)) if r else None
  if r:
   if not rm:e.add('SUBJ_MEM_E_DECISION_RESULT_MEMORY_DANGLING')
   else:
    if rm['character_id']!=d['character_id']:e.add('SUBJ_MEM_E_DECISION_RESULT_CHARACTER_MISMATCH')
    if rm['scope_binding']!=d['scope_binding']:e.add('SUBJ_MEM_E_DECISION_RESULT_SCOPE_MISMATCH')
    ok=rm['authorization_ref']=={'authority_kind':'formation_decision','authority_id':d['decision_id']}
    if o=='create':ok=ok and rm['memory_revision']==1 and rm['predecessor_revision_or_null'] is None
    elif tm:ok=ok and rm['memory_id']==tm['memory_id'] and rm['memory_revision']==tm['memory_revision']+1 and rm['predecessor_revision_or_null']==tm['memory_revision']
    if not ok:e.add('SUBJ_MEM_E_DECISION_RESULT_LINK_INVALID')
    if w>dt(rm['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
  if x:
   l=L.get(x)
   if not l or l['authorizing_decision_id']!=d['decision_id'] or mk(t) not in {mk(l['source_memory_ref']),mk(l['target_memory_ref'])}:e.add('SUBJ_MEM_E_DECISION_RELATION_LINK_INVALID')
   elif w>dt(l['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
  if not scopeok(d['scope_binding']):e.add('SUBJ_MEM_E_SCOPE_BINDING_INCONSISTENT')
  if d['scope_binding']['scope_kind'] in {'participant','relationship'} and d['scope_binding']['identity_status']!='known':e.add('SUBJ_MEM_E_SCOPE_IDENTITY_UNTRUSTED')
 for (m,v),r in M.items():
  q=r['grounded_assessment_ref'];a=A.get((q['assessment_id'],q['assessment_revision']));dg=a['supported_content_digest'] if a else None
  if not a:e.add('SUBJ_MEM_E_MEM_ASSESSMENT_DANGLING')
  if not a or q['supported_content_digest']!=dg or r['grounded_content_digest']!=dg or sha(r['grounded_content'])!=r['grounded_content_digest'] or a and r['grounded_content']!=a['supported_content']:e.add('SUBJ_MEM_E_GROUNDED_DIGEST_MISMATCH')
  p=r['predecessor_revision_or_null']
  if v==1 and p is not None or v>1 and (p!=v-1 or (m,p) not in M):e.add('SUBJ_MEM_E_MEM_PREDECESSOR_INVALID')
  elif p and dt(r['created_at'])<=dt(M[(m,p)]['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
  if r['retrieval_visible']!=(r['lifecycle_state'] in VIS):e.add('SUBJ_MEM_E_MEM_RETRIEVAL_VISIBILITY_INVALID')
  if not scopeok(r['scope_binding']):e.add('SUBJ_MEM_E_SCOPE_BINDING_INCONSISTENT')
  if r['scope_binding']['scope_kind'] in {'participant','relationship'} and r['scope_binding']['identity_status']!='known':e.add('SUBJ_MEM_E_SCOPE_IDENTITY_UNTRUSTED')
  if not snapok(r):e.add('SUBJ_MEM_E_SCOPE_SNAPSHOT_MISMATCH')
  q=r['authorization_ref'];z=D.get(q['authority_id']) if q['authority_kind']=='formation_decision' else T.get(q['authority_id'])
  if q['authority_kind']=='formation_decision' and (not z or mk(z['result_memory_ref_or_null'])!=(m,v)) or q['authority_kind']=='lifecycle_transition' and (not z or (z['memory_id'],z['to_revision'])!=(m,v)):e.add('SUBJ_MEM_E_MEM_AUTHORIZATION_INVALID')
 for k in mr:
  if k not in MS:e.add('SUBJ_MEM_E_MEM_CURRENT_MISSING')
 for (c,m),s in MS.items():
  r=M.get((m,s['current_revision']))
  if not r:e.add('SUBJ_MEM_E_MEM_CURRENT_DANGLING')
  elif r['character_id']!=c or r['lifecycle_state']!=s['lifecycle_state'] or s['current_revision']!=max(mr.get((c,m),[])):e.add('SUBJ_MEM_E_MEM_CURRENT_MISMATCH')
  if r and dt(s['updated_at'])<dt(r['created_at']):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
  if s['retrieval_eligible']!=bool(r and s['lifecycle_state'] in VIS and s['mutation_state']=='none'):e.add('SUBJ_MEM_E_MEM_RETRIEVAL_ELIGIBILITY_INVALID')
 edges=[]
 for l in L.values():
  a,b=mk(l['source_memory_ref']),mk(l['target_memory_ref']);x,y=M.get(a),M.get(b)
  if not x:e.add('SUBJ_MEM_E_RELATION_SOURCE_DANGLING')
  if not y:e.add('SUBJ_MEM_E_RELATION_TARGET_DANGLING')
  if a==b:e.add('SUBJ_MEM_E_RELATION_SELF_REFERENCE')
  if x and y:
   if l['character_id']!=x['character_id'] or l['character_id']!=y['character_id']:e.add('SUBJ_MEM_E_RELATION_CHARACTER_MISMATCH')
   if x['scope_binding']!=y['scope_binding']:e.add('SUBJ_MEM_E_RELATION_SCOPE_MISMATCH')
   if dt(l['created_at'])<max(dt(x['created_at']),dt(y['created_at'])):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
   if l['relation_type'] in SR:edges.append((a,b))
  d=D.get(l['authorizing_decision_id'])
  if not d or d['result_relation_id_or_null']!=l['relation_id']:e.add('SUBJ_MEM_E_RELATION_AUTHORIZATION_INVALID')
 if cycle(edges):e.add('SUBJ_MEM_E_RELATION_CYCLE')
 states={'correct':('active','active'),'forget':('active','hidden'),'restore':('hidden','active'),'consolidate':('active','active'),'pin':('active','pinned'),'unpin':('pinned','active')};stages={'consolidate':('primary','secondary')};auth={'correct':{'user_management','operator'},'forget':{'user_management','operator'},'restore':{'user_management','operator'},'pin':{'user_management','operator'},'unpin':{'user_management','operator'},'consolidate':{'user_management','operator','relaymem_policy'}}
 common={'memory_id','character_id','memory_kind','scope_binding','formation_snapshot'}; frozen=common|{'grounded_assessment_ref','grounded_content','grounded_content_digest','subjective_meaning','strength'}
 for t in T.values():
  a,b=M.get((t['memory_id'],t['from_revision'])),M.get((t['memory_id'],t['to_revision']))
  if not a:e.add('SUBJ_MEM_E_TRANSITION_FROM_DANGLING')
  if not b:e.add('SUBJ_MEM_E_TRANSITION_TO_DANGLING')
  if t['to_revision']!=t['from_revision']+1:e.add('SUBJ_MEM_E_TRANSITION_REVISION_INVALID')
  if not a or not b:continue
  if t['character_id']!=a['character_id'] or t['character_id']!=b['character_id']:e.add('SUBJ_MEM_E_TRANSITION_CHARACTER_MISMATCH')
  o=t['operation'];sp=(t['from_lifecycle_state'],t['to_lifecycle_state'])
  if sp!=(a['lifecycle_state'],b['lifecycle_state']) or sp!=states[o]:e.add('SUBJ_MEM_E_TRANSITION_STATE_INVALID')
  gp=(t['from_formation_stage'],t['to_formation_stage']);actual=(a['formation_stage'],b['formation_stage']);want=stages.get(o)
  if gp!=actual or want and gp!=want or not want and gp[0]!=gp[1]:e.add('SUBJ_MEM_E_TRANSITION_STAGE_INVALID')
  if t['authorized_by'] not in auth[o]:e.add('SUBJ_MEM_E_TRANSITION_AUTHORITY_INVALID')
  if any(a[k]!=b[k] for k in (common if o=='correct' else frozen)) or o!='consolidate' and a['formation_stage']!=b['formation_stage']:e.add('SUBJ_MEM_E_TRANSITION_PAYLOAD_MUTATION')
  if not(dt(a['created_at'])<=dt(t['committed_at'])<=dt(b['created_at'])):e.add('SUBJ_MEM_E_TIME_ORDER_INVALID')
 return e
def cases(d):
 for p in sorted(d.glob('*.json')):
  q=load(p)
  for c in q.get('cases',[]):yield p,q,c
def suite():
 s=load(S);f=[];vc=ic=0
 for p,q,c in cases(V):
  vc+=1;a=validate_records(materialize(q,c,p),s)
  if a:f.append(f"valid {p.name}:{c['name']} produced {sorted(a)}")
 for p,q,c in cases(I):
  ic+=1;a=validate_records(materialize(q,c,p),s);x=set(c['expected_error_ids'])
  if a!=x:f.append(f"invalid {p.name}:{c['name']} expected {sorted(x)} got {sorted(a)}")
 return vc,ic,f
def selftest():
 b=load(V/'matrix.json')['base_records'];s=load(S);f=[]
 for m,x in [([{'op':'set','record_index':3,'path':['result_memory_ref_or_null','memory_id'],'value':'missing'}],'SUBJ_MEM_E_DECISION_RESULT_MEMORY_DANGLING'),([{'op':'append_copy','record_index':2},{'op':'set','record_index':15,'path':['assessment_state_id'],'value':'other'}],'SUBJ_MEM_E_DUPLICATE_ASSESSMENT_CURRENT_STATE'),([{'op':'set','record_index':0,'path':['supported_content_digest'],'value':'f'*64}],'SUBJ_MEM_E_ASSESSMENT_DIGEST_MISMATCH'),([{'op':'set','record_index':10,'path':['subjective_meaning'],'value':'illicit'}],'SUBJ_MEM_E_TRANSITION_PAYLOAD_MUTATION'),([{'op':'set','record_index':11,'path':['decided_at'],'value':'2026-07-21T00:13:00Z'}],'SUBJ_MEM_E_DECISION_TARGET_NOT_CURRENT')]:
  if x not in validate_records(mutate(b,m),s):f.append(x)
 return f
def main():
 a=argparse.ArgumentParser();a.add_argument('--self-test',action='store_true');z=a.parse_args()
 try:
  Draft202012Validator.check_schema(load(S));m={x['schema']:x['definition'] for x in load(C)['schemas']}
  if m!=SCHEMA_TO_DEF:raise ValueError(m)
 except Exception as x:print(f'ERROR: contract schema setup failed: {x}',file=sys.stderr);return 1
 v,i,f=suite();f+=selftest() if z.self_test else []
 if f:
  for x in f:print('ERROR:',x,file=sys.stderr)
  return 1
 print(f"subjective-mem v1 validation{' + self-test' if z.self_test else ''}: PASS ({v} valid, {i} invalid)");return 0
if __name__=='__main__':raise SystemExit(main())
