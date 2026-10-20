"""Fixed millimetre plate requirements; authoring code is not acceptance evidence."""
from dataclasses import dataclass,asdict
from hashlib import sha256
import json,math

@dataclass(frozen=True)
class PlateSpec:
    width_x:float
    length_y:float
    thickness_z:float
    hole_diameter:float
    spacing_x:float
    spacing_y:float
    edge_material:float
    notch_depth:float
    notch_width:float
    def __post_init__(self):
        for name,value in asdict(self).items():
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=2000:
                raise ValueError('finite positive bounded millimetres required: '+name)
        if self.notch_depth>=self.width_x or self.notch_width>=self.length_y:
            raise ValueError('notch must be smaller than the envelope')
    @classmethod
    def from_document(cls,value):
        if type(value) is not dict or set(value)!={'schema','units','frame','holes','notch','additional_features','dimensions'}:
            raise ValueError('closed plate requirement document required')
        if type(value['dimensions']) is not dict:raise ValueError('exact dimensions required')
        try:spec=cls(**value['dimensions'])
        except TypeError as exc:raise ValueError('closed plate dimensions required') from exc
        if value!=spec.document():raise ValueError('unsupported plate requirement conventions')
        return spec
    def document(self):
        return dict(schema='bw.plate.v1',units='mm',frame='X-width,Y-length,Z-up; origin mid-XY,bottom-Z',
            holes='four centered through-holes',notch='positive-X,centered-Y,through-thickness',
            additional_features=False,dimensions=asdict(self))
    @property
    def identity(self):
        return sha256(json.dumps(self.document(),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    def feasibility(self):
        minimum_x=self.spacing_x+2*(self.edge_material+self.hole_diameter/2)
        minimum_y=self.spacing_y+2*(self.edge_material+self.hole_diameter/2)
        conflicts=[]
        if self.width_x<minimum_x:conflicts.append(dict(requirement='edge_material_x',minimum_mm=minimum_x,requested_mm=self.width_x,formula='spacing_x + 2*(edge_material + hole_diameter/2)'))
        if self.length_y<minimum_y:conflicts.append(dict(requirement='edge_material_y',minimum_mm=minimum_y,requested_mm=self.length_y,formula='spacing_y + 2*(edge_material + hole_diameter/2)'))
        dx=max(self.width_x/2-self.notch_depth-self.spacing_x/2,0)
        dy=max(self.spacing_y/2-self.notch_width/2,0)
        clearance=math.hypot(dx,dy)-self.hole_diameter/2
        if clearance<self.edge_material:conflicts.append(dict(requirement='notch_edge_material',available_mm=clearance,required_mm=self.edge_material))
        return dict(feasible=not conflicts,minimum_width_mm=minimum_x,minimum_length_mm=minimum_y,conflicts=conflicts)

def requirements_from_document(value):
    if type(value) is dict and value.get('schema')=='bw.module-carrier.v1':
        from .cad_carrier import CarrierSpec
        return CarrierSpec.from_document(value)
    return PlateSpec.from_document(value)
