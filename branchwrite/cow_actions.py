"""Convert completed COW proposals into independently checked host actions.

The canonical continuation remains in COW. These helpers do not reconstruct a
transcript, parse textual thinking tags, grant authority, or execute model code.
"""
import json

# Owner default for NEW admissions. Persisted grammar/controller budgets stay
# bound to their original generation; never rewrite them during continuation.
DEFAULT_THINKING_TOKENS = 4096


def completed_thinking_text(result, eos_tokens):
    """Require a durable, receipt-bound final; never fall back to raw thought.

    This validates the server's final view, not the truth of the model's answer.
    Text-stop or budget-partial answers without a consumed EOS are not actions.
    """
    view = result.answer.get('thinking')
    tokens = result.answer.get('tokens')
    if (type(view) is not dict or type(view.get('schema')) is not int or view['schema'] != 1
            or view.get('complete') is not True or view.get('snapshot') != result.receipt.snapshot
            or type(view.get('final_text')) is not str
            or not isinstance(tokens, (tuple, list)) or not tokens
            or type(tokens[-1]) is not int or tokens[-1] not in eos_tokens):
        raise ValueError('action requires a complete receipt-bound thinking final and consumed EOS')
    text = view['final_text']
    if len(text.encode('utf8')) > 262144:
        raise ValueError('final action exceeds the host bound')
    return text


def replacement_schema(path):
    from branchwrite.execution import Grant
    Grant((path,), False)
    return dict(type='object', properties=dict(
        tool=dict(type='string', enum=['replace']),
        arguments=dict(type='object', properties=dict(
            path=dict(type='string', enum=[path]),
            before=dict(type='string', minLength=1, maxLength=32768),
            after=dict(type='string', maxLength=32768)),
            required=['path', 'before', 'after'], additionalProperties=False)),
        required=['tool', 'arguments'], additionalProperties=False)


def parse_replacement(text, path):
    """The grammar is guidance; validate again before the existing Grant boundary."""
    if type(text) is not str or len(text.encode('utf8')) > 262144:
        raise ValueError('replacement must be bounded JSON text')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate replacement field')
            value[key] = item
        return value
    def reject(value):
        raise ValueError('non-finite replacement field')
    value = json.loads(text, object_pairs_hook=unique, parse_constant=reject)
    if type(value) is not dict or set(value) != {'tool', 'arguments'} or value['tool'] != 'replace':
        raise ValueError('unexpected replacement action')
    args = value['arguments']
    if (type(args) is not dict or set(args) != {'path', 'before', 'after'} or args['path'] != path
            or type(args['before']) is not str or type(args['after']) is not str):
        raise ValueError('unexpected replacement arguments')
    before, after = args['before'].encode('utf8'), args['after'].encode('utf8')
    if not before or len(before) > 32768 or len(after) > 32768:
        raise ValueError('replacement violates the host byte bound')
    return before, after
