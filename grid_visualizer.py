from typing import Any, Optional
import numpy as np
import plotly.graph_objects as go

def create_foam_grid_visualizer(
    x_mm: float, 
    y_mm: float, 
    z_mm: float, 
    max_segment_mm: float = 1000.0,
    wall_thickness_mm: float = 75.0,
    mesh: Optional[Any] = None
) -> go.Figure:
    """
    สร้างกราฟ 3D จำลอง Bounding Box, โมเดลงานจริง และระนาบการตัดแบ่งชิ้นส่วนโฟม (Slicing Planes)
    """
    fig = go.Figure()

    # 1. แสดงตัวโมเดล 3D งานจริง (สีน้ำเงิน) ซ้อนอยู่ภายใน Bounding Box
    if mesh is not None and hasattr(mesh, "vertices") and hasattr(mesh, "faces"):
        try:
            vertices = np.asarray(mesh.vertices, dtype=float).copy()
            faces = np.asarray(mesh.faces, dtype=int)

            # จัดตำแหน่ง Mesh ให้อยู่กึ่งกลางฐาน Bounding Box (0 -> x_mm, 0 -> y_mm, 0 -> z_mm)
            min_bounds = vertices.min(axis=0)
            max_bounds = vertices.max(axis=0)
            mesh_dims = max_bounds - min_bounds

            offset_x = (x_mm - mesh_dims[0]) / 2.0 - min_bounds[0]
            offset_y = (y_mm - mesh_dims[1]) / 2.0 - min_bounds[1]
            offset_z = -min_bounds[2]  # วางชิดฐาน Z=0

            vertices[:, 0] += offset_x
            vertices[:, 1] += offset_y
            vertices[:, 2] += offset_z

            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                color='#1565C0',
                opacity=0.85,
                name='3D Model',
                hoverinfo='name'
            ))
        except Exception as e:
            print(f"Error rendering mesh: {e}")

    # 2. วาดกรอบ Bounding Box รวมของชิ้นงาน (สีส้มใส)
    fig.add_trace(go.Mesh3d(
        x=[0, x_mm, x_mm, 0, 0, x_mm, x_mm, 0],
        y=[0, 0, y_mm, y_mm, 0, 0, y_mm, y_mm],
        z=[0, 0, 0, 0, z_mm, z_mm, z_mm, z_mm],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
        j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
        k=[0, 7, 5, 3, 6, 7, 1, 1, 1, 5, 7, 7],
        opacity=0.15,
        color='#E65100',
        name='Overall Bounding Box',
        hoverinfo='text',
        text=f'ขนาดรวม: {x_mm/1000:.2f} x {y_mm/1000:.2f} x {z_mm/1000:.2f} m'
    ))

    # 3. วาดเส้นแบ่งก้อนโฟมตามระนาบ Z (ทุกๆ max_segment_mm)
    z_cuts = list(range(0, int(z_mm) + 1, int(max_segment_mm)))
    if z_cuts[-1] < int(z_mm):
        z_cuts.append(int(z_mm))

    for idx, z in enumerate(z_cuts):
        fig.add_trace(go.Scatter3d(
            x=[0, x_mm, x_mm, 0, 0],
            y=[0, 0, y_mm, y_mm, 0],
            z=[z, z, z, z, z],
            mode='lines',
            line=dict(color='#00ACC1', width=4),
            name=f'Slice Plane Z={z/1000:.1f}m',
            hoverinfo='name'
        ))

    # 4. ปรับแต่ง Layout ของกราฟ 3D
    fig.update_layout(
        title={
            'text': f"<b>ผังการตัดแบ่งบล็อกโฟม (Total Segments: {len(z_cuts)-1} ชั้นแนวสูง)</b><br><sup>ขนาดบล็อกสูงสุด: {max_segment_mm/1000:.1f} x {max_segment_mm/1000:.1f} x {max_segment_mm/1000:.1f} เมตร | ความหนาเปลือกโฟม: {wall_thickness_mm} mm</sup>",
            'x': 0.0,
            'xanchor': 'left'
        },
        scene=dict(
            xaxis=dict(title='X (mm)', backgroundcolor="rgb(245, 245, 245)"),
            yaxis=dict(title='Y (mm)', backgroundcolor="rgb(245, 245, 245)"),
            zaxis=dict(title='Z (mm)', backgroundcolor="rgb(240, 240, 240)"),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=60),
        legend=dict(x=0.7, y=0.9)
    )

    return fig
