"""
foam_partition.py
=================
แบ่งโมเดล 3D ออกเป็นชิ้นส่วนตามก้อนโฟม (Smart Foam Partitioning) จากรูปทรงจริงของไฟล์

แทนที่หน้า "วิเคราะห์แบ่งก้อนโฟมอัตโนมัติ" เดิมที่:
  - สุ่มขนาดชิ้นส่วนด้วย np.random ทุกครั้งที่หน้ารีเฟรช (ตัวเลขเปลี่ยนไปมา ไม่ได้มาจากโมเดล)
  - เรียก create_foam_grid_visualizer() โดยไม่ส่ง x_mm (error ทุกครั้ง)
  - แนะนำจำนวนชิ้นจากตัวเลือก "ความซับซ้อน" ที่ผู้ใช้เลือกเอง ไม่ได้วัดจากโมเดล

วิธีทำงาน (ส่วนคำนวณใช้แค่ numpy/scipy ไม่ผูกกับ trimesh):
  1) แต่ละหน้า (face) ของโมเดลถูกกำหนดให้อยู่ชิ้นส่วนใดชิ้นส่วนหนึ่ง
  2) ก้อนโฟมของแต่ละชิ้น = กล่องครอบ (bounding box) ของหน้าที่อยู่ในชิ้นนั้น (+ ระยะเผื่อ)
  3) โหมดแบ่ง: auto (ผ่ากลางตามแกนที่เกินขนาดแผ่นโฟมจนพอดี) / ตามชั้นความสูง /
     ตามชิ้นส่วนที่แยกอยู่ในไฟล์ (connected components)

หมายเหตุ: ปริมาตรที่แสดงเป็นปริมาตรกล่องครอบ ไม่ใช่ "ปริมาณวัตถุดิบโฟมที่ต้องใช้" ในหน้าประเมินราคา
(อันนั้นคำนวณจากพื้นที่ผิว) ใช้วางแผนการตัด/จัดวางเท่านั้น ไม่เกี่ยวกับราคา
"""

import hashlib
import math

import numpy as np

FOAM_BLOCK_W_MM = 600.0
FOAM_BLOCK_L_MM = 1200.0
MAX_PARTS_HARD = 64
MAX_PARTITION_FACES = 1_500_000   # เกินนี้ไม่คำนวณ (กิน RAM บน Streamlit Cloud)
MAX_DISPLAY_FACES = 150_000       # เกินนี้แสดงเฉพาะก้อนโฟม ไม่วาดตัวโมเดล
MAX_COMPONENTS = 20_000           # ไฟล์ที่แตกเป็นชิ้นเล็กมากกว่านี้ถือว่าไม่น่าเชื่อถือ

_COLORS = [
    "#2E9E5B", "#E8833A", "#E3B93C", "#3FA34D", "#3B82F6", "#8B5CF6",
    "#EC4899", "#14B8A6", "#EF4444", "#6366F1", "#84CC16", "#F59E0B",
]


# ==========================================================================
# ส่วนคำนวณ (pure numpy)
# ==========================================================================
def fits_block(dims_mm, max_dims_mm, tol_mm=1.0):
    """กล่องขนาด dims ใส่ในแผ่นโฟม max_dims ได้ไหม (หมุนได้ จึงเทียบแบบเรียงลำดับ)"""
    d = sorted(float(x) for x in dims_mm)
    m = sorted(float(x) for x in max_dims_mm)
    return all(a <= b + tol_mm for a, b in zip(d, m))


def _face_stats(vertices, faces):
    tri = np.asarray(vertices, dtype=np.float32)[np.asarray(faces)]
    return tri.min(axis=1), tri.max(axis=1), tri.mean(axis=1)


def _make_group(idx, tmin, tmax):
    return {
        "idx": idx,
        "lo": tmin[idx].min(axis=0).astype(float),
        "hi": tmax[idx].max(axis=0).astype(float),
    }


def _pick_axis(dims, max_dims_mm, need_fit):
    """เลือกแกนที่จะผ่า: ถ้าต้องการให้พอดีแผ่นโฟม ผ่าแกนที่เกินขีดจำกัดมากสุด"""
    if not need_fit:
        return int(np.argmax(dims))
    order = np.argsort(-np.asarray(dims))            # แกนที่ยาวสุดก่อน
    limits = sorted((float(x) for x in max_dims_mm), reverse=True)
    ratios = {int(ax): float(dims[ax]) / max(limits[rank], 1e-6) for rank, ax in enumerate(order)}
    return max(ratios, key=ratios.get)


def split_auto(tmin, tmax, centers, max_dims_mm, target_parts, stop_when_fit=False):
    """
    ผ่ากลุ่มที่ "ใหญ่และยังไม่พอดีแผ่นโฟม" ก่อนเสมอ จนครบ target_parts
    stop_when_fit=True -> หยุดทันทีที่ทุกชิ้นพอดีแผ่นโฟม (ใช้หาจำนวนชิ้นขั้นต่ำที่แนะนำ)
    """
    target_parts = int(max(1, min(target_parts, MAX_PARTS_HARD)))
    groups = [_make_group(np.arange(len(centers)), tmin, tmax)]
    guard = 0
    while len(groups) < target_parts and guard < 5000:
        guard += 1
        cand = []
        for gi, g in enumerate(groups):
            if len(g["idx"]) < 2:
                continue
            dims = g["hi"] - g["lo"]
            nonfit = not fits_block(dims, max_dims_mm)
            cand.append((nonfit, float(np.prod(np.maximum(dims, 1e-6))), gi))
        if not cand:
            break
        if stop_when_fit and not any(c[0] for c in cand):
            break
        nonfit, _, gi = max(cand)
        g = groups.pop(gi)
        axis = _pick_axis(g["hi"] - g["lo"], max_dims_mm, nonfit)
        mid = (g["lo"][axis] + g["hi"][axis]) / 2.0
        c = centers[g["idx"], axis]
        left, right = g["idx"][c < mid], g["idx"][c >= mid]
        if len(left) == 0 or len(right) == 0:                      # ผ่ากลางไม่ได้ ใช้ค่ากลางของข้อมูลแทน
            order = np.argsort(c, kind="stable")
            half = len(order) // 2
            left, right = g["idx"][order[:half]], g["idx"][order[half:]]
        groups.append(_make_group(left, tmin, tmax))
        groups.append(_make_group(right, tmin, tmax))
    return groups


def split_layers(tmin, tmax, centers, seg_mm):
    """แบ่งเป็นชั้นความสูงเท่ากัน ชั้นละไม่เกิน seg_mm"""
    zmin, zmax = float(tmin[:, 2].min()), float(tmax[:, 2].max())
    height = max(zmax - zmin, 1e-6)
    n = int(max(1, min(math.ceil(height / max(seg_mm, 1.0)), MAX_PARTS_HARD)))
    seg = height / n
    lab = np.clip(((centers[:, 2] - zmin) / seg).astype(int), 0, n - 1)
    groups = []
    for k in range(n):
        idx = np.nonzero(lab == k)[0]
        if len(idx) == 0:
            continue
        g = _make_group(idx, tmin, tmax)
        g["lo"][2] = max(g["lo"][2], zmin + k * seg)               # ตัดขอบชั้นให้ตรงระนาบที่จะผ่าจริง
        g["hi"][2] = min(g["hi"][2], zmin + (k + 1) * seg)
        if g["hi"][2] <= g["lo"][2]:
            g["lo"][2], g["hi"][2] = zmin + k * seg, zmin + (k + 1) * seg
        groups.append(g)
    return groups


def split_components(faces, n_vertices, tmin, tmax):
    """แยกตามชิ้นส่วนที่ไม่ติดกันในไฟล์ (ใช้จุดยอดร่วม) คืน (groups, จำนวนชิ้นจริง) หรือ (None, จำนวน)"""
    try:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
    except ImportError:                                             # ไม่มี scipy บนเซิร์ฟเวอร์
        return None, -1

    f = np.asarray(faces)
    rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    graph = coo_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(n_vertices, n_vertices))
    ncomp, vlab = connected_components(graph, directed=False)
    if ncomp > MAX_COMPONENTS:
        return None, int(ncomp)
    flab = vlab[f[:, 0]]
    counts = np.bincount(flab, minlength=ncomp)
    order = np.argsort(-counts)
    keep = order[: MAX_PARTS_HARD - 1] if ncomp > MAX_PARTS_HARD else order
    groups = [_make_group(np.nonzero(flab == c)[0], tmin, tmax) for c in keep]
    if ncomp > MAX_PARTS_HARD:                                      # ชิ้นเล็กที่เหลือรวมเป็นกลุ่มเดียว
        kept = np.zeros(ncomp, dtype=bool)
        kept[keep] = True
        rest = np.nonzero(~kept[flab])[0]
        if len(rest):
            groups.append(_make_group(rest, tmin, tmax))
    return groups, int(ncomp)


def build_parts(vertices, faces, method, foam_h_mm, target_parts=None, margin_mm=0.0):
    """
    method: "auto" | "layers" | "components"
    คืน dict: parts, recommended, note, bbox_lo, bbox_hi
    """
    max_dims = (FOAM_BLOCK_W_MM, FOAM_BLOCK_L_MM, float(foam_h_mm))
    tmin, tmax, centers = _face_stats(vertices, faces)
    note, recommended = None, None

    if method == "layers":
        groups = split_layers(tmin, tmax, centers, foam_h_mm)
        recommended = len(groups)
    elif method == "components":
        groups, ncomp = split_components(faces, len(vertices), tmin, tmax)
        if groups is None:
            note = ("ยังไม่ได้ติดตั้ง scipy (เพิ่ม scipy ใน requirements.txt) จึงใช้ 'แบ่งอัตโนมัติ' แทน"
                    if ncomp < 0 else
                    f"ไฟล์แตกเป็น {ncomp:,} ชิ้นเล็กๆ (มากเกินไป) จึงไม่ใช้โหมดนี้ — ใช้ 'แบ่งอัตโนมัติ' แทน")
            groups = split_auto(tmin, tmax, centers, max_dims, 1, stop_when_fit=True)
            recommended = len(groups)
        else:
            recommended = ncomp
            if ncomp > MAX_PARTS_HARD:
                note = f"ไฟล์มี {ncomp} ชิ้นส่วน แสดง {MAX_PARTS_HARD - 1} ชิ้นใหญ่สุด ที่เหลือรวมเป็น 1 กลุ่ม"
    else:
        recommended = len(split_auto(tmin, tmax, centers, max_dims, MAX_PARTS_HARD, stop_when_fit=True))
        want = recommended if target_parts is None else target_parts
        groups = split_auto(tmin, tmax, centers, max_dims, want, stop_when_fit=False)

    parts = []
    for g in groups:
        lo, hi = g["lo"] - margin_mm, g["hi"] + margin_mm
        parts.append({
            "idx": g["idx"], "lo": lo, "hi": hi,
            "center": (lo + hi) / 2.0, "dims_mm": hi - lo,
            "fits": fits_block(hi - lo, max_dims),
        })
    parts.sort(key=lambda p: (round(float(p["center"][2]), 1), round(float(p["center"][1]), 1), float(p["center"][0])))
    for n, p in enumerate(parts, start=1):
        p["name"] = f"ชิ้นส่วน #{n}"

    return {
        "parts": parts, "recommended": int(recommended), "note": note,
        "bbox_lo": np.min([p["lo"] for p in parts], axis=0),
        "bbox_hi": np.max([p["hi"] for p in parts], axis=0),
    }


def summarize_blocks(block_dims_mm, bbox_dims_mm):
    """ปริมาตรรวมของก้อนโฟมทุกชิ้น เทียบกับการตัดจากก้อนใหญ่ก้อนเดียวที่ครอบทั้งโมเดล (หน่วย cm³)"""
    total = sum(w * l * h for w, l, h in block_dims_mm) / 1000.0
    single = float(np.prod(bbox_dims_mm)) / 1000.0
    saving_pct = (1.0 - total / single) * 100.0 if single > 0 else 0.0
    return {"total_cm3": total, "single_cm3": single, "saving_pct": saving_pct}


# ==========================================================================
# ภาพ 3D (Plotly)
# ==========================================================================
_BOX_I = [0, 0, 4, 4, 0, 0, 3, 3, 0, 0, 1, 1]
_BOX_J = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 2, 6]
_BOX_K = [2, 3, 6, 7, 5, 4, 6, 7, 7, 4, 6, 5]
_BOX_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]


def _box_corners(c, dims):
    lo, hi = c - dims / 2.0, c + dims / 2.0
    return np.array([
        [lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
        [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]],
    ])


def build_partition_figure(vertices, faces, parts, block_dims_mm, explode_pct=0.0,
                           show_mesh=True, show_blocks=True, highlight=None, height=640):
    import plotly.graph_objects as go

    verts = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces)
    model_center = (np.min([p["lo"] for p in parts], axis=0) + np.max([p["hi"] for p in parts], axis=0)) / 2.0
    k = float(explode_pct) / 100.0
    fig = go.Figure()

    for i, p in enumerate(parts):
        color = _COLORS[i % len(_COLORS)]
        dimmed = highlight is not None and highlight != i
        offset = (p["center"] - model_center) * k
        dims = np.asarray(block_dims_mm[i], dtype=float)
        hover = (f"{p['name']}<br>{dims[0] / 10:.1f} × {dims[1] / 10:.1f} × {dims[2] / 10:.1f} cm"
                 f"<br>{dims[0] * dims[1] * dims[2] / 1000:,.0f} cm³")
        legend_used = False

        if show_mesh:
            uniq, inv = np.unique(faces[p["idx"]].ravel(), return_inverse=True)
            v, tri = verts[uniq] + offset, inv.reshape(-1, 3)
            fig.add_trace(go.Mesh3d(
                x=v[:, 0], y=v[:, 1], z=v[:, 2], i=tri[:, 0], j=tri[:, 1], k=tri[:, 2],
                color=color, opacity=0.12 if dimmed else 1.0, flatshading=True,
                name=p["name"], legendgroup=p["name"], showlegend=True, hoverinfo="skip",
            ))
            legend_used = True

        if show_blocks:
            corners = _box_corners(p["center"] + offset, dims)
            fig.add_trace(go.Mesh3d(
                x=corners[:, 0], y=corners[:, 1], z=corners[:, 2], i=_BOX_I, j=_BOX_J, k=_BOX_K,
                color=color, opacity=0.04 if dimmed else 0.16, name=p["name"], legendgroup=p["name"],
                showlegend=not legend_used, hovertext=hover, hoverinfo="text",
            ))
            ex, ey, ez = [], [], []
            for a, b in _BOX_EDGES:
                ex += [corners[a, 0], corners[b, 0], None]
                ey += [corners[a, 1], corners[b, 1], None]
                ez += [corners[a, 2], corners[b, 2], None]
            fig.add_trace(go.Scatter3d(
                x=ex, y=ey, z=ez, mode="lines", line=dict(color=color, width=2 if dimmed else 4),
                legendgroup=p["name"], showlegend=False, hoverinfo="skip",
            ))

    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=10, b=0),
        scene=dict(aspectmode="data", xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)"),
        legend=dict(itemsizing="constant"),
    )
    return fig


# ==========================================================================
# หน้า Streamlit
# ==========================================================================
def _model_signature(vertices):
    v = np.asarray(vertices)
    raw = repr((len(v), tuple(np.round(v.min(axis=0), 1)), tuple(np.round(v.max(axis=0), 1))))
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def render_smart_partition_page(lang="TH", title=None, subtitle=None):
    import pandas as pd
    import streamlit as st

    tr = (lambda th, en: th) if lang == "TH" else (lambda th, en: en)

    if title:
        st.subheader(title)
    if subtitle:
        st.caption(subtitle)

    mesh = st.session_state.get("mesh")
    faces = getattr(mesh, "faces", None)
    verts = getattr(mesh, "vertices", None)
    if mesh is None or faces is None or verts is None or len(faces) == 0:
        st.warning(tr("⚠️ ยังไม่พบไฟล์โมเดล 3D (ที่มีพื้นผิว) กรุณาอัปโหลดที่หน้าแรกก่อนใช้งานครับ",
                      "⚠️ No 3D model with surfaces found. Please upload one on the first page."))
        return
    verts, faces = np.asarray(verts), np.asarray(faces)
    if len(faces) > MAX_PARTITION_FACES:
        st.error(tr(f"⚠️ โมเดลละเอียดเกินไป ({len(faces):,} หน้า) กรุณาลดจำนวนโพลีกอนก่อนอัปโหลด (ไม่เกิน {MAX_PARTITION_FACES:,})",
                    f"⚠️ Model too detailed ({len(faces):,} faces). Please decimate it first (max {MAX_PARTITION_FACES:,})."))
        return

    ext = verts.max(axis=0) - verts.min(axis=0)
    st.info(tr(
        f"📦 **Bounding Box ของโมเดล (จากหน้าแรก):** กว้าง X **{ext[0] / 10:.1f}** | ยาว Y **{ext[1] / 10:.1f}** | สูง Z **{ext[2] / 10:.1f}** ซม.",
        f"📦 **Model bounding box:** X **{ext[0] / 10:.1f}** | Y **{ext[1] / 10:.1f}** | Z **{ext[2] / 10:.1f}** cm"))

    # ---- ตั้งค่า ----
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric(tr("กว้างแผ่นโฟมมาตรฐาน", "Standard foam width"), f"{FOAM_BLOCK_W_MM / 10:.0f} cm")
    c2.metric(tr("ยาวแผ่นโฟมมาตรฐาน", "Standard foam length"), f"{FOAM_BLOCK_L_MM / 10:.0f} cm")
    foam_h_m = c3.slider(tr("ความสูงแผ่นโฟม (เมตร)", "Foam height (m)"), 1.0, 3.0, 1.8, 0.1, key="smart_foam_h_m")
    foam_h_mm = foam_h_m * 1000.0

    m1, m2 = st.columns([2, 1])
    method_labels = {
        "auto": tr("แบ่งอัตโนมัติให้พอดีแผ่นโฟม", "Auto-split to fit foam blocks"),
        "layers": tr("แบ่งตามชั้นความสูง", "Split by height layers"),
        "components": tr("แบ่งตามชิ้นส่วนที่แยกอยู่ในไฟล์", "Split by separate pieces in the file"),
    }
    method = m1.selectbox(tr("วิธีแบ่งชิ้นส่วน", "Split method"), list(method_labels), format_func=method_labels.get, key="smart_method")
    margin_mm = m2.number_input(tr("ระยะเผื่อต่อด้าน (มม.)", "Margin per side (mm)"), 0.0, 200.0, 0.0, 5.0, key="smart_margin")

    msig = _model_signature(verts)
    cache = st.session_state.setdefault("_smart_part_cache", {})

    def _parts_for(target):
        key = (msig, len(faces), method, round(foam_h_mm), round(margin_mm), target)
        if key not in cache:
            if len(cache) > 12:
                cache.clear()
            with st.spinner(tr("กำลังแบ่งชิ้นส่วน...", "Splitting...")):
                cache[key] = build_parts(verts, faces, method, foam_h_mm, target, margin_mm)
        return cache[key]

    base = _parts_for(None)                       # ค่าแนะนำ (จำนวนขั้นต่ำที่พอดีแผ่นโฟม)
    rec = base["recommended"]
    if base["note"]:
        st.warning(base["note"])

    if method == "auto":
        st.info(tr(f"💡 **ผลวิเคราะห์จากรูปทรงจริง:** ต้องแบ่งอย่างน้อย **{rec} ชิ้น** จึงพอดีแผ่นโฟม {FOAM_BLOCK_W_MM / 10:.0f}×{FOAM_BLOCK_L_MM / 10:.0f}×{foam_h_mm / 10:.0f} ซม.",
                   f"💡 **Shape analysis:** at least **{rec} parts** are needed to fit {FOAM_BLOCK_W_MM / 10:.0f}×{FOAM_BLOCK_L_MM / 10:.0f}×{foam_h_mm / 10:.0f} cm foam."))
        target = st.slider(tr("จำนวนชิ้นส่วนที่ต้องการ (เพิ่มได้ถ้าอยากแบ่งให้เล็กลง)", "Number of parts"),
                           1, MAX_PARTS_HARD, int(min(max(rec, 1), MAX_PARTS_HARD)), key=f"smart_target_{msig}_{round(foam_h_mm)}")
        result = _parts_for(int(target))
    else:
        st.info(tr(f"💡 แบ่งได้ **{rec} ชิ้น** ตามวิธีที่เลือก", f"💡 **{rec} parts** with the selected method"))
        result = base

    parts = result["parts"]
    max_dims = (FOAM_BLOCK_W_MM, FOAM_BLOCK_L_MM, foam_h_mm)

    # ---- ตารางขนาดก้อนโฟม (แก้ไขได้) ----
    st.markdown("---")
    st.subheader(tr("📋 ขนาดก้อนโฟมแต่ละชิ้นส่วน (แก้ไขได้)", "📋 Foam block size per part (editable)"))
    col_x, col_y, col_z = tr("กว้าง X (cm)", "W X (cm)"), tr("ยาว Y (cm)", "L Y (cm)"), tr("สูง Z (cm)", "H Z (cm)")
    col_name = tr("ชิ้นส่วน", "Part")
    df0 = pd.DataFrame({
        col_name: [p["name"] for p in parts],
        col_x: [round(float(p["dims_mm"][0]) / 10, 1) for p in parts],
        col_y: [round(float(p["dims_mm"][1]) / 10, 1) for p in parts],
        col_z: [round(float(p["dims_mm"][2]) / 10, 1) for p in parts],
    })
    num_cfg = st.column_config.NumberColumn(min_value=1.0, step=0.5, format="%.1f")
    tbl_key = f"smart_tbl_{msig}_{method}_{round(foam_h_mm)}_{round(margin_mm)}_{len(parts)}"
    df = st.data_editor(df0, key=tbl_key, hide_index=True, width="stretch", disabled=[col_name],
                        column_config={col_x: num_cfg, col_y: num_cfg, col_z: num_cfg})

    block_dims_mm = []
    for i, p in enumerate(parts):
        row = []
        for col, ax in ((col_x, 0), (col_y, 1), (col_z, 2)):
            val = df[col].iloc[i] if i < len(df) else None
            row.append(float(val) * 10.0 if val is not None and not pd.isna(val) and val > 0 else float(p["dims_mm"][ax]))
        block_dims_mm.append(row)

    fit_flags = [fits_block(d, max_dims) for d in block_dims_mm]
    vol = [w * l * h / 1000.0 for w, l, h in block_dims_mm]
    st.dataframe(pd.DataFrame({
        col_name: [p["name"] for p in parts],
        tr("ปริมาตรก้อน (cm³)", "Block volume (cm³)"): [round(v, 1) for v in vol],
        tr("สถานะ", "Status"): [tr("✅ พอดีแผ่นโฟม", "✅ Fits") if ok else tr("⚠️ เกินขนาดแผ่นโฟม", "⚠️ Too large") for ok in fit_flags],
    }), hide_index=True, width="stretch")
    if not all(fit_flags):
        st.warning(tr(f"⚠️ มี {fit_flags.count(False)} ชิ้นที่ใหญ่เกินแผ่นโฟมมาตรฐาน — เพิ่มจำนวนชิ้นส่วน หรือเพิ่มความสูงแผ่นโฟม",
                      f"⚠️ {fit_flags.count(False)} part(s) exceed the standard foam block — add parts or raise the foam height."))

    summary = summarize_blocks(block_dims_mm, result["bbox_hi"] - result["bbox_lo"])
    s1, s2, s3, s4 = st.columns(4)
    s1.metric(tr("จำนวนชิ้นส่วน", "Parts"), f"{len(parts)}")
    s2.metric(tr("ปริมาตรก้อนโฟมรวม", "Total block volume"), f"{summary['total_cm3']:,.0f} cm³")
    s3.metric(tr("ก้อนใหญ่ก้อนเดียว", "Single big block"), f"{summary['single_cm3']:,.0f} cm³")
    s4.metric(tr("ปริมาตรที่ลดได้", "Volume saved"), f"{summary['saving_pct']:.1f}%")
    st.caption(tr("ℹ️ ตัวเลขนี้คือปริมาตรกล่องครอบแต่ละชิ้นเพื่อวางแผนการตัด ไม่ใช่ปริมาณโฟมที่สั่งซื้อ (ดูหน้า 'ประเมินราคา')",
                  "ℹ️ These are bounding-box volumes for cut planning, not the foam quantity to order (see the cost page)."))

    # ---- ภาพ 3 มิติ ----
    st.markdown("---")
    st.subheader(tr("🧊 ภาพจำลองการแบ่งก้อนโฟมจากโมเดลจริง", "🧊 3D partition view of the real model"))
    too_heavy = len(faces) > MAX_DISPLAY_FACES
    modes = {
        "both": tr("หุ่น + ก้อนโฟม", "Model + foam"),
        "model": tr("เฉพาะหุ่น", "Model only"),
        "foam": tr("เฉพาะก้อนโฟม", "Foam only"),
    }
    v1, v2, v3 = st.columns([1.2, 2, 1.2])
    view_mode = v1.selectbox(tr("แสดงผล", "Display"), list(modes), format_func=modes.get, key="smart_view_mode")
    explode = v2.slider(tr("ระยะแยกชิ้นส่วน (0% = ประกอบรวม)", "Explode distance (0% = assembled)"), 0, 100, 0, key="smart_explode")
    names = [tr("ทั้งหมด", "All")] + [p["name"] for p in parts]
    pick = v3.selectbox(tr("เน้นชิ้นส่วน", "Highlight"), names, key=f"smart_hl_{len(parts)}")
    highlight = None if pick == names[0] else names.index(pick) - 1

    show_mesh = view_mode in ("both", "model") and not too_heavy
    show_blocks = view_mode in ("both", "foam") or too_heavy
    if too_heavy and view_mode != "foam":
        st.info(tr(f"โมเดลละเอียดมาก ({len(faces):,} หน้า) จึงแสดงเฉพาะก้อนโฟมเพื่อไม่ให้หน้าเว็บค้าง",
                   f"Model is very detailed ({len(faces):,} faces); only foam blocks are drawn to keep the page responsive."))

    fig = build_partition_figure(verts, faces, parts, block_dims_mm, explode, show_mesh, show_blocks, highlight)
    st.plotly_chart(fig, width="stretch", key="smart_partition_chart")
