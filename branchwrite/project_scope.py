"""Expand host-selected project directories into immutable exact file grants.

No wildcard remains at execution; later files acquire no authority automatically.
Selection observes names, not a content snapshot. Admission captures actual
copied input bytes separately through project_baseline.
"""
import os,stat
from pathlib import Path
from .execution import Executor,ToolRejected,_relative_path

def expand_directories(project,directories):
    project=Path(project).resolve(strict=True)
    if isinstance(directories,(str,bytes)):raise ValueError('directory list required')
    directories=tuple(directories)
    if len(directories)>128:raise ValueError('too many directory scopes')
    if any(type(value) is not str for value in directories):raise ValueError('relative directories required')
    reader=Executor(project,project.parent,project)
    validated=[]
    for directory in sorted(set(directories)):
        if type(directory) is not str:raise ValueError('relative directory required')
        if directory!='.':_relative_path(directory)
        if '.git' in Path(directory).parts:raise ValueError('Git administration is not a project grant')
        prefix=Path() if directory=='.' else Path(directory)
        probe=(prefix/'.bw-scope-probe').as_posix()
        with reader._parent_directory(probe) as (rootfd,_):
            pass
        validated.append(prefix)
    validated.sort(key=lambda prefix:(len(prefix.parts),prefix.as_posix()))
    minimal=[]
    for prefix in validated:
        if any(prefix.parts[:len(kept.parts)]==kept.parts for kept in minimal):continue
        minimal.append(prefix)
    selected=set();seen=set();total=0
    for prefix in minimal:
        probe=(prefix/'.bw-scope-probe').as_posix()
        with reader._parent_directory(probe) as (rootfd,_):
            for current,dirs,files,fd in os.fwalk('.',dir_fd=rootfd,follow_symlinks=False):
                relative=prefix/Path(current)
                if len(relative.parts)>64:raise ToolRejected('directory scope exceeds nesting bound')
                dirs[:]=[name for name in dirs if name!='.git']
                for name in dirs:
                    info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                    if not stat.S_ISDIR(info.st_mode):raise ToolRejected('directory scope contains a link')
                    seen.add((relative/name).as_posix())
                for name in files:
                    if name=='.git':continue
                    path=(relative/name).as_posix();path.encode('utf8')
                    info=os.stat(name,dir_fd=fd,follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:
                        raise ToolRejected('directory scope contains a link or special file')
                    if path not in selected:total+=info.st_size
                    selected.add(path);seen.add(path)
                    if info.st_size>4*1024**2:raise ToolRejected('scoped file exceeds bound')
                if len(seen)>20000 or total>64*1024**2:raise ToolRejected('directory scope exceeds project bounds')
    return sorted(selected)
