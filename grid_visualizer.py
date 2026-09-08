import plotly.graph_objects as go
import numpy as np
import trimesh
import math
import streamlit as st

def get_submeshes(mesh):
    """
    แยกชิ้นส่วนของโมเดล (Connected Components) 
    รองรับทั้งกรณีที่ trimesh.split() คืนค่าเป็น list หรือ numpy.ndarray
    """
    if mesh is None or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        return []
    
    raw_submeshes = mesh.split(only_watertight=False)
    
    # แปลงผลลัพธ์ให้อยู่ในรูปแบบ Python List เสมอเพื่อความปลอดภัย (แก้ Bug 1 & 2)
    if isinstance(raw_submeshes, np.ndarray):
        submeshes = raw_submeshes.tolist()
    elif isinstance(raw_submeshes, (list, tuple)):
        submeshes = list(raw_submeshes)
    else:
        submeshes = []

    if len(submeshes) == 0:
        submeshes = [mesh]
        
    # จัดเรียงตามปริมาตร/ขนาด จากใหญ่ไปเล็ก (ใช้งาน .sort(key=...) ได้แน่นอนแล้ว)
    submeshes.sort(key=lambda m: m.extents.prod(), reverse=True)
    return submeshes

def create_foam_grid_visualizer(x_mm, y_mm, z_mm, max_segment_mm=1000.0, wall_thickness_mm=75.0, mesh=None):
    fig = go.Figure()
    
    submeshes = get_submeshes(mesh)
    st.session_state["submesh_count"] = len(submeshes)
    
    if len(submeshes) > 0:
        n_items = len(submeshes)
        cols = math.ceil(math.sqrt(n_items))
        
        # 1. คำนวณขนาด Bounding Box ของชิ้นส่วนที่ใหญ่ที่สุด เพื่อตั้งระยะ Spacing ให้พอดี
        max_dx = max([m.extents[0] for m in submeshes])
        max_dy = max([m.extents[1] for m in submeshes])
        
        # ระยะห่างระหว่างชิ้นงาน = ขนาดชิ้นงาน + เว้นช่องว่าง 25%
        spacing_x = max_dx * 1.25 if max_dx > 0 else 500.0
        spacing_y = max_dy * 1.25 if max_dy > 0 else 500.0
        
        # คำนวณจุดศูนย์กลางรวม เพื่อ Shift ให้เซตของ Grid อยู่ตรงกลางฉากพอดี (Origin Centered)
        rows = math.ceil(n_items / cols)
        total_width_x = (cols - 1) * spacing_x
        total_width_y = (rows - 1) * spacing_y
        start_x = -total_width_x / 2.0
        start_y = -total_width_y / 2.0

        for idx, submesh in enumerate(submeshes):
            row_idx = idx // cols
            col_idx = idx % cols
            
            # ตำแหน่งศูนย์กลางของ Grid Cell นี้
            grid_center_x = start_x + (col_idx * spacing_x)
            grid_center_y = start_y + (row_idx * spacing_y)
            
            # ย้ายจุดศูนย์กลางของ submesh แต่ละชิ้นมาที่ (0,0,0) ก่อนย้ายไปตาม Grid Center
            bounds = submesh.bounds
            local_center = (bounds[0] + bounds[1]) / 2.0
            
            vertices = submesh.vertices - local_center
            vertices[:, 0] += grid_center_x
            vertices[:, 1] += grid_center_y
            vertices[:, 2] += (bounds[1][2] - bounds[0][2]) / 2.0  # วางบนระดับ Z=0
            
            faces = submesh.faces
            
            # --- 1.1 วาดโมเดล 3D จริง ---
            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                color='#1E3A8A', # Navy Blue
                opacity=0.95,
                name=f"ชิ้นส่วน {idx + 1}",
                showlegend=False, # ซ่อน Legend เพื่อไม่ให้บังพื้นที่วางกราฟ
                flatshading=True,
                lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.3)
            ))
            
            # --- 1.2 วาด Bounding Box (ก้อนโฟมดิบโปร่งแสง) แยกรายชิ้นส่วน ---
            sx, sy, sz = submesh.extents[0], submesh.extents[1], submesh.extents[2]
            
            bx0, bx1 = grid_center_x - sx/2.0, grid_center_x + sx/2.0
            by0, by1 = grid_center_y - sy/2.0, grid_center_y + sy/2.0
            bz0, bz1 = 0, sz
            
            box_verts = np.array([
                [bx0, by0, bz0], [bx1, by0, bz0], [bx1, by1, bz0], [bx0, by1, bz0],
                [bx0, by0, bz1], [bx1, by0, bz1], [bx1, by1, bz1], [bx0, by1, bz1]
            ])
            
            box_i = [0, 0, 4, 4, 0, 0, 1, 1, 0, 0, 3, 3]
            box_j = [1, 2, 5, 6, 3, 7, 2, 6, 4, 5, 7, 6]
            box_k = [2, 3, 6, 7, 7, 4, 6, 5, 5, 1, 6, 2]
            
            fig.add_trace(go.Mesh3d(
                x=box_verts[:, 0],
                y=box_verts[:, 1],
                z=box_verts[:, 2],
                i=box_i, j=box_j, k=box_k,
                color='#38BDF8',
                opacity=0.20,
                name=f"ก้อนโฟม {idx + 1}",
                showlegend=False,
                hoverinfo='text',
                text=f"ก้อนโฟมชิ้นที่ {idx+1}<br>ขนาด: {sx:.0f} x {sy:.0f} x {sz:.0f} mm"
            ))
            
            # เส้นขอบ Wireframe ของก้อนโฟมดิบ
            edges = [
                (0,1), (1,2), (2,3), (3,0),
                (4,5), (5,6), (6,7), (7,4),
                (0,4), (1,5), (2,6), (3,7)
            ]
            for edge in edges:
                fig.add_trace(go.Scatter3d(
                    x=[box_verts[edge[0]][0], box_verts[edge[1]][0]],
                    y=[box_verts[edge[0]][1], box_verts[edge[1]][1]],
                    z=[box_verts[edge[0]][2], box_verts[edge[1]][2]],
                    mode='lines',
                    line=dict(color='#0284C7', width=2),
                    showlegend=False,
                    hoverinfo='skip'
                ))

    else:
        # Fallback กรณีไม่มี Mesh
        st.session_state["submesh_count"] = 1
        bx0, bx1 = -x_mm/2.0, x_mm/2.0
        by0, by1 = -y_mm/2.0, y_mm/2.0
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
            color='#38BDF8', opacity=0.25, showlegend=False
        ))

    # --- 2. ตั้งค่า Layout การแสดงผล ---
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            yaxis=dict(title='Y (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            zaxis=dict(title='Z (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        margin=dict(l=0, r=0, b=0, t=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig
