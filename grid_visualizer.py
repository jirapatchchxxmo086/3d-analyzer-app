import plotly.graph_objects as go
import numpy as np
import trimesh
import math

def get_submeshes(mesh):
    if mesh is None or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        return []
    
    raw_submeshes = mesh.split(only_watertight=False)
    if isinstance(raw_submeshes, np.ndarray):
        submeshes = raw_submeshes.tolist()
    elif isinstance(raw_submeshes, (list, tuple)):
        submeshes = list(raw_submeshes)
    else:
        submeshes = []

    if len(submeshes) == 0:
        submeshes = [mesh]
        
    submeshes.sort(key=lambda m: m.extents.prod(), reverse=True)
    return submeshes

def create_foam_grid_visualizer(x_mm, y_mm, z_mm, max_segment_mm=1000.0, wall_thickness_mm=75.0, mesh=None, slice_mode="planar"):
    fig = go.Figure()

    if slice_mode == "planar":
        if mesh is not None:
            vertices = mesh.vertices.copy()
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2.0
            
            # ย้ายจุดศูนย์กลางมาที่ Center (X, Y) และวางฐานไว้ที่ Z=0
            vertices[:, 0] -= center[0]
            vertices[:, 1] -= center[1]
            vertices[:, 2] -= bounds[0][2]
            
            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                i=mesh.faces[:, 0], j=mesh.faces[:, 1], k=mesh.faces[:, 2],
                color='#1E3A8A', opacity=0.9, name='โมเดลหลัก', showlegend=False
            ))
            
            min_b, max_b = vertices.min(axis=0), vertices.max(axis=0)
            bx0, bx1 = min_b[0], max_b[0]
            by0, by1 = min_b[1], max_b[1]
            bz0, bz1 = 0, max_b[2]
        else:
            bx0, bx1 = -x_mm / 2.0, x_mm / 2.0
            by0, by1 = -y_mm / 2.0, y_mm / 2.0
            bz0, bz1 = 0, z_mm

        box_verts = np.array([
            [bx0, by0, bz0], [bx1, by0, bz0], [bx1, by1, bz0], [bx0, by1, bz0],
            [bx0, by0, bz1], [bx1, by0, bz1], [bx1, by1, bz1], [bx0, by1, bz1]
        ])
        fig.add_trace(go.Mesh3d(
            x=box_verts[:, 0], y=box_verts[:, 1], z=box_verts[:, 2],
            i=[0, 0, 4, 4, 0, 0, 1, 1, 0, 0, 3, 3],
            j=[1, 2, 5, 6, 3, 7, 2, 6, 4, 5, 7, 6],
            k=[2, 3, 6, 7, 7, 4, 6, 5, 5, 1, 6, 2],
            color='#38BDF8', opacity=0.15, showlegend=False
        ))

        total_height = bz1 - bz0
        num_slices = math.ceil(total_height / max_segment_mm) if max_segment_mm > 0 else 1
        for s in range(1, num_slices):
            z_plane = s * max_segment_mm
            if z_plane < total_height:
                fig.add_trace(go.Scatter3d(
                    x=[bx0, bx1, bx1, bx0, bx0],
                    y=[by0, by0, by1, by1, by0],
                    z=[z_plane, z_plane, z_plane, z_plane, z_plane],
                    mode='lines',
                    line=dict(color='#0284C7', width=3, dash='dash'),
                    name=f'ระนาบตัด Z={z_plane/1000:.1f}m'
                ))

    else:
        submeshes = get_submeshes(mesh)
        
        if len(submeshes) > 0:
            n_items = len(submeshes)
            cols = math.ceil(math.sqrt(n_items))
            
            max_dx = max([m.extents[0] for m in submeshes])
            max_dy = max([m.extents[1] for m in submeshes])
            spacing_x = max_dx * 1.2 spacing_x if max_dx > 0 else 500.0
            spacing_y = max_dy * 1.2 if max_dy > 0 else 500.0
            
            rows = math.ceil(n_items / cols)
            start_x = -((cols - 1) * spacing_x) / 2.0
            start_y = -((rows - 1) * spacing_y) / 2.0

            for idx, submesh in enumerate(submeshes):
                row_idx = idx // cols
                col_idx = idx % cols
                
                grid_center_x = start_x + (col_idx * spacing_x)
                grid_center_y = start_y + (row_idx * spacing_y)
                
                bounds = submesh.bounds
                local_center = (bounds[0] + bounds[1]) / 2.0
                
                vertices = submesh.vertices - local_center
                vertices[:, 0] += grid_center_x
                vertices[:, 1] += grid_center_y
                vertices[:, 2] += (bounds[1][2] - bounds[0][2]) / 2.0
                
                fig.add_trace(go.Mesh3d(
                    x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                    i=submesh.faces[:, 0], j=submesh.faces[:, 1], k=submesh.faces[:, 2],
                    color='#1E3A8A', opacity=0.95, showlegend=False, flatshading=True
                ))
                
                sx, sy, sz = submesh.extents[0], submesh.extents[1], submesh.extents[2]
                bx0, bx1 = grid_center_x - sx/2.0, grid_center_x + sx/2.0
                by0, by1 = grid_center_y - sy/2.0, grid_center_y + sy/2.0
                bz0, bz1 = 0, sz
                
                box_verts = np.array([
                    [bx0, by0, bz0], [bx1, by0, bz0], [bx1, by1, bz0], [bx0, by1, bz0],
                    [bx0, by0, bz1], [bx1, by0, bz1], [bx1, by1, bz1], [bx0, by1, bz1]
                ])
                
                fig.add_trace(go.Mesh3d(
                    x=box_verts[:, 0], y=box_verts[:, 1], z=box_verts[:, 2],
                    i=[0, 0, 4, 4, 0, 0, 1, 1, 0, 0, 3, 3],
                    j=[1, 2, 5, 6, 3, 7, 2, 6, 4, 5, 7, 6],
                    k=[2, 3, 6, 7, 7, 4, 6, 5, 5, 1, 6, 2],
                    color='#38BDF8', opacity=0.20, showlegend=False,
                    hoverinfo='text', text=f"ก้อนโฟมชิ้นที่ {idx+1}<br>ขนาด: {sx:.0f} x {sy:.0f} x {sz:.0f} mm"
                ))

    # ปรับแต่งกล้องและสัดส่วนให้ซูมเข้าพอดีชิ้นงาน และหมุนขยับได้ลื่นไหล
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            yaxis=dict(title='Y (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            zaxis=dict(title='Z (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            aspectmode='cube',  # ปรับสัดส่วนเป็นลูกบาศก์เพื่อให้ขยับและหมุนดูง่าย
            camera=dict(
                eye=dict(x=1.25, y=1.25, z=0.88),  # ขยับกล้องให้อยู่ใกล้ตัวชิ้นงานมากขึ้น
                center=dict(x=0, y=0, z=0)
            )
        ),
        margin=dict(l=0, r=0, b=0, t=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig
