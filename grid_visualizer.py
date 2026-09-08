import plotly.graph_objects as go
import numpy as np
import trimesh
import math
import streamlit as st

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

def create_foam_grid_visualizer(x_mm, y_mm, z_mm, max_segment_mm=1000.0, wall_thickness_mm=75.0, mesh=None, slice_mode="modular"):
    fig = go.Figure()

    # ==========================================
    # โหมดที่ 1: การกัดแบบระนาบ (Planar Split)
    # ==========================================
    if slice_mode == "planar":
        if mesh is not None:
            vertices = mesh.vertices.copy()
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2.0
            
            # จัดตำแหน่งโมเดลให้อยู่ตรงกลาง Origin บนระดับ Z=0
            vertices[:, 0] -= center[0]
            vertices[:, 1] -= center[1]
            vertices[:, 2] -= bounds[0][2]
            
            # 1. วาดตัวโมเดลหลัก
            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                i=mesh.faces[:, 0], j=mesh.faces[:, 1], k=mesh.faces[:, 2],
                color='#1E3A8A', opacity=0.9, name='โมเดลหลัก', showlegend=False
            ))
            
            # 2. วาด Bounding Box รวมก้อนใหญ่
            min_b, max_b = vertices.min(axis=0), vertices.max(axis=0)
            bx0, bx1 = min_b[0], max_b[0]
            by0, by1 = min_b[1], max_b[1]
            bz0, bz1 = 0, max_b[2]
            
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

            # 3. วาดเส้นระนาบตัด Z (Slice Planes) ตามระยะ max_segment_mm
            num_slices = math.ceil(max_b[2] / max_segment_mm) if max_segment_mm > 0 else 1
            for s in range(1, num_slices):
                z_plane = s * max_segment_mm
                if z_plane < max_b[2]:
                    fig.add_trace(go.Scatter3d(
                        x=[bx0, bx1, bx1, bx0, bx0],
                        y=[by0, by0, by1, by1, by0],
                        z=[z_plane, z_plane, z_plane, z_plane, z_plane],
                        mode='lines',
                        line=dict(color='#0284C7', width=3, dash='dash'),
                        name=f'ระนาบตัด Z={z_plane/1000:.1f}m'
                    ))

    # ==========================================
    # โหมดที่ 2: การกัดแยกชิ้นตามข้อต่อ (Modular Split)
    # ==========================================
    else:
        submeshes = get_submeshes(mesh)
        st.session_state["submesh_count"] = len(submeshes)
        
        if len(submeshes) > 0:
            n_items = len(submeshes)
            cols = math.ceil(math.sqrt(n_items))
            
            max_dx = max([m.extents[0] for m in submeshes])
            max_dy = max([m.extents[1] for m in submeshes])
            spacing_x = max_dx * 1.25 if max_dx > 0 else 500.0
            spacing_y = max_dy * 1.25 if max_dy > 0 else 500.0
            
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
                
                # วาดโมเดลย่อย
                fig.add_trace(go.Mesh3d(
                    x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                    i=submesh.faces[:, 0], j=submesh.faces[:, 1], k=submesh.faces[:, 2],
                    color='#1E3A8A', opacity=0.95, showlegend=False, flatshading=True
                ))
                
                # วาด Bounding Box แยกก้อนโฟมดิบ
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

    # ตั้งค่ากล้องและ Layout
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            yaxis=dict(title='Y (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            zaxis=dict(title='Z (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            aspectmode='data',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        ),
        margin=dict(l=0, r=0, b=0, t=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig
