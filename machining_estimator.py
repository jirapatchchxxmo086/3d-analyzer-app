"""
machining_estimator.py
======================

Machine-hour estimation module for:

1. Robot CNC - Foam
2. 3D Print - FDM

Version: Calibration-ready
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


# ==========================================================================
# DATA CLASS
# ==========================================================================

@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


# ==========================================================================
# MACHINE PARAMETERS
# ==========================================================================

MACHINE_PARAMS = {

    "Robot_Foam": {
        "feed_rate_mm_per_min": 5000,
        "tool_diameter_mm_range": (6, 20),
        "stepover_pct_range": (0.30, 0.75),
        "stepdown_mm_range": (10, 50),

        "working_area_mm": (
            2000,
            1200,
            1000
        ),

        "material": "Foam",
    },

    "3D_Print_FDM": {

        "nozzle_diameter_mm": 0.4,

        # ใช้ volumetric flow แทน grams/hour
        # ต้อง calibrate จากเครื่องจริงภายหลัง
        "volumetric_flow_mm3_s": 10.0,

        "filament_diameter_mm": 1.75,

        "layer_height_mm": 0.20,

        "material": (
            "PETG",
            "PLA"
        ),
    },
}


# ==========================================================================
# MATERIAL
# ==========================================================================

MATERIAL_DENSITY_G_PER_CM3 = {

    "PETG": 1.27,
    "PLA": 1.24,

}


# ==========================================================================
# ROBOT FOAM PARAMETERS
# ==========================================================================

FOAM_INTERCEPT_HR = 1.0

FOAM_SLOPE_HR_PER_SQM = 2.20


# ==========================================================================
# FDM PARAMETERS
# ==========================================================================

WALL_THICKNESS_MM = 1.2

DEFAULT_NOZZLE_MM = 0.4

DEFAULT_LAYER_HEIGHT_MM = 0.20

DEFAULT_FLOW_MM3_S = 10.0


# ==========================================================================
# UTILITY
# ==========================================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


# ==========================================================================
# ROBOT CNC FOAM
# ==========================================================================

def estimate_foam_cnc_hours(
    volume_removal_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    complexity_level: int = 3,
    setup_hours_override: Optional[float] = None,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
) -> MachiningEstimate:

    area_sqm = max(surface_area_sqm, 0.0)

    complexity_level = clamp(
        complexity_level,
        1,
        5
    )

    # ------------------------------------------------------------------
    # Complexity
    # ------------------------------------------------------------------

    complexity_factor = {
        1: 0.88,
        2: 0.94,
        3: 1.00,
        4: 1.10,
        5: 1.20,
    }[complexity_level]

    # ------------------------------------------------------------------
    # Base machine time
    # ------------------------------------------------------------------

    machine_hours_total = (
        FOAM_INTERCEPT_HR
        +
        FOAM_SLOPE_HR_PER_SQM * area_sqm
    )

    machine_hours_total *= complexity_factor

    # ------------------------------------------------------------------
    # Finishing
    # ------------------------------------------------------------------

    finishing_fraction = {

        1: 0.20,
        2: 0.25,
        3: 0.30,
        4: 0.35,
        5: 0.45,

    }[complexity_level]

    finishing_hours = (
        machine_hours_total
        * finishing_fraction
    )

    roughing_hours = (
        machine_hours_total
        - finishing_hours
    )

    # ------------------------------------------------------------------
    # Tool
    # ------------------------------------------------------------------

    finish_tool_mm = (
        6.0
        if complexity_level >= 4
        else 10.0
    )

    # ------------------------------------------------------------------
    # Programming
    # ------------------------------------------------------------------

    program_hours = max(
        0.20,
        round(0.15 * area_sqm, 2)
    )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    if setup_hours_override is not None:

        setup_hours = max(
            0.0,
            setup_hours_override
        )

    else:

        setup_hours = max(
            0.8,
            round(0.5 * area_sqm, 2)
        )

    # ------------------------------------------------------------------
    # Total
    # ------------------------------------------------------------------

    total_hours = (
        roughing_hours
        +
        finishing_hours
        +
        program_hours
        +
        setup_hours
    )

    return MachiningEstimate(

        hours=round(
            total_hours,
            2
        ),

        breakdown={

            "machine_type":
                "Robot CNC (Foam)",

            "surface_area_sqm":
                round(area_sqm, 4),

            "machine_hours_total":
                round(
                    machine_hours_total,
                    2
                ),

            "roughing_hours":
                round(
                    roughing_hours,
                    2
                ),

            "finishing_hours":
                round(
                    finishing_hours,
                    2
                ),

            "finish_tool_mm_used":
                finish_tool_mm,

            "program_hours":
                round(
                    program_hours,
                    2
                ),

            "setup_hours":
                round(
                    setup_hours,
                    2
                ),

            "billed_total_hours_excl_setup":
                round(
                    roughing_hours
                    +
                    finishing_hours
                    +
                    program_hours,
                    2
                ),

            "parts_count":
                1,

            "assembly_labor_hours":
                0.0,

            "hourly_rate_baht":
                300,

            "calibration_note":
                "Robot Foam baseline model",

        },

    )


# ==========================================================================
# FOAM BLOCK ESTIMATION
# ==========================================================================

def estimate_foam_blocks_needed(
    width_mm: float,
    length_mm: float,
    height_mm: float,

    block_w_mm: float = 600.0,
    block_l_mm: float = 1220.0,
    block_h_mm: float = 2440.0,

    hollow_shell: bool = True,

    wall_thickness_mm: float = 75.0,

    waste_factor: float = 1.15,
) -> Dict[str, Any]:

    bbox_volume_mm3 = (
        width_mm
        * length_mm
        * height_mm
    )

    if hollow_shell:

        inner_w = max(
            width_mm
            - 2 * wall_thickness_mm,
            0.0
        )

        inner_l = max(
            length_mm
            - 2 * wall_thickness_mm,
            0.0
        )

        inner_h = max(
            height_mm
            - 2 * wall_thickness_mm,
            0.0
        )

        inner_volume_mm3 = (
            inner_w
            * inner_l
            * inner_h
        )

        material_volume_mm3 = max(
            bbox_volume_mm3
            - inner_volume_mm3,
            0.0
        )

    else:

        material_volume_mm3 = bbox_volume_mm3

    block_volume_mm3 = (
        block_w_mm
        * block_l_mm
        * block_h_mm
    )

    if block_volume_mm3 > 0:

        blocks_needed_raw = (
            material_volume_mm3
            /
            block_volume_mm3
        )

    else:

        blocks_needed_raw = 0.0

    blocks_needed = math.ceil(
        blocks_needed_raw
        * waste_factor
    )

    return {

        "material_volume_cm3":
            round(
                material_volume_mm3 / 1000.0,
                1
            ),

        "block_volume_cm3":
            round(
                block_volume_mm3 / 1000.0,
                1
            ),

        "blocks_needed_raw":
            round(
                blocks_needed_raw,
                2
            ),

        "waste_factor":
            waste_factor,

        "blocks_needed":
            blocks_needed,

        "hollow_shell":
            hollow_shell,

        "wall_thickness_mm":
            wall_thickness_mm,

        "note":
            "Volumetric estimate only",

    }


# ==========================================================================
# FDM ESTIMATION
# ==========================================================================

def estimate_3d_print_hours(

    volume_cm3: float = 0.0,

    surface_area_sqm: float = 0.0,

    infill_pct: float = 15.0,

    complexity_level: int = 4,

    technology: str = "FDM",

    material: str = "PETG",

    nozzle_diameter_mm: float = DEFAULT_NOZZLE_MM,

    layer_height_mm: float = DEFAULT_LAYER_HEIGHT_MM,

    volumetric_flow_mm3_s: float = DEFAULT_FLOW_MM3_S,

    support_pct: float = 0.0,

    calibration_factor: float = 1.0,

) -> MachiningEstimate:

    # ------------------------------------------------------------------
    # Clean input
    # ------------------------------------------------------------------

    volume_cm3 = max(
        volume_cm3,
        0.0
    )

    area_sqm = max(
        surface_area_sqm,
        0.0
    )

    infill_pct = clamp(
        infill_pct,
        0.0,
        100.0
    )

    complexity_level = clamp(
        complexity_level,
        1,
        5
    )

    support_pct = clamp(
        support_pct,
        0.0,
        100.0
    )

    volumetric_flow_mm3_s = max(
        volumetric_flow_mm3_s,
        0.1
    )

    calibration_factor = max(
        calibration_factor,
        0.1
    )

    # ------------------------------------------------------------------
    # If one of volume / area is missing
    # ------------------------------------------------------------------

    if area_sqm == 0.0 and volume_cm3 > 0.0:

        approx_radius_cm = (
            (
                3.0 * volume_cm3
            )
            /
            (
                4.0 * math.pi
            )
        ) ** (
            1.0 / 3.0
        )

        area_sqm = (
            4.0
            * math.pi
            * approx_radius_cm ** 2
        ) / 10000.0

    elif volume_cm3 == 0.0 and area_sqm > 0.0:

        area_cm2 = (
            area_sqm
            * 10000.0
        )

        approx_radius_cm = math.sqrt(
            area_cm2
            /
            (
                4.0 * math.pi
            )
        )

        volume_cm3 = (
            4.0 / 3.0
        ) * math.pi * (
            approx_radius_cm ** 3
        )

    # ------------------------------------------------------------------
    # Shell volume
    # ------------------------------------------------------------------

    wall_thickness_cm = (
        WALL_THICKNESS_MM / 10.0
    )

    shell_volume_cm3 = min(

        area_sqm
        * 10000.0
        * wall_thickness_cm,

        volume_cm3

    )

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    core_volume_cm3 = max(

        volume_cm3
        - shell_volume_cm3,

        0.0

    )

    # ------------------------------------------------------------------
    # Infill
    # ------------------------------------------------------------------

    infill_fraction = (
        infill_pct / 100.0
    )

    effective_volume_cm3 = (

        shell_volume_cm3

        +

        (
            core_volume_cm3
            * infill_fraction
        )

    )

    # ------------------------------------------------------------------
    # Support
    # ------------------------------------------------------------------

    support_volume_cm3 = (

        effective_volume_cm3
        *
        support_pct
        / 100.0

    )

    total_extrusion_volume_cm3 = (

        effective_volume_cm3
        +
        support_volume_cm3

    )

    # ------------------------------------------------------------------
    # Convert cm3 -> mm3
    # ------------------------------------------------------------------

    total_extrusion_volume_mm3 = (

        total_extrusion_volume_cm3
        * 1000.0

    )

    # ------------------------------------------------------------------
    # MACHINE PRINT TIME
    # ------------------------------------------------------------------

    pure_print_seconds = (

        total_extrusion_volume_mm3
        /
        volumetric_flow_mm3_s

    )

    pure_print_hours = (
        pure_print_seconds
        / 3600.0
    )

    # ------------------------------------------------------------------
    # Complexity factor
    # ------------------------------------------------------------------

    complexity_factor = {

        1: 0.95,
        2: 0.98,
        3: 1.00,
        4: 1.05,
        5: 1.12,

    }[complexity_level]

    machine_hours = (

        pure_print_hours
        *
        complexity_factor

        *
        calibration_factor

    )

    # ------------------------------------------------------------------
    # Travel / acceleration / cooling overhead
    # ------------------------------------------------------------------

    travel_overhead = (

        machine_hours
        * 0.12

    )

    # ------------------------------------------------------------------
    # Program
    # ------------------------------------------------------------------

    program_hours = max(

        0.25,

        round(
            machine_hours * 0.05,
            2
        )

    )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    setup_hours = max(

        0.50,

        round(
            machine_hours * 0.03,
            2
        )

    )

    # ------------------------------------------------------------------
    # Total
    # ------------------------------------------------------------------

    total_time = (

        machine_hours
        +
        travel_overhead
        +
        program_hours
        +
        setup_hours

    )

    # ------------------------------------------------------------------
    # Material weight
    # ------------------------------------------------------------------

    density = MATERIAL_DENSITY_G_PER_CM3.get(

        material,

        MATERIAL_DENSITY_G_PER_CM3[
            "PETG"
        ]

    )

    weight_g = (
        total_extrusion_volume_cm3
        * density
    )

    # ------------------------------------------------------------------
    # Hour / volume
    # ------------------------------------------------------------------

    hours_per_cm3 = (

        machine_hours
        /
        effective_volume_cm3

        if effective_volume_cm3 > 0

        else 0.0

    )

    # ------------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------------

    return MachiningEstimate(

        hours=round(
            total_time,
            2
        ),

        breakdown={

            "machine_type":
                "3D Print FDM",

            "surface_area_sqm":
                round(
                    area_sqm,
                    4
                ),

            "volume_cm3":
                round(
                    volume_cm3,
                    2
                ),

            "shell_volume_cm3":
                round(
                    shell_volume_cm3,
                    2
                ),

            "core_volume_cm3":
                round(
                    core_volume_cm3,
                    2
                ),

            "infill_pct":
                infill_pct,

            "support_pct":
                support_pct,

            "material":
                material,

            "density_g_per_cm3":
                density,

            "effective_volume_cm3":
                round(
                    effective_volume_cm3,
                    2
                ),

            "support_volume_cm3":
                round(
                    support_volume_cm3,
                    2
                ),

            "total_extrusion_volume_cm3":
                round(
                    total_extrusion_volume_cm3,
                    2
                ),

            "estimated_weight_g":
                round(
                    weight_g,
                    1
                ),

            "nozzle_diameter_mm":
                nozzle_diameter_mm,

            "layer_height_mm":
                layer_height_mm,

            "volumetric_flow_mm3_s":
                volumetric_flow_mm3_s,

            "hours_per_cm3":
                round(
                    hours_per_cm3,
                    6
                ),

            "machine_hours":
                round(
                    machine_hours,
                    2
                ),

            "travel_overhead_hours":
                round(
                    travel_overhead,
                    2
                ),

            "roughing_hours":
                0.0,

            "finishing_hours":
                round(
                    machine_hours,
                    2
                ),

            "finish_tool_mm_used":
                nozzle_diameter_mm,

            "program_hours":
                round(
                    program_hours,
                    2
                ),

            "setup_hours":
                round(
                    setup_hours,
                    2
                ),

            "parts_count":
                1,

            "assembly_labor_hours":
                0.0,

            "hourly_rate_baht":
                50,

            "calibration_factor":
                calibration_factor,

            "calibration_note":
                "FDM volumetric-flow model; machine-specific calibration required",

        },

    )
