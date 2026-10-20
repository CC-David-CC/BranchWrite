"""Immutable host-selected thinking ladder; mutable progress stays in RuntimeLog.

This module supplies definitions and decisions, not a second agent driver.
The workflow integration must derive its rung from committed host verdicts and
use COW forks for planning tips. Definitions alone do not prove that integration.
"""
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class ThinkingRung:
    tokens: int
    seconds: int
    @property
    def grammar_state(self):
        return 'BW_TOOLS' if self.tokens==4096 else 'BW_TOOLS_THINK_'+str(self.tokens)

# These are generous per-attempt planning allowances,not speed predictions.
# They do not reserve CPU/GPU time or require the model to fill its allowance.
_LITE=tuple(ThinkingRung(tokens,seconds) for tokens,seconds in
    [(256,30),(512,45),(1024,60),(2048,90),(4096,180),(8192,360),(16384,720),(32768,1440)])
_STANDARD=_LITE[4:]
_VERDICTS=frozenset(('verified_pass','verified_failure','incomplete','tool_progress','infrastructure_failure','unresolved_effect'))

def ladder(mode='standard'):
    if mode not in ('standard','lite'):raise ValueError('unknown host thinking mode')
    return _STANDARD if mode=='standard' else _LITE

def next_attempt(mode,index,verdict):
    rungs=ladder(mode)
    if type(index) is not int or not 0<=index<len(rungs):raise ValueError('invalid thinking rung')
    if verdict not in _VERDICTS:raise ValueError('host task verdict required')
    if verdict=='verified_pass':return None
    if verdict=='verified_failure':
        return index+1 if index+1<len(rungs) else None
    # Incomplete thinking/tool progress does not mean the task failed.
    # Unknown effects retain their original IDs and must be reconciled first.
    return index

def task_verdict(outcome,verification):
    """Classify a host-owned completed tool/check pair,not a model claim.

    Ordinary intermediate checks use status=fail until the task is done. They
    are progress,not evidence that another planning attempt should be spent.
    Tool timeouts with proven cleanup likewise remain observations to diagnose.
    """
    if (type(outcome) is not dict or type(verification) is not dict
            or verification.get('status') not in ('pass','fail')):
        raise ValueError('recognized host verification and tool outcome required')
    disposition=outcome.get('disposition')
    if disposition in ('effect_indeterminate','unresolved','unknown'):
        return 'unresolved_effect'
    if disposition in ('spawn_error','boundary_error','harness_error','publication_error'):
        return 'infrastructure_failure'
    complete=(outcome.get('tool')=='finish' and disposition=='completion_requested'
              and outcome.get('requested_finish') is True and outcome.get('exit_code') is None)
    if not complete:return 'tool_progress'
    return 'verified_pass' if verification['status']=='pass' else 'verified_failure'

def recovery_guidance(goal,observations):
    if (type(goal) is not str or type(observations) is not str
            or not goal or max(len(goal.encode()),len(observations.encode()))>32768):
        raise ValueError('bounded task and already-public observations required')
    return ('The previous attempt did not satisfy host verification. Think carefully about the goal, '
        'the givens,and your assumptions. Identify which assumptions conflict with the observed evidence. '
        'Choose a different approach and verify it with actual granted tools. '
        'File edits and tool effects already acknowledged still exist;reobserve current files before acting. '
        'Do not repeat an unresolved operation or invent a successful result.\n\nGoal:\n'+goal+
        '\n\nAlready-visible tool observations:\n'+observations)


def planning_context(value):
    """Validate a pointer-based host plan annotation, not native mutable state.

    The origin names an existing model frame on FrameKernel. Failed operation
    IDs refer to committed host verdicts; the interpreter proves their visible
    ownership before admission. Grammar/RNG/parser state still belongs to COW.
    """
    keys={'schema','profile','mode','rung','origin_model_frame','handled_failures'}
    if type(value) is not dict or set(value)!=keys or type(value['schema']) is not int or value['schema']!=1:
        raise ValueError('closed thinking plan context required')
    for name in ('profile','origin_model_frame'):
        if type(value[name]) is not str or re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}',value[name]) is None:
            raise ValueError('host profile and original model frame required')
    rungs=ladder(value['mode']);index=value['rung'];failures=value['handled_failures']
    if (type(index) is not int or not 0<=index<len(rungs) or type(failures) is not tuple
            or len(failures)!=index or any(type(op) is not str or re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}',op) is None for op in failures)
            or len(set(failures))!=len(failures)):
        raise ValueError('thinking rung must match distinct handled host failures')
    return {**value,'handled_failures':tuple(failures)}
