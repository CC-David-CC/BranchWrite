"""Pilot removable module carrier/base: nominal CAD fit, not physical fit.

Dimensions are task-family fixtures, not David's hardware specification. Source
is ordinary build123d Python; this checker reopens STEP without importing it.
"""
from dataclasses import dataclass,asdict
from hashlib import sha256
from pathlib import Path
import json,math,tempfile

def _identity(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@dataclass(frozen=True)
class CarrierSpec:
    base_x:float=120
    base_y:float=80
    base_z:float=6
    carrier_x:float=80
    carrier_y:float=50
    carrier_z:float=4
    seat_depth:float=2
    clearance:float=.3
    key_depth:float=3
    key_width:float=8
    module_hole_x:float=60
    module_hole_y:float=30
    module_hole_d:float=4
    base_hole_x:float=100
    base_hole_y:float=60
    base_hole_d:float=6
    def __post_init__(self):
        for name,value in asdict(self).items():
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=2000:raise ValueError('finite bounded positive carrier dimensions required: '+name)
        if (self.seat_depth>=min(self.base_z,self.carrier_z) or self.carrier_x+2*self.clearance>=self.base_x or self.carrier_y+2*self.clearance>=self.base_y
            or self.key_depth+self.clearance>=self.carrier_x/2 or self.key_width+2*self.clearance>=self.module_hole_y-self.module_hole_d
            or self.module_hole_x+self.module_hole_d>=self.carrier_x or self.module_hole_y+self.module_hole_d>=self.carrier_y
            or self.base_hole_x+self.base_hole_d>=self.base_x or self.base_hole_y+self.base_hole_d>=self.base_y):raise ValueError('invalid carrier fit/interface envelope')
    def document(self):
        return dict(schema='bw.module-carrier.v1',units='mm',frame='assembled; centered XY; base bottom Z=0; carrier bottom at pocket floor',
            parts=['base','carrier'],key='positive-X centered-Y',additional_features=False,dimensions=asdict(self))
    @classmethod
    def from_document(cls,value):
        if type(value) is not dict or type(value.get('dimensions')) is not dict:raise ValueError('closed carrier requirements required')
        try:s=cls(**value['dimensions'])
        except TypeError as e:raise ValueError('closed carrier dimensions required') from e
        if value!=s.document():raise ValueError('unsupported carrier conventions')
        return s
    @property
    def identity(self):return _identity(self.document())
    @property
    def interface_id(self):
        # Top thickness may change. Seating, footprint, key and hole patterns stay
        # fixed. A changed interface receives a different compatibility identity.
        return _identity({k:v for k,v in asdict(self).items() if k!='carrier_z'})

def _references(s):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
    from OCP.gp import gp_Pnt,gp_Dir,gp_Ax2
    def box(x,y,z,dx,dy,dz):return BRepPrimAPI_MakeBox(gp_Pnt(x,y,z),dx,dy,dz).Shape()
    def cut(a,b):return BRepAlgoAPI_Cut(a,b).Shape()
    z=s.base_z-s.seat_depth
    base=box(-s.base_x/2,-s.base_y/2,0,s.base_x,s.base_y,s.base_z)
    base=cut(base,box(-s.carrier_x/2-s.clearance,-s.carrier_y/2-s.clearance,z,s.carrier_x+2*s.clearance,s.carrier_y+2*s.clearance,s.seat_depth))
    base=BRepAlgoAPI_Fuse(base,box(s.carrier_x/2-s.key_depth,-s.key_width/2,z,s.key_depth+s.clearance,s.key_width,s.seat_depth)).Shape()
    carrier=box(-s.carrier_x/2,-s.carrier_y/2,z,s.carrier_x,s.carrier_y,s.carrier_z)
    carrier=cut(carrier,box(s.carrier_x/2-s.key_depth-s.clearance,-s.key_width/2-s.clearance,z,s.key_depth+s.clearance,s.key_width+2*s.clearance,s.carrier_z))
    for name,hx,hy,diameter,z0,height in [('base',s.base_hole_x,s.base_hole_y,s.base_hole_d,0,s.base_z),('carrier',s.module_hole_x,s.module_hole_y,s.module_hole_d,z,s.carrier_z)]:
        shape=base if name=='base' else carrier
        for x in (-hx/2,hx/2):
            for y in (-hy/2,hy/2):shape=cut(shape,BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z0),gp_Dir(0,0,1)),diameter/2,height).Shape())
        if name=='base':base=shape
        else:carrier=shape
    return base,carrier

def inspect_carrier(path,spec):
    from .cad_inspect import read_step_bytes,_volume,LENGTH_TOL_MM,VOLUME_TOL_MM3
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Common
    import build123d as b
    if type(spec) is not CarrierSpec:raise ValueError('fixed CarrierSpec required')
    raw=read_step_bytes(path)
    with tempfile.TemporaryDirectory(prefix='bw-carrier-inspect-') as tmp:
        p=Path(tmp)/'part.step';p.write_bytes(raw);shape=b.import_step(p)
    solids=sorted(shape.solids(),key=lambda o:o.bounding_box().min.Z);checks={};measure={}
    checks['valid_shape']=bool(shape.is_valid)
    checks['two_complete_solids']=(len(solids)==2 and all(len(getattr(shape,n)())==sum(len(getattr(o,n)()) for o in solids) for n in ('faces','edges','vertices')))
    if len(solids)==2:
        references=_references(spec)
        for name,part,reference in zip(('base','carrier'),solids,references):
            extra=_volume(BRepAlgoAPI_Cut(part.wrapped,reference).Shape());missing=_volume(BRepAlgoAPI_Cut(reference,part.wrapped).Shape())
            measure[name]=dict(extra_material_mm3=extra,missing_material_mm3=missing,volume_mm3=part.volume)
            checks[name+'_material_geometry']=(abs(extra)<=VOLUME_TOL_MM3 and abs(missing)<=VOLUME_TOL_MM3)
        common=_volume(BRepAlgoAPI_Common(solids[0].wrapped,solids[1].wrapped).Shape());measure['interference_mm3']=common;checks['no_interference']=abs(common)<=VOLUME_TOL_MM3
        # Locate actual pocket wall faces and compare them with actual carrier
        # bounds. Full material checks above distinguish other same-bounds parts.
        base,carrier=solids;cb=carrier.bounding_box();z=spec.base_z-spec.seat_depth
        walls=[]
        for face in base.faces():
            bb=face.bounding_box()
            if face.geom_type==b.GeomType.PLANE and abs(bb.max.X-bb.min.X)<=LENGTH_TOL_MM and abs(bb.min.Z-z)<=LENGTH_TOL_MM and abs(bb.max.Z-spec.base_z)<=LENGTH_TOL_MM:
                walls.append(bb.min.X)
        left=[x for x in walls if x<cb.min.X]
        clearance=cb.min.X-max(left) if left else None
        measure['pocket_clearance_x_mm']=clearance
        checks['measured_nominal_clearance']=clearance is not None and abs(clearance-spec.clearance)<=LENGTH_TOL_MM
    return dict(schema=1,status='PASS' if all(checks.values()) else 'FAIL',requirements_id=spec.identity,interface_id=spec.interface_id,
        artifact_sha256=sha256(raw).hexdigest(),checks=checks,measurements=measure,length_tolerance_mm=LENGTH_TOL_MM,
        volume_tolerance_mm3=VOLUME_TOL_MM3,scope='actual STEP geometry and nominal interface only; physical manufactured fit not tested')
