import asyncio
import os
from morphomesh.server import mcp, HUMAN_TOOL_NAMES, CREATURE_TOOL_NAMES

async def check():
    os.environ.pop('MORPHOMESH_INCLUDE_HUMAN_TOOLS', None)
    tools = await mcp.list_tools()
    print('Default count:', len(tools))
    assert len(tools) == 7, f'Expected 7, got {len(tools)}'
    names = {t.name for t in tools}
    assert names == CREATURE_TOOL_NAMES, f'Expected creature tools only, got {names}'

    os.environ['MORPHOMESH_INCLUDE_HUMAN_TOOLS'] = '1'
    tools_all = await mcp.list_tools()
    print('Enabled count:', len(tools_all))
    assert len(tools_all) == 12, f'Expected 12, got {len(tools_all)}'
    names_all = {t.name for t in tools_all}
    assert names_all == CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES

    os.environ.pop('MORPHOMESH_INCLUDE_HUMAN_TOOLS', None)
    res = await mcp.call_tool('morphomesh_create_human_asset', {'character_name': 'TestChar'})
    print('Direct call_tool when unlisted works:', len(res) > 0)

    import mcp.types as mcp_types
    if mcp_types.ListToolsRequest in mcp._mcp_server.request_handlers:
        handler = mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]
        os.environ.pop('MORPHOMESH_INCLUDE_HUMAN_TOOLS', None)
        low_res = await handler(mcp_types.ListToolsRequest())
        print('Low level default count:', len(low_res.root.tools))
        assert len(low_res.root.tools) == 7

        os.environ['MORPHOMESH_INCLUDE_HUMAN_TOOLS'] = 'true'
        low_res_all = await handler(mcp_types.ListToolsRequest())
        print('Low level enabled count:', len(low_res_all.root.tools))
        assert len(low_res_all.root.tools) == 12

    print('ALL TOGGLE & DISCOVERY TESTS PASSED PERFECTLY!')

asyncio.run(check())
