"""Actual Blender worker. Build and independent reopen use separate namespaces."""
import base64,json,os,sys,traceback,math
from pathlib import Path
sys.path.insert(0,'/policy')
from cad_build_worker import candidate_process_policy

def inspect():
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath='/inputs/scene.blend',load_ui=False,use_scripts=False)
    scene=bpy.context.scene
    meshes=[o for o in scene.objects if o.type=='MESH']
    if not meshes or len(scene.objects)>64:raise ValueError('bounded nonempty mesh scene required')
    scene.frame_start=1;scene.frame_end=24;scene.render.fps=12
    samples={};observed=[];framing=[]
    # Fit the controlled cameras to evaluated geometry at every rendered frame.
    # A middle-frame box can crop a fast-moving mesh or a modifier's result.
    for frame in range(1,25):
        scene.frame_set(frame)
        graph=bpy.context.evaluated_depsgraph_get()
        evaluated=[o.evaluated_get(graph) for o in meshes]
        if frame in (1,12,24):
            samples[str(frame)]=[dict(name=o.name,matrix=[list(row) for row in o.matrix_world]) for o in evaluated]
        for o in evaluated:
            points=[o.matrix_world@Vector(v) for v in o.bound_box]
            if any(not math.isfinite(v[i]) or abs(v[i])>1e6 for v in points for i in range(3)):
                raise ValueError('scene bounds invalid')
            framing.extend(points)
    moving=samples['1']!=samples['12'] or samples['12']!=samples['24']
    scene.frame_set(12)
    graph=bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        o=obj.evaluated_get(graph)
        corners=[o.matrix_world@Vector(v) for v in o.bound_box]
        box=[[min(v[i] for v in corners),max(v[i] for v in corners)] for i in range(3)]
        observed.append(dict(name=o.name,bounds_world=box,vertices=len(o.data.vertices),polygons=len(o.data.polygons)))
    center=Vector(tuple((min(v[i] for v in framing)+max(v[i] for v in framing))/2 for i in range(3)))
    extent=max(max(v[i] for v in framing)-min(v[i] for v in framing) for i in range(3))
    if not 1e-6<extent<=1e6:raise ValueError('degenerate scene extent')
    # The declared inspection lighting/cameras are derived products; authored
    # scene.blend stays unchanged. These are not nominal CAD measurements.
    for o in list(scene.objects):
        if o.type in ('CAMERA','LIGHT'):bpy.data.objects.remove(o,do_unlink=True)
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.seed=37
    scene.render.resolution_x=320;scene.render.resolution_y=240;scene.render.resolution_percentage=100;scene.render.pixel_aspect_x=1;scene.render.pixel_aspect_y=1
    if scene.world is None:scene.world=bpy.data.worlds.new('BW inspection world')
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.25,.3,1)
    for index,direction in enumerate(((2,-3,5),(-3,-1,2),(0,4,3))):
        data=bpy.data.lights.new('BW studio '+str(index),'AREA');data.energy=600*extent*extent;data.shape='DISK';data.size=extent*3
        light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=center+Vector(direction)*extent
        light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('BW inspection camera');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';data.sensor_fit='HORIZONTAL';data.clip_start=extent*.001;data.clip_end=extent*20
    views={}
    Path('/work/output').mkdir()
    for name,direction in [('top',(0,0,1)),('front',(0,-1,0)),('side',(1,0,0)),('isometric',(1,-1,1))]:
        camera.location=center+Vector(direction)*extent*4;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        rotation=camera.rotation_euler.to_quaternion()
        right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0))
        half_width=max(abs((point-center).dot(right)) for point in framing)
        half_height=max(abs((point-center).dot(up)) for point in framing)
        aspect=scene.render.resolution_x/scene.render.resolution_y
        data.ortho_scale=2*max(half_width,half_height*aspect)*1.12
        scene.render.image_settings.file_format='PNG';scene.render.filepath='/work/output/'+name+'.png';bpy.ops.render.render(write_still=True)
        views[name]=dict(position=list(camera.location),rotation=list(camera.rotation_euler),projection='orthographic',scale=data.ortho_scale,frame=12,sensor_fit=data.sensor_fit,clip_start=data.clip_start,clip_end=data.clip_end)
    scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
    scene.render.filepath='/work/output/animation.mp4';bpy.ops.render.render(animation=True)
    return dict(objects=observed,frames=[1,12,24],sampled_transforms=samples,transform_animation_observed=moving,
        cameras=views,render_profile='bw.blender-cpu-views-motion.v2',animation=dict(start=1,end=24,fps=12,frames_rendered=24),
        framing_frames=list(range(1,25)),framing_scope='evaluated mesh bounds at every rendered frame',
        blender_version=bpy.app.version_string,blender_build=bpy.app.build_hash.decode(),scope='rendered scene and sampled transforms; not CAD acceptance')

def run():
    protocol=os.dup(1);os.dup2(2,1)
    candidate_process_policy()
    mode,entry=sys.argv[sys.argv.index('--')+1:]
    result=dict(schema=1,status='FAIL',error=None,scene=None,assets={})
    try:
        if mode=='build':
            import shutil,runpy
            for root,dirs,files in os.walk('/inputs'):
                dirs[:]=[d for d in dirs if root!='/inputs' or d!='policy']
                for name in files:
                    relative=os.path.relpath(os.path.join(root,name),'/inputs')
                    if relative=='scene.blend':continue
                    target=Path('/work')/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(os.path.join(root,name),target)
            sys.path.insert(0,'/work');runpy.run_path('/work/'+entry,run_name='__main__')
            path=Path('/work/scene.blend')
            if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=32*1024*1024:raise ValueError('fresh bounded scene.blend export required')
            result['assets']['scene.blend']=base64.b64encode(path.read_bytes()).decode()
        elif mode=='inspect':
            result['scene']=inspect()
            for path in Path('/work/output').iterdir():result['assets'][path.name]=base64.b64encode(path.read_bytes()).decode()
        else:raise ValueError('unregistered Blender worker mode')
        result['status']='PASS'
    except BaseException as exc:result['error']=type(exc).__name__+': '+str(exc)[:3000]
    with os.fdopen(protocol,'w') as response:response.write(json.dumps(result,separators=(',',':'))+'\n')
if __name__=='__main__':run()
