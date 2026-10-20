"""Resolve human selectors to immutable saved-turn identities before admission."""

CONTROL_MODES = {'edit', 'explore', 'select'}


def control_request(message, mode):
    text=message.strip()
    if mode=='select':
        if not text or len(text.split())!=1:
            raise ValueError('Choose one saved turn number from /history')
        return text, ''
    first, _, rest=text.partition(' ')
    if first=='last' or first.isdecimal() or first.startswith('turn-'):
        selector, task=first, rest.strip()
    else:selector, task='last', text
    if not task:raise ValueError('Add the new request after the saved turn')
    return selector, task


def control_target(history, message, mode, *, pinned=None):
    selector, task=control_request(message,mode)
    def eligible(row):
        result=row.get('result')
        return (result is not None and result.get('file_commit') is not None
                and row['input']['mode']!='aside'
                and (mode=='select' or row['input']['mode'] in ('work','edit','explore')))
    if pinned is not None:
        found=[row for row in history if row['id']==pinned and eligible(row)]
    elif selector=='last':
        found=[row for row in history if eligible(row)][-1:]
    elif selector.isdecimal():
        index=int(selector)-1
        found=history[index:index+1] if 0<=index<len(history) else []
        found=[row for row in found if eligible(row)]
    else:
        found=[row for row in history if row['id'].startswith(selector) and eligible(row)]
    if len(found)!=1:
        raise ValueError('Choose a completed saved turn from /history; edit/explore require a Work turn')
    return found[0], task


def unfinished_task(history, source, message):
    """Derive one next input from canonical intents missing from the chosen tip.

    A completed ModelOutput proves the current request is in its saved context.
    Before that boundary, steering falls back to an older model tip: carry the
    unfinished user intent as data in the new request. Keep old records intact.
    Branch references can differ while selecting the same exact saved prefix.
    """
    context=source.get('context')
    if not context:return message
    identity=('tip','root','model_contract_id','execution_profile_id')
    same=lambda other:other is not None and all(other.get(k)==context.get(k) for k in identity)
    rows={row['id']:row for row in history};turn=source.get('turn');seen=set();messages=[]
    while turn:
        if turn in seen:raise ValueError('Saved request source cycle')
        seen.add(turn)
        if turn not in rows:raise ValueError('Saved request source is missing')
        row=rows[turn];result=row.get('result');data=row['input']
        if result is None or not same(result.get('context')):break
        mode=data['mode']
        if mode=='select':turn=data['target'];continue
        pending=result.get('unfinished_request')
        if pending is None:pending=(result['context'].get('mode')=='context' and context.get('mode')=='context')
        if result.get('status') not in ('interrupted','waiting') or not pending:break
        if mode in ('edit','explore'):
            messages.append(control_request(data['message'],mode)[1]);break
        if mode in ('work','plan','chat'):messages.append(data['message'])
        turn=data['source'].get('turn')
    if not messages:return message
    return ('Earlier unfinished request and updates:\n'+'\n\n'.join(reversed(messages))
            +'\n\nNew instruction:\n'+message)
