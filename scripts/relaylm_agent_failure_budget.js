#!/usr/bin/env node
'use strict';

const crypto = require('crypto');

const MARKER_START = '<!-- relaylm-failure-budget-state\n';
const MARKER_END = '\n-->';
const LABELS = [
  'relaylm:failure-1',
  'relaylm:failure-2',
  'relaylm:p6-stop',
];
const LABEL_COLORS = {
  'relaylm:failure-1': 'FBCA04',
  'relaylm:failure-2': 'D93F0B',
  'relaylm:p6-stop': 'B60205',
};
const SUCCESS = 'success';
const NON_COUNTING = new Set(['skipped', 'neutral']);

function emptyState() {
  return {version: 1, workflows: {}, p6_stop: false};
}

function parseState(body) {
  const start = body.indexOf(MARKER_START);
  if (start < 0) return null;
  const contentStart = start + MARKER_START.length;
  const end = body.indexOf(MARKER_END, contentStart);
  if (end < 0) throw new Error('failure-budget marker is unterminated');
  const value = JSON.parse(body.slice(contentStart, end));
  if (!value || value.version !== 1 || typeof value.workflows !== 'object') {
    throw new Error('failure-budget state has an invalid schema');
  }
  return value;
}

function canonicalState(state) {
  const recent = Object.entries(state.workflows || {})
    .filter(([, value]) => value && Number(value.last_run_id || 0) > 0)
    .sort((left, right) => Number(right[1].last_run_id) - Number(left[1].last_run_id))
    .slice(0, 64)
    .sort((left, right) => left[0].localeCompare(right[0]));
  return {
    version: 1,
    workflows: Object.fromEntries(recent),
    p6_stop: Boolean(state.p6_stop),
  };
}

function boundedCategory(conclusion) {
  const allowed = new Set([
    'failure',
    'cancelled',
    'timed_out',
    'action_required',
    'startup_failure',
    'stale',
  ]);
  return allowed.has(conclusion) ? conclusion : 'other_non_success';
}

function signatureDigest(fields) {
  const stable = {
    workflow_id: Number(fields.workflow_id || 0),
    failed_job_name: String(fields.failed_job_name || ''),
    first_failed_step_name: String(fields.first_failed_step_name || ''),
    bounded_conclusion_category: String(fields.bounded_conclusion_category || ''),
  };
  return crypto.createHash('sha256').update(JSON.stringify(stable)).digest('hex');
}

function successState(previous, run) {
  return {
    workflow_name: String(run.name || ''),
    signature_digest: null,
    signature_fields: null,
    consecutive_count: 0,
    last_run_id: Number(run.id),
  };
}

function nonCountingState(previous, run) {
  if (!previous) return successState(previous, run);
  return {
    ...previous,
    workflow_name: String(run.name || ''),
    last_run_id: Number(run.id),
  };
}

function failureState(previous, run, fields) {
  const digest = signatureDigest(fields);
  const count = previous && previous.signature_digest === digest
    ? Number(previous.consecutive_count || 0) + 1
    : 1;
  return {
    workflow_name: String(run.name || ''),
    signature_digest: digest,
    signature_fields: fields,
    consecutive_count: count,
    last_run_id: Number(run.id),
  };
}

function desiredLabel(state) {
  if (state.p6_stop) return 'relaylm:p6-stop';
  const highest = Object.values(state.workflows || {})
    .reduce((value, item) => Math.max(value, Number(item.consecutive_count || 0)), 0);
  if (highest >= 2) return 'relaylm:failure-2';
  if (highest >= 1) return 'relaylm:failure-1';
  return null;
}

function summary(state, resetReason = '') {
  const highest = Object.values(state.workflows || {})
    .reduce((value, item) => Math.max(value, Number(item.consecutive_count || 0)), 0);
  const status = state.p6_stop
    ? 'P6-STOP — branch writes and merge are prohibited.'
    : highest > 0
      ? `Consecutive failure level: ${highest}/3.`
      : 'No active consecutive failure.';
  const reset = resetReason
    ? `\n\nLast reviewed reset: ${resetReason.slice(0, 500)}`
    : '';
  return `${MARKER_START}${JSON.stringify(canonicalState(state))}${MARKER_END}\n\n**RelayLM failure budget**\n\n${status}${reset}`;
}

function stateForReviewedReset(markers, currentLabels) {
  if (markers.length > 1) {
    throw new Error('reset requires at most one failure-budget state comment');
  }

  if (markers.length === 1) {
    const state = canonicalState(parseState(markers[0].body));
    if (!state.p6_stop && !currentLabels.has('relaylm:p6-stop')) {
      throw new Error('reset target has no active P6 stop');
    }
    return state;
  }

  if (!currentLabels.has('relaylm:p6-stop')) {
    throw new Error('reset requires a failure-budget state comment or relaylm:p6-stop label');
  }

  return {version: 1, workflows: {}, p6_stop: true};
}

async function commentsFor(github, owner, repo, prNumber) {
  return github.paginate(github.rest.issues.listComments, {
    owner,
    repo,
    issue_number: prNumber,
    per_page: 100,
  });
}

async function ensureLabel(github, owner, repo, name) {
  try {
    await github.rest.issues.getLabel({owner, repo, name});
  } catch (error) {
    if (error.status !== 404) throw error;
    try {
      await github.rest.issues.createLabel({
        owner,
        repo,
        name,
        color: LABEL_COLORS[name],
        description: 'RelayLM machine-owned execution failure state',
      });
    } catch (createError) {
      if (createError.status !== 422) throw createError;
    }
  }
}

async function replaceExecutionLabel(github, owner, repo, prNumber, current, desired) {
  for (const name of LABELS) {
    if (!current.has(name)) continue;
    try {
      await github.rest.issues.removeLabel({
        owner,
        repo,
        issue_number: prNumber,
        name,
      });
    } catch (error) {
      if (error.status !== 404) throw error;
    }
  }
  if (desired) {
    await ensureLabel(github, owner, repo, desired);
    await github.rest.issues.addLabels({
      owner,
      repo,
      issue_number: prNumber,
      labels: [desired],
    });
  }
}

async function writeState(github, owner, repo, prNumber, markers, state, resetReason = '') {
  const body = summary(state, resetReason);
  if (markers.length) {
    await github.rest.issues.updateComment({
      owner,
      repo,
      comment_id: markers[0].id,
      body,
    });
  } else {
    await github.rest.issues.createComment({
      owner,
      repo,
      issue_number: prNumber,
      body,
    });
  }
}

async function loadPr(github, owner, repo, prNumber) {
  const response = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });
  return response.data;
}

async function makeDraft(github, pr) {
  if (pr.draft) return;
  await github.graphql(
    `mutation($id: ID!) {
      convertPullRequestToDraft(input: {pullRequestId: $id}) {
        pullRequest { id }
      }
    }`,
    {id: pr.node_id},
  );
}

async function resetStop({github, owner, repo, prNumber, reason}) {
  const pr = await loadPr(github, owner, repo, prNumber);
  if (pr.state !== 'open') throw new Error('reset target PR is not open');
  const comments = await commentsFor(github, owner, repo, prNumber);
  const markers = comments.filter(item => item.body && item.body.includes(MARKER_START));
  const currentLabels = new Set(pr.labels.map(item => item.name));
  const state = stateForReviewedReset(markers, currentLabels);
  state.p6_stop = false;
  state.workflows = {};

  // Establish the canonical state comment before removing the fail-closed label.
  // A partial reset therefore remains stopped and can be retried safely.
  await writeState(github, owner, repo, prNumber, markers, state, reason);
  await replaceExecutionLabel(github, owner, repo, prNumber, currentLabels, null);
}

async function failedFields(github, owner, repo, run) {
  const jobs = await github.paginate(
    github.rest.actions.listJobsForWorkflowRun,
    {owner, repo, run_id: run.id, per_page: 100, filter: 'latest'},
  );
  const failedJobs = jobs
    .filter(job => !['success', 'skipped', 'neutral'].includes(job.conclusion))
    .sort((left, right) => left.name.localeCompare(right.name));
  const job = failedJobs[0];
  const step = job && Array.isArray(job.steps)
    ? job.steps.find(item => !['success', 'skipped', 'neutral'].includes(item.conclusion))
    : null;
  return {
    workflow_name: String(run.name || ''),
    workflow_id: Number(run.workflow_id || 0),
    failed_job_name: String(job ? job.name : '<workflow>'),
    first_failed_step_name: String(step ? step.name : '<unknown-step>'),
    bounded_conclusion_category: boundedCategory(
      String((step && step.conclusion) || (job && job.conclusion) || run.conclusion || ''),
    ),
  };
}

async function processRun({github, owner, repo, prNumber, run}) {
  const pr = await loadPr(github, owner, repo, prNumber);
  if (pr.state !== 'open') return;

  const currentLabels = new Set(pr.labels.map(item => item.name));
  const comments = await commentsFor(github, owner, repo, prNumber);
  const markers = comments.filter(item => item.body && item.body.includes(MARKER_START));
  let state = emptyState();

  if (markers.length === 1) {
    state = canonicalState(parseState(markers[0].body));
  } else if (markers.length > 1 || LABELS.some(name => currentLabels.has(name))) {
    state.p6_stop = true;
  }

  const workflowKey = String(run.workflow_id);
  const previous = state.workflows[workflowKey];
  if (previous && Number(run.id) <= Number(previous.last_run_id || 0)) return;

  const conclusion = String(run.conclusion || '');
  if (!state.p6_stop && conclusion === SUCCESS) {
    state.workflows[workflowKey] = successState(previous, run);
  } else if (!state.p6_stop && NON_COUNTING.has(conclusion)) {
    state.workflows[workflowKey] = nonCountingState(previous, run);
  } else if (!state.p6_stop) {
    const fields = await failedFields(github, owner, repo, run);
    state.workflows[workflowKey] = failureState(previous, run, fields);
    if (state.workflows[workflowKey].consecutive_count >= 3) state.p6_stop = true;
  }

  state = canonicalState(state);
  const desired = desiredLabel(state);
  await replaceExecutionLabel(github, owner, repo, prNumber, currentLabels, desired);
  if (state.p6_stop) await makeDraft(github, pr);
  if (markers.length || desired || state.p6_stop) {
    await writeState(github, owner, repo, prNumber, markers, state);
  }
}

async function associatedPullRequests(github, owner, repo, run) {
  const direct = Array.isArray(run.pull_requests) ? run.pull_requests : [];
  if (direct.length || !run.head_branch) return direct;
  return github.paginate(github.rest.pulls.list, {
    owner,
    repo,
    state: 'open',
    head: `${owner}:${run.head_branch}`,
    per_page: 100,
  });
}

async function run({github, context}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (context.eventName === 'workflow_dispatch') {
    const prNumber = Number(context.payload.inputs.pr_number);
    const reason = String(context.payload.inputs.reset_reason || '').trim();
    if (!Number.isInteger(prNumber) || prNumber <= 0 || !reason) {
      throw new Error('valid pr_number and reset_reason are required');
    }
    await resetStop({github, owner, repo, prNumber, reason});
    return;
  }

  const workflowRun = context.payload.workflow_run;
  for (const item of await associatedPullRequests(github, owner, repo, workflowRun)) {
    await processRun({
      github,
      owner,
      repo,
      prNumber: Number(item.number),
      run: workflowRun,
    });
  }
}

function selfTest() {
  const failures = [];
  const expect = (name, condition) => {
    process.stdout.write(`${condition ? 'PASS' : 'FAIL'}: ${name}\n`);
    if (!condition) failures.push(name);
  };
  const expectThrows = (name, action, pattern) => {
    try {
      action();
      expect(name, false);
    } catch (error) {
      expect(name, pattern.test(String(error && error.message)));
    }
  };

  const run1 = {id: 100, name: 'Example'};
  const fields = {
    workflow_name: 'Example',
    workflow_id: 42,
    failed_job_name: 'test',
    first_failed_step_name: 'run tests',
    bounded_conclusion_category: 'failure',
  };
  const first = failureState(null, run1, fields);
  const renamed = failureState(first, {id: 101, name: 'Renamed'}, {...fields, workflow_name: 'Renamed'});
  expect('same workflow ID survives display-name rename', renamed.consecutive_count === 2);

  const skipped = nonCountingState(renamed, {id: 102, name: 'Renamed'});
  expect('skipped run preserves count', skipped.consecutive_count === 2);
  expect('skipped run advances workflow-local ordering', skipped.last_run_id === 102);

  const success = successState(skipped, {id: 103, name: 'Renamed'});
  expect('success resets count', success.consecutive_count === 0);

  const state = canonicalState({
    version: 1,
    workflows: {
      '42': renamed,
      '43': {...first, last_run_id: 99},
    },
    p6_stop: false,
  });
  expect('workflow-local state remains independent', Object.keys(state.workflows).length === 2);
  expect('highest state produces failure-2', desiredLabel(state) === 'relaylm:failure-2');

  const stop = {...state, p6_stop: true};
  expect('P6 stop label is sticky state', desiredLabel(stop) === 'relaylm:p6-stop');

  const serialized = summary(stop);
  expect('state marker round-trips', parseState(serialized).p6_stop === true);
  expect('neutral conclusion is non-counting', NON_COUNTING.has('neutral'));

  const marker = [{body: serialized}];
  expect(
    'reviewed reset accepts canonical stopped marker',
    stateForReviewedReset(marker, new Set()).p6_stop === true,
  );
  expect(
    'reviewed reset reconstructs missing marker from P6 label',
    stateForReviewedReset([], new Set(['relaylm:p6-stop'])).p6_stop === true,
  );
  expect(
    'reviewed reset accepts label when marker mirror is stale',
    stateForReviewedReset([{body: summary(emptyState())}], new Set(['relaylm:p6-stop'])).p6_stop === false,
  );
  expectThrows(
    'reviewed reset rejects duplicate marker comments',
    () => stateForReviewedReset([marker[0], marker[0]], new Set(['relaylm:p6-stop'])),
    /at most one/,
  );
  expectThrows(
    'reviewed reset rejects absent stop evidence',
    () => stateForReviewedReset([], new Set()),
    /state comment or relaylm:p6-stop label/,
  );
  expectThrows(
    'reviewed reset rejects inactive marker without P6 label',
    () => stateForReviewedReset([{body: summary(emptyState())}], new Set()),
    /no active P6 stop/,
  );

  if (failures.length) {
    process.stderr.write(`SELF-TEST FAILED: ${failures.length} assertion(s)\n`);
    return 1;
  }
  process.stdout.write('SELF-TEST PASS\n');
  return 0;
}

module.exports = {
  boundedCategory,
  canonicalState,
  desiredLabel,
  failureState,
  nonCountingState,
  parseState,
  run,
  signatureDigest,
  stateForReviewedReset,
  successState,
};

if (require.main === module) {
  process.exit(process.argv.includes('--self-test') ? selfTest() : 2);
}
