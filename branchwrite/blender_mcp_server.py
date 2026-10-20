"""Ephemeral stdio MCP tool for isolated Blender jobs, not another workflow.

No network listener, asset service, addon auto-installer or telemetry. BW alone
owns admission/ledger/branches. MCP is the tool transport. The third-party live
addon was inspected but is not installed by this bounded CPU-render integration.
"""
import base64,os
from pathlib import Path

def main():
    from mcp.server.fastmcp import FastMCP
    from .blender_execution import BlenderRuntime,build_scene
    runtime=BlenderRuntime(Path(os.environ['BW_BLENDER_RUNTIME']),timeout=float(os.environ.get('BW_BLENDER_TIMEOUT','120')))
    server=FastMCP('BranchWrite bounded Blender')
    @server.tool()
    def render_scene(entry:str,files:dict[str,str])->dict:
        """Build captured Python, independently reopen scene.blend, render fixed views and a two-second animation. File values are base64; no host paths or network grants."""
        if len(files)>1000 or sum(len(s) for s in files.values())>90*1024*1024:raise ValueError('bounded captured scene sources required')
        sources=tuple((name,base64.b64decode(raw,validate=True)) for name,raw in files.items())
        result=build_scene(sources,entry,runtime)
        result['assets']={name:base64.b64encode(raw).decode() for name,raw in result['assets'].items()}
        return result
    server.run(transport='stdio')
if __name__=='__main__':main()
