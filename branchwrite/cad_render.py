"""CPU depth-buffer views of reopened CAD geometry using VTK/OSMesa.

No GUI or model-supplied picture is used. The host must provide the declared
OSMesa runtime; absence is an error, never a fallback to fabricated diagrams.
"""
from pathlib import Path
import base64,hashlib,json,tempfile
from .cad_inspect import read_step_bytes

# Camera direction from target, view-up, readable world-frame convention.
CAMERAS={
 'top':((0,0,1),(0,1,0),'Top: +X right, +Y up'),
 'bottom':((0,0,-1),(0,-1,0),'Bottom: +X right, -Y up'),
 'side':((0,-1,0),(0,0,1),'Side from -Y: +X right, +Z up'),
 'isometric':((1,-1,1),(0,0,1),'Isometric from +X, -Y, +Z'),
}

def render_step(path,output_dir):
    import build123d as b
    import vtk
    from PIL import Image
    raw=read_step_bytes(path);identity=hashlib.sha256(raw).hexdigest()
    with tempfile.TemporaryDirectory(prefix='bw-cad-render-') as tmp:
        captured=Path(tmp)/'part.step';captured.write_bytes(raw);part=b.import_step(captured)
    points,triangles=part.tessellate(0.05,0.1)
    if not points or not triangles or len(triangles)>1000000:raise ValueError('bounded nonempty CAD mesh required')
    vertices=vtk.vtkPoints()
    for p in points:vertices.InsertNextPoint(p.X,p.Y,p.Z)
    cells=vtk.vtkCellArray()
    for triangle in triangles:
        cells.InsertNextCell(3)
        for index in triangle:cells.InsertCellPoint(index)
    poly=vtk.vtkPolyData();poly.SetPoints(vertices);poly.SetPolys(cells)
    clean=vtk.vtkCleanPolyData();clean.SetInputData(poly)
    normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(clean.GetOutputPort());normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.SetFeatureAngle(45)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());mapper.ScalarVisibilityOff()
    actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.35,.6,.8);actor.GetProperty().SetAmbient(.25);actor.GetProperty().SetDiffuse(.75)
    out=Path(output_dir);out.mkdir(mode=0o700,parents=False,exist_ok=False)
    box=part.bounding_box();center=box.center();distance=max(box.size.X,box.size.Y,box.size.Z)*3
    window=vtk.vtkOSOpenGLRenderWindow();window.SetOffScreenRendering(1);window.SetSize(770,550);window.SetMultiSamples(0)
    renderer=vtk.vtkRenderer();renderer.SetBackground(.97,.98,1);renderer.AddActor(actor);window.AddRenderer(renderer)
    label=vtk.vtkTextActor();label.SetPosition(20,510);label.GetTextProperty().SetFontSize(20);label.GetTextProperty().SetColor(.1,.15,.2);renderer.AddViewProp(label)
    bound_text=vtk.vtkTextActor();bound_text.SetPosition(20,15);bound_text.GetTextProperty().SetFontSize(14);bound_text.GetTextProperty().SetColor(.15,.2,.25)
    bound_text.SetInput('Measured bounds (mm): X [%g, %g]  Y [%g, %g]  Z [%g, %g]'%(box.min.X,box.max.X,box.min.Y,box.max.Y,box.min.Z,box.max.Z));renderer.AddViewProp(bound_text)
    views={};capabilities=None
    try:
        for name,(direction,up,title) in CAMERAS.items():
            camera=renderer.GetActiveCamera();camera.ParallelProjectionOn();camera.SetFocalPoint(center.X,center.Y,center.Z)
            position=[value+distance*delta for value,delta in zip((center.X,center.Y,center.Z),direction)]
            camera.SetPosition(*position);camera.SetViewUp(*up);renderer.ResetCamera();camera.Zoom(1.1);renderer.ResetCameraClippingRange();label.SetInput(title)
            window.Render()
            if capabilities is None:capabilities=window.ReportCapabilities()
            capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
            image=out/(name+'.png');writer=vtk.vtkPNGWriter();writer.SetFileName(str(image));writer.SetInputConnection(capture.GetOutputPort());writer.Write()
            views[name]=dict(path=str(image),sha256=hashlib.sha256(image.read_bytes()).hexdigest(),camera_position=list(camera.GetPosition()),focal_point=list(camera.GetFocalPoint()),view_up=list(camera.GetViewUp()),parallel_scale=camera.GetParallelScale(),orientation=title)
    finally:window.Finalize()
    sheet=Image.new('RGB',(1540,1100),'white')
    for index,row in enumerate(views.values()):
        with Image.open(row['path']) as image:sheet.paste(image.convert('RGB'),((index%2)*770,(index//2)*550))
    contact=out/'views.png';sheet.save(contact)
    report=dict(schema=1,artifact_sha256=identity,triangles=len(triangles),mesh_tolerance_mm=.05,views=views,
        renderer=dict(kind='VTK-OSMesa',version=vtk.vtkVersion.GetVTKVersion(),capabilities=capabilities),
        contact_sheet=dict(path=str(contact),sha256=hashlib.sha256(contact.read_bytes()).hexdigest()))
    (out/'render.json').write_text(json.dumps(report,indent=2)+'\n')
    html='<!doctype html><meta charset="utf-8"><title>BranchWrite CAD views</title><style>body{font-family:sans-serif;margin:2rem}img{max-width:100%;height:auto}code{overflow-wrap:anywhere}</style><h1>CAD geometry views</h1><p>STEP SHA256: <code>'+identity+'</code></p>'
    for name,row in views.items():html+='<h2>'+name+'</h2><img alt="'+name+' view in the documented world frame" src="data:image/png;base64,'+base64.b64encode(Path(row['path']).read_bytes()).decode()+'">'
    (out/'index.html').write_text(html)
    return report
