"""Read a context budget bound to the saved coding launch; no workflow work."""
from .coding_cli import read_launch, _client


def budget_saved(state):
    launch=read_launch(state)
    cow=launch['config']['cow']
    client=_client(state,launch)
    budget=client.context_budget(cow['branch'])
    if (budget['model_contract_id']!=cow['model_contract_id']
            or budget['execution_profile_id']!=cow['execution_profile_id']):
        raise ValueError('context budget belongs to a different model or profile')
    head=client.head(cow['branch'])
    if head.revision!=budget['revision'] or head.tip!=budget['snapshot']:
        raise ValueError('COW branch changed during context budget inspection')
    return 0,dict(status='observed',workflow_advanced=False,
                  future_input_included=False,budget=budget)
