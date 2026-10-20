"""Inspect reopened STEP geometry, never candidate constants or pass flags.

The reference CSG uses direct OCCT primitives, independent of candidate Python
and build123d construction helpers. Both still share OpenCascade: this is not an
independent verification of the CAD kernel. Manufactured fit is not measured.
Run this parser in the bounded CAD worker before accepting untrusted exports.
"""
from pathlib import Path
import errno,hashlib,math,os,stat,tempfile
from .cad_requirements import PlateSpec
# Frozen from baseline 97/100/110mm STEP round trips,2026-10-20:
# max bbox error0, max analytic volume error8.74e-11mm^3.
LENGTH_TOL_MM=1e-6
VOLUME_TOL_MM3=1e-5
MAX_STEP_BYTES=64*1024*1024

def _reference(spec):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Pnt,gp_Dir,gp_Ax2
    s=spec
    shape=BRepPrimAPI_MakeBox(gp_Pnt(-s.width_x/2,-s.length_y/2,0),s.width_x,s.length_y,s.thickness_z).Shape()
    for x in (-s.spacing_x/2,s.spacing_x/2):
        for y in (-s.spacing_y/2,s.spacing_y/2):
            cylinder=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,0),gp_Dir(0,0,1)),s.hole_diameter/2,s.thickness_z).Shape()
            shape=BRepAlgoAPI_Cut(shape,cylinder).Shape()
    notch=BRepPrimAPI_MakeBox(gp_Pnt(s.width_x/2-s.notch_depth,-s.notch_width/2,0),s.notch_depth,s.notch_width,s.thickness_z).Shape()
    return BRepAlgoAPI_Cut(shape,notch).Shape()

def _volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    p=GProp_GProps();BRepGProp.VolumeProperties_s(shape,p);return p.Mass()

def read_step_bytes(path):
    absolute=Path(path).absolute()
    if '..' in absolute.parts:raise ValueError('parent traversal is not an artifact path')
    directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=following
        fd=os.open(absolute.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
    except OSError as error:
        if error.errno in (errno.ELOOP,errno.ENOTDIR):raise ValueError('linked/non-directory artifact path refused') from error
        raise
    finally:os.close(directory)
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('regular STEP input required')
        raw=stream.read(MAX_STEP_BYTES+1)
    if not raw or len(raw)>MAX_STEP_BYTES:raise ValueError('bounded nonempty STEP input required')
    return raw

def inspect_step(path,spec):
    from .cad_carrier import CarrierSpec,inspect_carrier
    if type(spec) is CarrierSpec:return inspect_carrier(path,spec)
    if type(spec) is not PlateSpec:raise ValueError('fixed PlateSpec required')
    raw=read_step_bytes(path)
    # Immutable captured bytes are parsed, not a candidate-controlled live path.
    import build123d as b
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    with tempfile.TemporaryDirectory(prefix='bw-cad-inspect-') as tmp:
        captured=Path(tmp)/'part.step';captured.write_bytes(raw);shape=b.import_step(captured)
    feasibility=spec.feasibility()
    report=dict(schema=1,status='INFEASIBLE' if not feasibility['feasible'] else 'FAIL',
        requirements_id=spec.identity,artifact_sha256=hashlib.sha256(raw).hexdigest(),
        length_tolerance_mm=LENGTH_TOL_MM,volume_tolerance_mm3=VOLUME_TOL_MM3,
        feasibility=feasibility,checks={},measurements={})
    if not feasibility['feasible']:return report
    checks=report['checks'];measure=report['measurements'];s=spec;t=LENGTH_TOL_MM
    def check(name,passed,actual=None,expected=None):
        checks[name]={'pass':bool(passed),'actual':actual,'expected':expected}
    solids=shape.solids();check('valid_shape',shape.is_valid)
    # A compound can contain one solid plus loose faces/edges/vertices whose
    # zero volume would evade both volume and material-difference checks.
    topology={name:len(getattr(shape,name)()) for name in ('faces','edges','vertices')}
    solid_topology={} if len(solids)!=1 else {name:len(getattr(solids[0],name)()) for name in topology}
    measure['topology']=topology
    check('single_solid',len(solids)==1 and topology==solid_topology,
        dict(solids=len(solids),all_topology=topology,solid_topology=solid_topology),'one solid with no loose geometry')
    box=shape.bounding_box();bounds=[box.min.X,box.max.X,box.min.Y,box.max.Y,box.min.Z,box.max.Z]
    expected=[-s.width_x/2,s.width_x/2,-s.length_y/2,s.length_y/2,0,s.thickness_z]
    measure['bounds_mm']=bounds;check('bounds',all(abs(x-y)<=t for x,y in zip(bounds,expected)),bounds,expected)
    expected_volume=s.width_x*s.length_y*s.thickness_z-4*math.pi*(s.hole_diameter/2)**2*s.thickness_z-s.notch_depth*s.notch_width*s.thickness_z
    measure['volume_mm3']=shape.volume;check('volume',abs(shape.volume-expected_volume)<=VOLUME_TOL_MM3,shape.volume,expected_volume)
    holes=[];cylinders=[];walls=[];notch_floor=False
    for face in shape.faces():
        bb=face.bounding_box()
        if face.geom_type==b.GeomType.CYLINDER:
            cylinder=BRepAdaptor_Surface(face.wrapped).Cylinder();axis=cylinder.Axis();direction=axis.Direction();loc=axis.Location()
            row=dict(x=loc.X(),y=loc.Y(),diameter=2*cylinder.Radius(),z_min=bb.min.Z,z_max=bb.max.Z,axis_z=direction.Z())
            holes.append(row);cylinders.append(face)
        elif face.geom_type==b.GeomType.PLANE and abs(face.normal_at().Z)<=t:
            walls.append(face)
            if (abs(bb.min.X-(s.width_x/2-s.notch_depth))<=t and abs(bb.max.X-bb.min.X)<=t
                and abs(bb.min.Y+s.notch_width/2)<=t and abs(bb.max.Y-s.notch_width/2)<=t
                and abs(bb.min.Z)<=t and abs(bb.max.Z-s.thickness_z)<=t):notch_floor=True
    holes.sort(key=lambda h:(h['x'],h['y']));measure['holes']=holes
    desired=sorted((x,y) for x in (-s.spacing_x/2,s.spacing_x/2) for y in (-s.spacing_y/2,s.spacing_y/2))
    check('hole_pattern',len(holes)==4 and all(abs(h['x']-x)<=t and abs(h['y']-y)<=t for h,(x,y) in zip(holes,desired)))
    check('hole_diameter',len(holes)==4 and all(abs(h['diameter']-s.hole_diameter)<=t for h in holes))
    through=len(holes)==4 and all(abs(abs(h['axis_z'])-1)<=t and abs(h['z_min'])<=t and abs(h['z_max']-s.thickness_z)<=t
        and not any(shape.is_inside((h['x'],h['y'],s.thickness_z*f)) for f in (.1,.5,.9)) for h in holes)
    check('through_holes',through)
    notch_open=not shape.is_inside((s.width_x/2-s.notch_depth/2,0,s.thickness_z/2))
    negative_solid=shape.is_inside((-s.width_x/2+s.notch_depth/2,0,s.thickness_z/2))
    check('locating_notch',notch_floor and notch_open and negative_solid)
    clearance=min((hole.distance_to(wall) for hole in cylinders for wall in walls),default=0)
    measure['minimum_edge_material_mm']=clearance;check('edge_material',clearance>=s.edge_material-t,clearance,s.edge_material)
    reference=_reference(s)
    extra=_volume(BRepAlgoAPI_Cut(shape.wrapped,reference).Shape());missing=_volume(BRepAlgoAPI_Cut(reference,shape.wrapped).Shape())
    measure['extra_material_mm3']=extra;measure['missing_material_mm3']=missing
    check('material_geometry',abs(extra)<=VOLUME_TOL_MM3 and abs(missing)<=VOLUME_TOL_MM3)
    report['status']='PASS' if all(v['pass'] for v in checks.values()) else 'FAIL'
    return report
