#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CONTRACT=ROOT/'docs/contracts/relayctx-session-evidence-overlay.md'; SCHEMA=ROOT/'docs/contracts/schemas/ctx-ovl-v1/relaylm-ctx-ovl-v1.schema.json'; CATALOG=ROOT/'docs/contracts/schemas/ctx-ovl-v1/schema-catalog.json'; VALID=ROOT/'docs/contracts/fixtures/ctx-ovl-v1/valid'; INVALID=ROOT/'docs/contracts/fixtures/ctx-ovl-v1/invalid'
TOKENS=['producer_artifact_ref','content_address_space','contract1_binding','evaluated_at < ttl_expires_at','session_id + partition_kind + partition_id','ContextSelection','CatchUpAttempt','RebuildEvent','SharedSceneProjection','watermark_advanced','RelayATN','PR #586','A digest alone is not a resolvable reference','same shared-scene partition and partition epoch','fail-closed or no-op outcome has no produced IDs','invalidation_scope_binding','max_total_candidate_bytes','max_overlay_records','unique within its own schema namespace','must be `current` and `admitted`','ctx_ovl_budget_policy_v1']
TOP={'CandidateArtifact':'relaylm.ctx_ovl_candidate_artifact.v1','PartitionEpochDescriptor':'relaylm.ctx_ovl_partition_epoch.v1','OverlayRecord':'relaylm.ctx_ovl_overlay_record.v1','CatchUpAttempt':'relaylm.ctx_ovl_catch_up_attempt.v1','ReflexSnapshot':'relaylm.ctx_ovl_reflex_snapshot.v1','WriteAttempt':'relaylm.ctx_ovl_write_attempt.v1','RebuildEvent':'relaylm.ctx_ovl_rebuild_event.v1','SharedSceneProjection':'relaylm.ctx_ovl_shared_scene_projection.v1','OverlayInvalidationEvent':'relaylm.ctx_ovl_overlay_invalidation_event.v1','ContextSelection':'relaylm.ctx_ovl_context_selection.v1'}
def main():
 f=[]; text=CONTRACT.read_text(); s=json.loads(SCHEMA.read_text()); c=json.loads(CATALOG.read_text()); defs=s.get('$defs',{})
 for x in TOKENS:
  if x not in text: f.append(f'missing contract token: {x}')
 for n,sid in TOP.items():
  if defs.get(n,{}).get('properties',{}).get('schema',{}).get('const')!=sid: f.append(f'{n} discriminator mismatch')
  if n not in text: f.append(f'{n} absent from prose')
 if {x['definition'] for x in c.get('schemas',[])}!=set(TOP): f.append('catalog definitions mismatch')
 v=[x for p in sorted(VALID.glob('*.json')) for x in json.loads(p.read_text()).get('cases',[])]; i=[x for p in sorted(INVALID.glob('*.json')) for x in json.loads(p.read_text()).get('cases',[])]
 if len(v)!=9: f.append(f'valid case count must be 9, found {len(v)}')
 if len(i)!=65: f.append(f'invalid case count must be 65, found {len(i)}')
 req={'projection_stale_authorization','projection_restricted_authorization','dangling_invalidation_target','invalidation_target_scope_mismatch','duplicate_artifact_id','duplicate_overlay_id','duplicate_partition_epoch_id','catch_up_output_count_exceeds_bound','catch_up_output_bytes_exceed_bound','rebuild_output_count_exceeds_bound','rebuild_output_bytes_exceed_bound','partition_visibility_mismatch','dangling_supersession_target','self_supersession_reference','supersession_cycle','dangling_quarantine_shadow_target','catch_up_budget_policy_mismatch','catch_up_budget_above_policy_cap','rebuild_budget_policy_mismatch','rebuild_budget_above_policy_cap'}
 if not req.issubset({x.get('name') for x in i}): f.append('required final invalid coverage missing')
 if f:
  print('CTX-OVL equivalence FAILED',file=sys.stderr)
  for x in f: print('-',x,file=sys.stderr)
  return 1
 print('CTX-OVL equivalence PASS: prose, 10 top-level schemas, catalog, and 74 matrix cases agree.'); return 0
if __name__=='__main__': raise SystemExit(main())
