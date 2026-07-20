#!/usr/bin/env python3
"""Validate the strict RelayCTX Session Evidence Overlay v1 contract matrices."""
from __future__ import annotations
import argparse, json, re, sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

ROOT=Path(__file__).resolve().parents[1]
SCHEMA_PATH=ROOT/'docs/contracts/schemas/ctx-ovl-v1/relaylm-ctx-ovl-v1.schema.json'
CATALOG_PATH=ROOT/'docs/contracts/schemas/ctx-ovl-v1/schema-catalog.json'
VALID_DIR=ROOT/'docs/contracts/fixtures/ctx-ovl-v1/valid'
INVALID_DIR=ROOT/'docs/contracts/fixtures/ctx-ovl-v1/invalid'

CURATED={
 ('ContextSelection','required','evaluated_at'):'CTX_OVL_E_MISSING_EVALUATED_AT',
 ('SharedSceneProjection','required','evaluated_at'):'CTX_OVL_E_MISSING_EVALUATED_AT',
 ('CatchUpAttempt','required','evaluated_at'):'CTX_OVL_E_MISSING_EVALUATED_AT',
 ('RebuildEvent','required','evaluated_at'):'CTX_OVL_E_MISSING_EVALUATED_AT',
 ('RebuildEvent','const','durable_state_claimed'):'CTX_OVL_E_REBUILD_NO_DURABLE_CLAIM',
 ('CatchUpAttempt','const','completeness_claimed_from'):'CTX_OVL_E_CATCH_UP_TIMESTAMP_ONLY',
 ('WriteAttempt','const','target_authority_domain'):'CTX_OVL_E_TARGET_AUTHORITY_DOMAIN_FIXED',
}

def synth(defn:str, kind:str, key:str)->str:
    n=re.sub(r'[^A-Za-z0-9]+','_',key).strip('_').upper() or 'ROOT'
    return f'CTX_OVL_E_SCHEMA_{defn.upper()}_{kind.upper()}_{n}'

def dt(v:str)->datetime:
    return datetime.fromisoformat(v.replace('Z','+00:00'))

@dataclass(frozen=True)
class Err:
    error_id:str
    detail:str
    record_index:int|None=None

class Validator:
    def __init__(self):
        self.schema=json.loads(SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(self.schema)
        self.catalog=json.loads(CATALOG_PATH.read_text())
        if self.catalog['bundle'] != self.schema['$id']:
            raise ValueError('catalog bundle mismatch')
        self.defs=self.schema['$defs']
        self.schema_map={v.get('properties',{}).get('schema',{}).get('const'):k for k,v in self.defs.items() if v.get('properties',{}).get('schema',{}).get('const')}
        for entry in self.catalog['schemas']:
            if entry['definition'] not in self.defs:
                raise ValueError(f"catalog missing definition {entry['definition']}")
            expected=f"{self.schema['$id']}#/$defs/{entry['definition']}"
            if entry['id'] != expected:
                raise ValueError(f"catalog id mismatch for {entry['definition']}")
        self.fc=FormatChecker()

    def schema_validator(self,name:str):
        return Draft202012Validator({'$ref':f'#/$defs/{name}','$defs':self.defs},format_checker=self.fc)

    def classify(self,name:str,e)->str:
        kind=str(e.validator)
        path='/'.join(str(p) for p in e.absolute_path)
        if kind=='required':
            m=re.search(r"'([^']+)' is a required property",e.message)
            key=m.group(1) if m else 'unknown'
        elif kind=='additionalProperties':
            key=path or 'root'
        else:
            key=path or 'root'
        return CURATED.get((name,kind,key),synth(name,kind,key))

    def validate_case(self,case:dict[str,Any])->list[Err]:
        records=case.get('records')
        if not isinstance(records,list): return [Err('CTX_OVL_E_FIXTURE_MALFORMED','records must be an array')]
        errors:list[Err]=[]; invalid_indices:set[int]=set(); defs_by_index={}
        for i,r in enumerate(records):
            if not isinstance(r,dict):
                errors.append(Err('CTX_OVL_E_RECORD_NOT_OBJECT',f'record[{i}] is not an object',i)); invalid_indices.add(i); continue
            sid=r.get('schema'); name=self.schema_map.get(sid)
            if not sid:
                errors.append(Err('CTX_OVL_E_RECORD_MISSING_DISCRIMINATOR',f'record[{i}] missing schema',i)); invalid_indices.add(i); continue
            if not name:
                errors.append(Err('CTX_OVL_E_RECORD_UNKNOWN_SCHEMA',f'record[{i}] unknown schema {sid}',i)); invalid_indices.add(i); continue
            defs_by_index[i]=name
            serr=list(self.schema_validator(name).iter_errors(r))
            if serr: invalid_indices.add(i)
            for e in serr:
                errors.append(Err(self.classify(name,e),f'record[{i}] {e.message}',i))
        errors.extend(self.custom(records,invalid_indices))
        return errors

    def custom(self,records:list[dict[str,Any]],badidx:set[int])->list[Err]:
        out:list[Err]=[]
        def valid_records(schema):
            return [(i,r) for i,r in enumerate(records) if i not in badidx and isinstance(r,dict) and r.get('schema')==schema]
        id_fields={'relaylm.ctx_ovl_candidate_artifact.v1':'artifact_id','relaylm.ctx_ovl_partition_epoch.v1':'partition_epoch_descriptor_id','relaylm.ctx_ovl_overlay_record.v1':'overlay_record_id','relaylm.ctx_ovl_catch_up_attempt.v1':'catch_up_attempt_id','relaylm.ctx_ovl_reflex_snapshot.v1':'reflex_snapshot_id','relaylm.ctx_ovl_write_attempt.v1':'write_attempt_id','relaylm.ctx_ovl_rebuild_event.v1':'rebuild_event_id','relaylm.ctx_ovl_shared_scene_projection.v1':'shared_scene_projection_id','relaylm.ctx_ovl_overlay_invalidation_event.v1':'invalidation_event_id','relaylm.ctx_ovl_context_selection.v1':'selection_id'}
        for sid,field in id_fields.items():
            seen=set()
            for idx,r in valid_records(sid):
                value=r.get(field)
                if value in seen: out.append(Err('CTX_OVL_E_DUPLICATE_RECORD_ID',f'duplicate {sid} {field}={value}',idx))
                seen.add(value)
        arts={r['artifact_id']:(i,r) for i,r in valid_records('relaylm.ctx_ovl_candidate_artifact.v1')}
        raw_ov_ids={r.get('overlay_record_id') for r in records if isinstance(r,dict) and r.get('schema')=='relaylm.ctx_ovl_overlay_record.v1'}
        ovs={r['overlay_record_id']:(i,r) for i,r in valid_records('relaylm.ctx_ovl_overlay_record.v1')}
        eps={r['partition_epoch_descriptor_id']:(i,r) for i,r in valid_records('relaylm.ctx_ovl_partition_epoch.v1')}
        selections=valid_records('relaylm.ctx_ovl_context_selection.v1')
        projections=valid_records('relaylm.ctx_ovl_shared_scene_projection.v1')
        catchups=valid_records('relaylm.ctx_ovl_catch_up_attempt.v1')
        rebuilds=valid_records('relaylm.ctx_ovl_rebuild_event.v1')
        invalidations=valid_records('relaylm.ctx_ovl_overlay_invalidation_event.v1')
        writes=valid_records('relaylm.ctx_ovl_write_attempt.v1')

        # Partition epoch references and uniqueness are scoped to a true partition instance.
        active={}
        for _,e in eps.values():
            if e.get('epoch_status')=='active':
                key=(e.get('session_id'),e.get('partition_kind'),e.get('partition_id'))
                active.setdefault(key,[]).append(e.get('partition_epoch_descriptor_id'))
        for key,ids in active.items():
            if len(ids)>1: out.append(Err('CTX_OVL_E_MULTIPLE_ACTIVE_EPOCHS_FOR_PARTITION',f'{key} has active epochs {ids}'))
        def epoch_check(owner:dict, ref:dict|None, expected_kind:str|None=None):
            if not ref: return
            target=eps.get(ref.get('partition_epoch_descriptor_id'))
            if not target: out.append(Err('CTX_OVL_E_DANGLING_PARTITION_EPOCH',f"dangling epoch {ref.get('partition_epoch_descriptor_id')}")); return
            _,e=target
            if e.get('session_id')!=owner.get('session_id'): out.append(Err('CTX_OVL_E_CROSS_SESSION_EPOCH','epoch session mismatch'))
            kind=expected_kind or owner.get('partition_kind')
            if kind and e.get('partition_kind')!=kind: out.append(Err('CTX_OVL_E_PARTITION_KIND_MISMATCH','epoch kind mismatch'))
            if owner.get('partition_id') and e.get('partition_id')!=owner.get('partition_id'): out.append(Err('CTX_OVL_E_PARTITION_INSTANCE_MISMATCH','epoch partition mismatch'))
            if e.get('epoch_status')!='active' or e.get('epoch_sequence')!=ref.get('epoch_sequence'): out.append(Err('CTX_OVL_E_STALE_PARTITION_EPOCH','epoch is not current'))
        for _,r in ovs.values(): epoch_check(r,r.get('partition_epoch_ref'))
        for _,p in projections: epoch_check(p,p.get('partition_epoch_ref'),'shared_scene')

        # Overlay internal bindings, candidate resolution, authorization and lifecycle.
        for oid,(idx,r) in ovs.items():
            sp=r.get('source_provenance') or {}; b=r.get('contract1_binding') or {}; a=r.get('last_validated_authorization') or {}; env=r.get('candidate_envelope') or {}; pref=env.get('producer_artifact_ref') or {}
            if sp.get('source_access_state_at_admission')!='admitted': out.append(Err('CTX_OVL_E_SOURCE_PROVENANCE_NOT_ADMITTED',f'{oid} source was not admitted',idx))
            if not (b.get('source_event_id')==sp.get('source_event_id') and b.get('evidence_space_id')==sp.get('evidence_space_id') and b.get('change_partition_id')==a.get('change_partition_id') and b.get('partition_epoch_id')==a.get('partition_epoch_id') and b.get('authority_snapshot_digest')==a.get('authority_snapshot_digest')):
                out.append(Err('CTX_OVL_E_CONTRACT1_BINDING_MISMATCH',f'{oid} Contract 1 binding mismatch',idx))
            sidecar=r.get('candidate_basis')=='validated_sidecar'
            expected_env='validated_sidecar_envelope' if sidecar else 'deterministic_operation_envelope'
            expected_artifact='validated_sidecar' if sidecar else 'deterministic_operation_result'
            if env.get('envelope_kind')!=expected_env:
                out.append(Err('CTX_OVL_E_CANDIDATE_BASIS_KIND_MISMATCH',f'{oid} candidate basis/envelope mismatch',idx))
            elif pref.get('artifact_kind')!=expected_artifact:
                out.append(Err('CTX_OVL_E_CANDIDATE_ARTIFACT_KIND_MISMATCH',f'{oid} envelope/artifact kind mismatch',idx))
            target=arts.get(pref.get('artifact_id'))
            if target is None:
                out.append(Err('CTX_OVL_E_UNRESOLVABLE_CANDIDATE_ARTIFACT',f'{oid} artifact does not resolve',idx))
            else:
                _,ar=target
                if pref.get('artifact_kind')!=ar.get('artifact_kind'):
                    out.append(Err('CTX_OVL_E_CANDIDATE_ARTIFACT_KIND_MISMATCH',f'{oid} artifact kind mismatch',idx))
                scope_keys=('session_id','source_event_id','evidence_space_id')
                if pref.get('producer_component')!=ar.get('producer_component') or pref.get('authority_domain')!=ar.get('authority_domain'):
                    out.append(Err('CTX_OVL_E_CANDIDATE_ARTIFACT_PRODUCER_MISMATCH',f'{oid} artifact producer/authority mismatch',idx))
                if any(pref.get(k)!=ar.get(k) for k in scope_keys) or pref.get('session_id')!=r.get('session_id') or pref.get('source_event_id')!=sp.get('source_event_id') or pref.get('evidence_space_id')!=sp.get('evidence_space_id'):
                    out.append(Err('CTX_OVL_E_CANDIDATE_ARTIFACT_SCOPE_MISMATCH',f'{oid} artifact scope mismatch',idx))
                if env.get('content_digest')!=pref.get('content_digest') or pref.get('content_digest')!=ar.get('content_digest'):
                    out.append(Err('CTX_OVL_E_CANDIDATE_DIGEST_MISMATCH',f'{oid} digest mismatch',idx))
                if env.get('content_kind')!=pref.get('content_kind') or pref.get('content_kind')!=ar.get('content_kind'):
                    out.append(Err('CTX_OVL_E_CANDIDATE_ARTIFACT_KIND_MISMATCH',f'{oid} content kind mismatch',idx))
                if (env.get('size_bound') or {}).get('actual_bytes')!=ar.get('actual_bytes') or (env.get('size_bound') or {}).get('actual_bytes',0)>(env.get('size_bound') or {}).get('max_bytes',-1):
                    out.append(Err('CTX_OVL_E_CANDIDATE_ENVELOPE_SIZE_EXCEEDED',f'{oid} size mismatch',idx))
            expected_visibility={'participant':'participant_private','shared_scene':'shared_scene_visible','relationship':'relationship_scoped','quarantine':'quarantined'}.get(r.get('partition_kind'))
            if r.get('visibility_scope')!=expected_visibility: out.append(Err('CTX_OVL_E_PARTITION_VISIBILITY_MISMATCH',f'{oid} partition/visibility mismatch',idx))
            expected_creator='ctx_ovl_rebuild_process' if r.get('admission_origin')=='rebuild_pipeline' else 'relayctx_pipeline'
            if r.get('created_by_actor')!=expected_creator:
                out.append(Err('CTX_OVL_E_ADMISSION_CREATOR_MISMATCH',f'{oid} admission origin/creator mismatch',idx))
            if r.get('lifecycle_state')=='active' and (a.get('watermark_freshness')!='current' or a.get('validated_access_state')!='admitted'):
                out.append(Err('CTX_OVL_E_STALE_AUTHORIZATION',f'{oid} active with stale authorization',idx))
            successor=r.get('superseded_by_overlay_record_id_or_null')
            if r.get('lifecycle_state')=='superseded' and not successor: out.append(Err('CTX_OVL_E_LIFECYCLE_SUPERSESSION_MISMATCH',f'{oid} superseded without successor',idx))
            if r.get('lifecycle_state')!='superseded' and successor: out.append(Err('CTX_OVL_E_LIFECYCLE_SUPERSESSION_MISMATCH',f'{oid} successor on non-superseded record',idx))
            if r.get('lifecycle_state')=='superseded' and successor:
                if successor==oid: out.append(Err('CTX_OVL_E_SELF_SUPERSESSION_REFERENCE',f'{oid} supersedes itself',idx))
                elif successor not in ovs: out.append(Err('CTX_OVL_E_DANGLING_SUPERSESSION_TARGET',f'{oid} successor {successor} does not resolve',idx))
                elif ovs[successor][1].get('session_id')!=r.get('session_id'): out.append(Err('CTX_OVL_E_CROSS_SESSION_SUPERSESSION_TARGET',f'{oid} successor is in another session',idx))
            pr=r.get('participant_ref') or {}
            if pr.get('identity_status')=='known' and pr.get('participant_id_or_null') is None:
                out.append(Err('CTX_OVL_E_PARTICIPANT_IDENTITY_MISMATCH',f'{oid} known participant is null',idx))
            if pr.get('identity_status') in ('unknown','conflicting'):
                if not (r.get('partition_kind')=='quarantine' and r.get('visibility_scope')=='quarantined' and r.get('non_shadowing') is True and pr.get('participant_id_or_null') is None):
                    out.append(Err('CTX_OVL_E_PARTICIPANT_IDENTITY_MISMATCH',f'{oid} unresolved identity not quarantined',idx))
                shadow=r.get('quarantine_shadow_target_overlay_record_id_or_null')
                if shadow:
                    if shadow not in ovs: out.append(Err('CTX_OVL_E_DANGLING_QUARANTINE_SHADOW_TARGET',f'{oid} shadow target does not resolve',idx))
                    elif ovs[shadow][1].get('session_id')!=r.get('session_id'): out.append(Err('CTX_OVL_E_CROSS_SESSION_QUARANTINE_SHADOW_TARGET',f'{oid} shadow target is in another session',idx))
                    else: out.append(Err('CTX_OVL_E_UNKNOWN_PARTICIPANT_SHADOW',f'{oid} shadows {shadow}',idx))
        edges={oid:r.get('superseded_by_overlay_record_id_or_null') for oid,(_,r) in ovs.items() if r.get('lifecycle_state')=='superseded' and r.get('superseded_by_overlay_record_id_or_null') in ovs and r.get('superseded_by_overlay_record_id_or_null')!=oid}
        visiting=set(); visited=set()
        def visit(node):
            if node in visiting: return True
            if node in visited or node not in edges: return False
            visiting.add(node)
            if visit(edges[node]): return True
            visiting.remove(node); visited.add(node); return False
        if any(visit(node) for node in list(edges)): out.append(Err('CTX_OVL_E_SUPERSESSION_CYCLE','supersession graph contains a cycle'))

        def ttl_check(op:dict, ids:list[str], dangling_id:str, session_id:str, origin:str|None=None, scope:tuple[str,str,str]|None=None, require_active_authorized:bool=False):
            eval_at=dt(op['evaluated_at'])
            for oid in ids:
                item=ovs.get(oid)
                if item is None:
                    if oid not in raw_ov_ids:
                        out.append(Err(dangling_id,f'output {oid} does not resolve'))
                    continue
                _,r=item
                if r.get('session_id')!=session_id:
                    out.append(Err(dangling_id.replace('DANGLING','').replace('__','_').replace('OUTPUT','OUTPUT_SESSION_MISMATCH').strip('_'),f'{oid} session mismatch'))
                    continue
                if require_active_authorized:
                    if r.get('lifecycle_state')!='active': out.append(Err('CTX_OVL_E_OPERATION_NON_ACTIVE_OVERLAY',f'{oid} is not active'))
                    auth=r.get('last_validated_authorization') or {}
                    if auth.get('watermark_freshness')!='current' or auth.get('validated_access_state')!='admitted': out.append(Err('CTX_OVL_E_OPERATION_UNAUTHORIZED_OVERLAY',f'{oid} is not currently authorized'))
                if origin and r.get('admission_origin')!=origin:
                    prefix='CATCH_UP' if origin=='catch_up_pipeline' else 'REBUILD'
                    out.append(Err(f'CTX_OVL_E_{prefix}_OUTPUT_ORIGIN_MISMATCH',f'{oid} origin mismatch'))
                if scope:
                    b=r.get('contract1_binding') or {}
                    if (b.get('change_partition_id'),b.get('partition_epoch_id'),b.get('authority_snapshot_digest'))!=scope:
                        prefix='CATCH_UP' if origin=='catch_up_pipeline' else 'REBUILD'
                        out.append(Err(f'CTX_OVL_E_{prefix}_OUTPUT_SCOPE_MISMATCH',f'{oid} scope mismatch'))
                if dt(r['ttl_expires_at'])<=eval_at:
                    out.append(Err('CTX_OVL_E_TTL_EXPIRED_AT_EVALUATION',f'{oid} expired at operation time'))

        for _,s in selections:
            selected=s.get('selected_overlay_record_ids',[])
            ttl_check(s,selected,'CTX_OVL_E_DANGLING_SELECTION_OUTPUT',s.get('session_id'),require_active_authorized=True)
            expected_artifacts=[]; resolution_complete=True
            for oid in selected:
                if oid in ovs:
                    aid=(ovs[oid][1].get('candidate_envelope') or {}).get('producer_artifact_ref',{}).get('artifact_id')
                    if aid in arts: expected_artifacts.append(aid)
                    else: resolution_complete=False
                    if aid in arts and aid not in s.get('resolved_candidate_artifact_ids',[]):
                        out.append(Err('CTX_OVL_E_UNRESOLVED_SELECTION_ARTIFACT',f'{oid} artifact not resolved by selection'))
                else:
                    resolution_complete=False
            if resolution_complete and (set(s.get('resolved_candidate_artifact_ids',[]))!=set(expected_artifacts) or s.get('rendered_hint_count')!=len(selected)):
                out.append(Err('CTX_OVL_E_SELECTION_RESOLUTION_MISMATCH','selection artifact set or rendered hint count mismatch'))
        def output_candidate_bytes(ids):
            return sum((ovs[oid][1].get('candidate_envelope') or {}).get('size_bound',{}).get('actual_bytes',0) for oid in ids if oid in ovs)
        for _,c in catchups:
            cov=c.get('coverage_checkpoint_ref') or {}; aw=c.get('authorization_watermark_ref') or {}
            applied=c.get('outcome')=='bounded_catch_up_applied'; produced=c.get('produced_overlay_record_ids',[]); bound=c.get('eligible_selection_bound') or {}
            if len(produced)>bound.get('max_events',-1): out.append(Err('CTX_OVL_E_CATCH_UP_OUTPUT_COUNT_EXCEEDS_BOUND','catch-up output count exceeds max_events'))
            if output_candidate_bytes(produced)>bound.get('max_total_candidate_bytes',-1): out.append(Err('CTX_OVL_E_CATCH_UP_OUTPUT_BYTES_EXCEED_BOUND','catch-up candidate bytes exceed budget'))
            if applied:
                if cov.get('derived_coverage_status') not in ('open_contiguous','sealed_complete'): out.append(Err('CTX_OVL_E_CATCH_UP_COVERAGE_INCOMPLETE','catch-up applied without complete coverage'))
                if aw.get('watermark_freshness')!='current': out.append(Err('CTX_OVL_E_STALE_AUTHORIZATION','catch-up applied with stale watermark'))
                if not produced: out.append(Err('CTX_OVL_E_CATCH_UP_OUTCOME_OUTPUT_MISMATCH','applied catch-up produced no overlay'))
            elif produced: out.append(Err('CTX_OVL_E_CATCH_UP_OUTCOME_OUTPUT_MISMATCH','fail-closed/no-op catch-up produced overlays'))
            if (cov.get('change_partition_id'),cov.get('partition_epoch_id'))!=(aw.get('change_partition_id'),aw.get('partition_epoch_id')):
                out.append(Err('CTX_OVL_E_COVERAGE_AUTHORIZATION_PARTITION_MISMATCH','catch-up coverage/auth mismatch'))
            scope=(cov.get('change_partition_id'),cov.get('partition_epoch_id'),aw.get('authority_snapshot_digest'))
            ttl_check(c,produced,'CTX_OVL_E_DANGLING_CATCH_UP_OUTPUT',c.get('session_id'),'catch_up_pipeline',scope,True)
        for _,r in rebuilds:
            cov=r.get('coverage_checkpoint_ref') or {}; ar=r.get('authorization_ref') or {}; produced=r.get('produced_overlay_record_ids',[]); bound=r.get('rebuild_bound') or {}
            if len(produced)>bound.get('max_overlay_records',-1): out.append(Err('CTX_OVL_E_REBUILD_OUTPUT_COUNT_EXCEEDS_BOUND','rebuild output count exceeds budget'))
            if output_candidate_bytes(produced)>bound.get('max_total_candidate_bytes',-1): out.append(Err('CTX_OVL_E_REBUILD_OUTPUT_BYTES_EXCEED_BOUND','rebuild candidate bytes exceed budget'))
            if (cov.get('change_partition_id'),cov.get('partition_epoch_id'))!=(ar.get('change_partition_id'),ar.get('partition_epoch_id')):
                out.append(Err('CTX_OVL_E_COVERAGE_AUTHORIZATION_PARTITION_MISMATCH','rebuild coverage/auth mismatch'))
            if ar.get('watermark_freshness')!='current' or ar.get('validated_access_state')!='admitted':
                out.append(Err('CTX_OVL_E_REBUILD_AUTHORIZATION_NOT_CURRENT','rebuild authorization is not current+admitted'))
            scope=(cov.get('change_partition_id'),cov.get('partition_epoch_id'),ar.get('authority_snapshot_digest'))
            ttl_check(r,produced,'CTX_OVL_E_DANGLING_REBUILD_OUTPUT',r.get('session_id'),'rebuild_pipeline',scope,True)
        for _,p in projections:
            ttl_check(p,p.get('included_overlay_record_ids',[]),'CTX_OVL_E_DANGLING_INCLUDED_OVERLAY',p.get('session_id'),require_active_authorized=True)
            d=eps.get((p.get('partition_epoch_ref') or {}).get('partition_epoch_descriptor_id'))
            if d and d[1].get('scene_epoch_id_or_null')!=p.get('scene_epoch_id'): out.append(Err('CTX_OVL_E_STALE_SCENE_EPOCH','projection scene epoch mismatch'))
            pa=p.get('authorization_ref') or {}; visible=set(p.get('visible_participant_ids') or []); allowed=set(pa.get('authorized_participant_ids') or [])
            if pa.get('watermark_freshness')!='current' or pa.get('validated_access_state')!='admitted': out.append(Err('CTX_OVL_E_PROJECTION_AUTHORIZATION_NOT_CURRENT','projection authorization is not current+admitted'))
            if not visible.issubset(allowed): out.append(Err('CTX_OVL_E_PARTICIPANT_SCOPE_MISMATCH','projection participant scope mismatch'))
            for oid in p.get('included_overlay_record_ids',[]):
                if oid not in ovs: continue
                r=ovs[oid][1]
                if r.get('partition_kind')!='shared_scene' or r.get('visibility_scope')!='shared_scene_visible': out.append(Err('CTX_OVL_E_PRIVATE_TO_GROUP_DISCLOSURE',f'{oid} is not shared-scene visible'))
                if r.get('partition_id')!=p.get('partition_id') or r.get('partition_epoch_ref')!=p.get('partition_epoch_ref'):
                    out.append(Err('CTX_OVL_E_PROJECTION_PARTITION_EPOCH_MISMATCH',f'{oid} is from another shared-scene partition/epoch'))
                if r.get('lifecycle_state')!='active': out.append(Err('CTX_OVL_E_NON_ACTIVE_RECORD_IN_PROJECTION',f'{oid} not active'))
                b=r.get('contract1_binding') or {}
                if (b.get('change_partition_id'),b.get('partition_epoch_id'),b.get('authority_snapshot_digest'))!=(pa.get('change_partition_id'),pa.get('partition_epoch_id'),pa.get('authority_snapshot_digest')):
                    out.append(Err('CTX_OVL_E_PROJECTION_OVERLAY_AUTHORIZATION_MISMATCH',f'{oid} projection authorization mismatch'))

        reason_state={'restricted':'restricted','redacted':'redacted','purged':'purged','corrected_superseded':'corrected_superseded'}
        for _,ev in invalidations:
            ar=ev.get('authorization_ref') or {}; reason=ev.get('invalidation_reason'); scope=ev.get('invalidation_scope_binding') or {}
            if (scope.get('change_partition_id'),scope.get('partition_epoch_id'),scope.get('authority_snapshot_digest'))!=(ar.get('change_partition_id'),ar.get('partition_epoch_id'),ar.get('authority_snapshot_digest')): out.append(Err('CTX_OVL_E_INVALIDATION_SCOPE_AUTHORIZATION_MISMATCH','invalidation scope/auth mismatch'))
            if reason in reason_state and ar.get('validated_access_state')!=reason_state[reason]: out.append(Err('CTX_OVL_E_INVALIDATION_REASON_STATE_MISMATCH','invalidation reason/access state mismatch'))
            if reason=='watermark_advanced':
                prev=ev.get('prior_highest_observed_partition_sequence_or_null')
                if prev is None or ar.get('highest_observed_partition_sequence',-1)<=prev: out.append(Err('CTX_OVL_E_WATERMARK_NOT_ADVANCED','watermark did not advance'))
            for oid in ev.get('affected_overlay_record_ids',[]):
                if oid not in ovs:
                    out.append(Err('CTX_OVL_E_DANGLING_INVALIDATION_TARGET',f'{oid} invalidation target does not resolve')); continue
                target=ovs[oid][1]
                if target.get('session_id')!=ev.get('session_id'): out.append(Err('CTX_OVL_E_INVALIDATION_SESSION_MISMATCH',f'{oid} invalidated from another session'))
                if target.get('contract1_binding')!=scope: out.append(Err('CTX_OVL_E_INVALIDATION_TARGET_SCOPE_MISMATCH',f'{oid} invalidation scope mismatch'))
                if target.get('lifecycle_state')!='removed': out.append(Err('CTX_OVL_E_INVALIDATION_NOT_APPLIED',f'{oid} not removed'))
        for _,w in writes:
            actor=w.get('attempted_actor_component'); allowed=actor in ('relayctx_pipeline','ctx_ovl_rebuild_process')
            if not allowed and (w.get('authorized_actor') or w.get('authorized')): out.append(Err('CTX_OVL_E_WRITE_ATTEMPT_ACTOR_UNAUTHORIZED','unauthorized actor claimed authorization'))
            elif allowed and w.get('authorized_actor')!=w.get('authorized'): out.append(Err('CTX_OVL_E_WRITE_AUTHORIZATION_MISMATCH','authorization booleans disagree'))
        return out

def load_cases(directory:Path)->list[dict[str,Any]]:
    cases=[]
    for path in sorted(directory.glob('*.json')):
        batch=json.loads(path.read_text()).get('cases')
        if not isinstance(batch,list) or not batch: raise ValueError(f'{path} must contain non-empty cases array')
        cases.extend(batch)
    names=[c.get('name') for c in cases]
    if not cases or any(not isinstance(n,str) or not n for n in names) or len(set(names))!=len(names): raise ValueError(f'{directory} case names must be unique non-empty strings')
    return cases

def run(verbose=False)->int:
    v=Validator(); failures=[]
    valid=load_cases(VALID_DIR); invalid=load_cases(INVALID_DIR)
    for case in valid:
        errs=v.validate_case(case)
        if errs: failures.append(f"valid case {case['name']} produced {[e.error_id for e in errs]}")
        elif verbose: print('OK ',case['name'])
    for case in invalid:
        expected=sorted(set(case.get('expected_error_ids') or [])); produced=sorted(set(e.error_id for e in v.validate_case(case)))
        if not expected: failures.append(f"invalid case {case['name']} missing expected_error_ids")
        elif produced!=expected: failures.append(f"invalid case {case['name']} expected={expected} produced={produced}")
        elif verbose: print('FAIL as expected ',case['name'],expected)
    if failures:
        print('CTX-OVL strict matrix validation FAILED',file=sys.stderr)
        for f in failures: print('-',f,file=sys.stderr)
        return 1
    print(f'CTX-OVL strict matrix validation PASS: {len(valid)} valid, {len(invalid)} invalid cases; exact error-id sets matched.')
    return 0

def self_test()->int:
    v=Validator(); cases=load_cases(INVALID_DIR)
    names=['candidate_digest_mismatch','ttl_expired_at_selection','candidate_basis_kind_mismatch','dangling_rebuild_output','projection_stale_authorization','dangling_invalidation_target','duplicate_artifact_id','catch_up_output_count_exceeds_bound','partition_visibility_mismatch','catch_up_budget_policy_mismatch']
    failures=[]
    def bs(case,sid): return [r for r in case['records'] if r.get('schema')==sid]
    for name in names:
        c=next(x for x in cases if x['name']==name); original=set(c['expected_error_ids']); m=json.loads(json.dumps(c))
        if name=='candidate_digest_mismatch':
            a=bs(m,'relaylm.ctx_ovl_candidate_artifact.v1')[0]; o=bs(m,'relaylm.ctx_ovl_overlay_record.v1')[0]; o['candidate_envelope']['content_digest']=a['content_digest']; o['contract1_binding']['source_event_id']='other'
        elif name=='ttl_expired_at_selection':
            o=bs(m,'relaylm.ctx_ovl_overlay_record.v1')[0]; o['ttl_expires_at']='2026-07-20T03:00:00Z'; o['contract1_binding']['source_event_id']='other'
        elif name=='candidate_basis_kind_mismatch':
            o=bs(m,'relaylm.ctx_ovl_overlay_record.v1')[0]; o['candidate_basis']='validated_sidecar'; o['contract1_binding']['source_event_id']='other'
        elif name=='dangling_rebuild_output':
            x=bs(m,'relaylm.ctx_ovl_rebuild_event.v1')[0]; x['produced_overlay_record_ids']=[]; x['durable_state_claimed']=True
        elif name=='projection_stale_authorization':
            x=bs(m,'relaylm.ctx_ovl_shared_scene_projection.v1')[0]; x['authorization_ref']['watermark_freshness']='current'; x['partition_id']='other'
        elif name=='dangling_invalidation_target':
            x=bs(m,'relaylm.ctx_ovl_overlay_invalidation_event.v1')[0]; o=bs(m,'relaylm.ctx_ovl_overlay_record.v1')[0]; x['affected_overlay_record_ids']=[o['overlay_record_id']]; x['authorization_ref']['validated_access_state']='restricted'
        elif name=='duplicate_artifact_id':
            a=bs(m,'relaylm.ctx_ovl_candidate_artifact.v1'); m['records'].remove(a[-1]); bs(m,'relaylm.ctx_ovl_overlay_record.v1')[0]['contract1_binding']['source_event_id']='other'
        elif name=='catch_up_output_count_exceeds_bound':
            x=bs(m,'relaylm.ctx_ovl_catch_up_attempt.v1')[0]; x['eligible_selection_bound']['max_events']=len(x['produced_overlay_record_ids']); x['coverage_checkpoint_ref']['derived_coverage_status']='open_incomplete'
        elif name=='partition_visibility_mismatch':
            o=bs(m,'relaylm.ctx_ovl_overlay_record.v1')[0]; o['visibility_scope']='participant_private'; o['contract1_binding']['source_event_id']='other'
        else:
            x=bs(m,'relaylm.ctx_ovl_catch_up_attempt.v1')[0]; x['budget_policy_ref']=dict(policy_id='ctx_ovl_budget_policy_v1',policy_version=1,authority_domain='relayctx_contract'); x['coverage_checkpoint_ref']['derived_coverage_status']='open_incomplete'
        produced=set(x.error_id for x in v.validate_case(m))
        if produced==original or not produced: failures.append(f'{name} did not discriminate: {produced}')
    if failures:
        for f in failures: print(f,file=sys.stderr)
        return 1
    print(f'CTX-OVL validator self-test PASS: {len(names)} defect substitutions discriminated.')
    return 0

def main():
    p=argparse.ArgumentParser(); p.add_argument('--verbose',action='store_true'); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    return self_test() if a.self_test else run(a.verbose)
if __name__=='__main__': raise SystemExit(main())
