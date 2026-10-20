"""Closed operator-selected CAD environment; never supplied by model output."""
from pathlib import Path
from .cad_requirements import requirements_from_document

def validate_cad_config(spec):
    if type(spec) is not dict or set(spec)!={'python','osmesa','timeout','requirements'}:
        raise ValueError('closed CAD environment and requirement definition required')
    import math
    for key in ('python','osmesa'):
        if type(spec[key]) is not str or not Path(spec[key]).is_absolute():raise ValueError('absolute CAD runtime path required')
    if type(spec['timeout']) not in (int,float) or not math.isfinite(spec['timeout']) or not 0<spec['timeout']<=120:raise ValueError('bounded CAD timeout required')
    requirements_from_document(spec['requirements'])
    return spec

def load_cad_config(spec):
    from .cad_tools import CadCapability
    from .cad_execution import CadRuntime
    validate_cad_config(spec)
    return CadCapability(CadRuntime(Path(spec['python']),timeout=spec['timeout'],osmesa=Path(spec['osmesa'])),requirements_from_document(spec['requirements']))
