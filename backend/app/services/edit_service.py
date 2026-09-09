from pathlib import Path
import subprocess, json, uuid
from app.services.video_processor import resolve_executable

QUALITY_DIMENSIONS = {'1080p': (1920, 1080), '4k': (3840, 2160), '8k': (7680, 4320)}


def long_form_dimensions(export_quality='1080p'):
    try:
        return QUALITY_DIMENSIONS[export_quality]
    except KeyError as exc:
        raise ValueError('export_quality must be 1080p, 4k, or 8k') from exc

def render_edit(video_path,spec,out_path):
    start=float(spec.get('start',0)); duration=spec.get('duration'); end=spec.get('end')
    if duration is None and end is not None: duration=max(0,float(end)-start)
    vf=[]
    export_quality=spec.get('export_quality','1080p')
    if spec.get('aspect_ratio')=='9:16':
        width,height={'1080p':(1080,1920),'4k':(2160,3840),'8k':(4320,7680)}[export_quality]
        vf.append(f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}')
    elif spec.get('aspect_ratio')=='1:1':
        size={'1080p':1080,'4k':2160,'8k':4320}[export_quality]
        vf.append(f'scale={size}:{size}:force_original_aspect_ratio=increase:flags=lanczos,crop={size}:{size}')
    elif spec.get('width') and spec.get('height'):
        vf.append(f"scale={int(spec['width'])}:{int(spec['height'])}:flags=lanczos")
    else:
        width,height=long_form_dimensions(export_quality)
        vf.append(f'scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2')
    if spec.get('brightness') is not None: vf.append(f"eq=brightness={float(spec['brightness'])}")
    cmd=[resolve_executable('ffmpeg'),'-ss',str(start),'-i',video_path]
    if duration is not None: cmd += ['-t',str(float(duration))]
    if vf: cmd += ['-vf',','.join(vf)]
    cmd += ['-c:v','libx264','-preset','veryfast','-c:a','aac','-movflags','+faststart','-y',out_path]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
    if r.returncode!=0: raise RuntimeError(r.stderr[-1500:])
    return out_path
