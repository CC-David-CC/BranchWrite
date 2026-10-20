"""Real MCP stdio transport to the bounded Blender tool; no COW credentials."""
from pathlib import Path
import asyncio,base64,json,os
from datetime import timedelta

def render_through_mcp(python,runtime,sources,entry,*,timeout=120):
    # Imported only by an operator-enabled Blender capability. Ordinary BW
    # clients need neither the MCP SDK nor Blender installed in their venv.
    async def call():
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        env=dict(PATH='/usr/bin:/bin',HOME='/tmp',LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1',
            BW_BLENDER_RUNTIME=str(runtime),BW_BLENDER_TIMEOUT=str(timeout),
            PYTHONPATH=str(Path(__file__).resolve().parent.parent))
        params=StdioServerParameters(command=str(python),args=['-B','-m','branchwrite.blender_mcp_server'],env=env)
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=2*timeout+60)) as session:
                initialized=await session.initialize();menu=await session.list_tools()
                if [t.name for t in menu.tools]!=['render_scene']:raise ValueError('unrecognized Blender MCP tool menu')
                reply=await session.call_tool('render_scene',dict(entry=entry,files={n:base64.b64encode(raw).decode() for n,raw in sources}))
                if reply.isError:raise ValueError('Blender MCP tool failed: '+str(reply.content)[:4096])
                result=reply.structuredContent
                if result is None:
                    if len(reply.content)!=1 or reply.content[0].type!='text':raise ValueError('invalid Blender MCP result')
                    result=json.loads(reply.content[0].text)
                if type(result) is not dict or result.get('status') not in ('PASS','FAIL') or type(result.get('assets')) is not dict:raise ValueError('closed Blender MCP result required')
                result['assets']={n:base64.b64decode(raw,validate=True) for n,raw in result['assets'].items()}
                result['mcp']=dict(initialized=True,protocol_version=initialized.protocolVersion,server=initialized.serverInfo.model_dump(),tool='render_scene',transport='stdio')
                return result
    return asyncio.run(call())

def main():
    import sys
    request=json.load(sys.stdin)
    if type(request) is not dict or set(request)!={'python','runtime','timeout','entry','files'}:raise ValueError('closed Blender transport request required')
    sources=tuple((n,base64.b64decode(raw,validate=True)) for n,raw in request['files'].items())
    result=render_through_mcp(Path(request['python']),Path(request['runtime']),sources,request['entry'],timeout=request['timeout'])
    result['assets']={n:base64.b64encode(raw).decode() for n,raw in result['assets'].items()}
    json.dump(result,sys.stdout,separators=(',',':'));sys.stdout.write('\n')
if __name__=='__main__':main()
