"""A purchased ISO 4762 component; dimensions are millimetres.

simple=True omits helical thread geometry. This is an assembly representation,
not evidence of thread fit, screw access or print/manufacturing tolerances.
"""
from build123d import export_step
from bd_warehouse.fastener import SocketHeadCapScrew

screw = SocketHeadCapScrew(
    size="M4-0.7",
    length=16,
    fastener_type="iso4762",
    simple=True,
)
export_step(screw, "m4_socket_head_screw.step")
