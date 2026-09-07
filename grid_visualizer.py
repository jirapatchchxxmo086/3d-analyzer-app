import plotly.graph_objects as go
import numpy as np
import trimesh
import math
import streamlit as st

def get_submeshes(mesh):
    """
    แยกชิ้นส่วนของโมเดล (Connected Components) 
    หากเป็นโมเดลชิ้นเดียว จะส่งคืน list ที่มีชิ้นเดิม
    """
    if mesh is None or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        return []
    
    submeshes = mesh.split(only_watertight=False)
    if not submeshes:
        submeshes = [mesh]
        
    # จัดเรียงตามปริมาตร/ขนาด จากใหญ่ไปเล็ก
    submeshes.sort(key=lambda m: m.extents.prod(), reverse=True)
    return submeshes

def create_foam_grid_visualizer(x_mm, y_mm, z_mm, max_segment_mm=1000.0, wall_thickness_mm=75.0, mesh=None):
    """
    สร้าง Plotly Figure จำลองการจัดวางก้อนโฟมดิบแบบ Exploded Grid Layout
    - ลบ Slice Plane Z และ Wireframe Box รวมออก
    - แยก Bounding Box ก้อนโฟมตามชิ้นส่วนแบบโปร่งแสง
    - กระจายแต่ละชิ้นส่วนในรูปแบบ Grid ไม่ให้ทับซ้อนกัน
    """
    fig = go.Figure()
    
    # 1. ดึงชิ้นส่วนโมเดลย่อย (Submeshes)
    submeshes = get_submeshes(mesh)
    
    # บันทึกจำนวนชิ้นส่วนลง session_state สำหรับประเมินยุทธศาสตร์
    st.session_state["submesh_count"] = len(submeshes)
    
    if submeshes:
        n_items = len(submeshes)
        cols = math.ceil(math.sqrt(n_items))
        
        # คำนวณระยะ Spacing ระหว่าง Grid โดยอิงจากขนาดชิ้นส่วนสูงสุด
        max_extent = max([m.extents.max() for m in submeshes])
        spacing = max_extent * 1.5 if max_extent > 0 else 1000.0
        
        for idx, submesh in enumerate(submeshes):
            row_idx = idx // cols
            col_idx = idx % cols
            
            # ระยะ Shift สำหรับทำ Exploded Grid View
            shift_x = col_idx * spacing
            shift_y = row_idx * spacing
            
            # ย้ายจุดศูนย์กลางของ submesh มาที่ origin ชั่วคราว แล้ววางตาม Grid
            bounds = submesh.bounds
            min_corner = bounds[0]
            max_corner = bounds[1]
            center = (min_corner + max_corner) / 2.0
            
            # โพสิชัน Vertices ใหม่
            vertices = submesh.vertices - center
            vertices[:, 0] += shift_x
            vertices[:, 1] += shift_y
            vertices[:, 2] += (max_corner[2] - min_corner[2]) / 2.0  # ให้ฐานตั้งระดับใกล้เคียงกัน
            
            faces = submesh.faces
            
            # --- 1.1 วาดโมเดล 3D จริง (สีน้ำเงินเข้ม) ---
            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                color='#1E3A8A', # Navy Blue
                opacity=0.95,
                name=f"ชิ้นส่วนที่ {idx + 1}",
                showlegend=True,
                flatshading=True,
                lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.3)
            ))
            
            # --- 1.2 วาด Bounding Box (ก้อนโฟมดิบโปร่งแสง) แยกรายชิ้นส่วน ---
            sub_ext = submesh.extents
            sx, sy, sz = sub_ext[0], sub_ext[1], sub_ext[2]
            
            # Bounding Box Coordinates (Centered at shift_x, shift_y)
            bx0, bx1 = shift_x - sx/2.0, shift_x + sx/2.0
            by0, by1 = shift_y - sy/2.0, shift_y + sy/2.0
            bz0, bz1 = 0, sz
            
            # 8 มุมของก้อนโฟม
            box_verts = np.array([
                [bx0, by0, bz0], [bx1, by0, bz0], [bx1, by1, bz0], [bx0, by1, bz0],
                [bx0, by0, bz1], [bx1, by0, bz1], [bx1, by1, bz1], [bx0, by1, bz1]
            ])
            
            # Faces ของ Bounding Box (12 Triangles)
            box_i = [0, 0, 4, 4, 0, 0, 1, 1, 0, 0, 3, 3]
            box_j = [1, 2, 5, 6, 3, 7, 2, 6, 4, 5, 7, 6]
            box_k = [2, 3, 6, 7, 7, 4, 6, 5, 5, 1, 6, 2]
            
            fig.add_trace(go.Mesh3d(
                x=box_verts[:, 0],
                y=box_verts[:, 1],
                z=box_verts[:, 2],
                i=box_i, j=box_j, k=box_k,
                color='#38BDF8', # Sky Blue Transparent
                opacity=0.22,
                name=f"ก้อนโฟมดิบ (ชิ้น {idx + 1})",
                showlegend=True,
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
                    line=dict(color='#0284C7', width=3),
                    showlegend=False,
                    hoverinfo='skip'
                ))

    else:
        # Fallback กรณีไม่มี Mesh (ใช้วาดก้อนโฟมเดี่ยวธรรมดา)
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
            color='#38BDF8', opacity=0.25, name="ก้อนโฟมดิบรวม"
        ))

    # --- 2. ตั้งค่า Layout การแสดงผลแบบ 3D Studio Style ---
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            yaxis=dict(title='Y (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            zaxis=dict(title='Z (mm)', backgroundcolor='#FAF8F5', gridcolor='#E2D9CE', showbackground=True),
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.6, y=1.6, z=1.2)
            )
        ),
        margin=dict(l=10, r=10, b=10, t=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            yanchor="top", y=0.98,
            xanchor="left", x=0.02,
            bgcolor="rgba(255, 255, 255, 0.7)"
        )
    )

    return fig
