"""Display-only labels from closed admitted tool names.

Never include tool arguments, paths, commands, output or model text. This view
is not a receipt and never authorizes execution or implies a passing check.
"""
from .records import decode

_LABELS={
 'read_file':'Reading a project file...',
 'create_file':'Creating a project file...',
 'create_text_file':'Creating a text file...',
 'replace_text_file':'Updating a text file...',
 'replace':'Editing a project file...',
 'set_mode':'Changing file permissions...',
 'run_tests':'Running unit tests...',
 'run_shell':'Running a project command...',
 'run_check':'Running a project check...',
 'capture_page':'Opening the page in a browser...',
 'interact_page':'Checking the page in a browser...',
 'remote_command':'Running a command on an authorized host...',
 'check_remote':'Checking an authorized host...',
 'upload_file':'Uploading a project file...',
 'build_pdf':'Building and checking the PDF...',
 'render_pdf':'Rendering the PDF page...',
 'inspect_scene':'Building and rendering the Blender scene...',
 'inspect_cad':'Building, measuring and rendering CAD...',
 'finish':'Recording the final answer...',
}

def tool_start_event(plan_bytes,registry_identity,world):
    try:data=decode(plan_bytes)
    except (ValueError,TypeError,UnicodeError):return None
    if (type(data) is not tuple or len(data)!=8
        or data[:3]!=('bw.tool-plan.v2',registry_identity,world)
        or type(data[3]) is not str or data[3] not in _LABELS):return None
    return 'tool_started/'+data[3]

def detail_message(event):
    if type(event) is not str or not event.startswith('tool_started/'):return None
    return _LABELS.get(event[len('tool_started/'):])
