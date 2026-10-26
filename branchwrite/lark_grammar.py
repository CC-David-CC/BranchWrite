"""Optional compilation of BW's generated GBNF into structured Lark.

llguidance's GBNF converter otherwise treats acyclic action/array rules as
lexical regular expressions. Preserve those boundaries while retaining string
lexemes. No limits, literals, repetitions, grants or workflow records change.
"""

def tool_lark(source):
    try:
        import llguidance
        from llguidance.gbnf_to_lark import GrammarParser, resolve
    except ImportError as exc:
        raise ValueError('Lark tool grammar requires optional llguidance 1.9.1') from exc
    if getattr(llguidance, '__version__', None) != '1.9.1':
        raise ValueError('Lark tool grammar requires pinned llguidance 1.9.1')
    rules = GrammarParser().parse(source)
    resolve(rules)
    # resolve() binds RuleRefNode.target objects. Renaming those objects also
    # updates every reference without replacing text inside quoted literals.
    structured = {'TEXT_LINES', 'BROWSER_ACTIONS', 'BROWSER_ACTION',
                  'BROWSER_CLICK', 'BROWSER_FILL'}
    for rule in rules.values():
        if rule.name.startswith('CALL_') or rule.name in structured:
            rule.name = rule.name.lower()
    return '%llguidance {}\n' + '\n'.join(
        str(rule) for rule in sorted(rules.values(), key=lambda rule: rule.order)) + '\n'
