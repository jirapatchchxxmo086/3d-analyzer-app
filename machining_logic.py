import numpy as np

class CNCController:
    def __init__(self, safe_z: float = 10.0):
        self.toolpath_planar = []
        self.toolpath_joints = {}
        self.safe_z = safe_z

    def generate_planar_toolpath(self, surface_z: float, bounds: tuple, stepover: float):
        self.toolpath_planar = []
        x_min, x_max, y_min, y_max = bounds
        
        if stepover <= 0:
            stepover = 10.0

        y_curr = y_min
        direction = 1
        
        while y_curr <= y_max:
            if direction == 1:
                self.toolpath_planar.append((x_min, y_curr, surface_z))
                self.toolpath_planar.append((x_max, y_curr, surface_z))
            else:
                self.toolpath_planar.append((x_max, y_curr, surface_z))
                self.toolpath_planar.append((x_min, y_curr, surface_z))
            
            y_curr += stepover
            direction *= -1
            
        return self.toolpath_planar

    def generate_joint_machining_toolpath(self, joint_list: list):
        self.toolpath_joints = {}
        for joint in joint_list:
            joint_id = joint.get('id', 'joint')
            center_x, center_y = joint.get('center', (0, 0))
            radius = joint.get('radius', 10.0)
            depth = joint.get('depth', 5.0)
            
            joint_path = []
            if depth <= 0:
                continue

            for z in np.arange(0.5, depth + 0.5, 0.5):
                angles = np.linspace(0, 2 * np.pi, 36)
                for theta in angles:
                    x = center_x + radius * np.cos(theta)
                    y = center_y + radius * np.sin(theta)
                    joint_path.append((x, y, -z))
            
            self.toolpath_joints[joint_id] = joint_path
            
        return self.toolpath_joints

    def export_gcode(self, mode: str = "all") -> str:
        gcode = [
            "G21 ; Unit mm", 
            "G90 ; Absolute positioning",
            f"G0 Z{self.safe_z:.3f} ; Move to Safe Z"
        ]
        
        if mode in ["all", "planar"] and self.toolpath_planar:
            gcode.append("(--- START PLANAR MACHINING ---)")
            first_pt = self.toolpath_planar[0]
            gcode.append(f"G0 X{first_pt[0]:.3f} Y{first_pt[1]:.3f}")
            gcode.append(f"G1 Z{first_pt[2]:.3f} F500")
            
            for pt in self.toolpath_planar:
                gcode.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f} Z{pt[2]:.3f} F1000")
            
            gcode.append(f"G0 Z{self.safe_z:.3f} ; Retract to Safe Z")

        if mode in ["all", "joints"] and self.toolpath_joints:
            gcode.append("(--- START JOINT-BY-JOINT MACHINING ---)")
            for joint_id, path in self.toolpath_joints.items():
                if not path:
                    continue
                gcode.append(f"( Toolpath for Joint: {joint_id} )")
                
                first_pt = path[0]
                gcode.append(f"G0 Z{self.safe_z:.3f}")
                gcode.append(f"G0 X{first_pt[0]:.3f} Y{first_pt[1]:.3f}")
                
                for pt in path:
                    gcode.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f} Z{pt[2]:.3f} F800")
                
                gcode.append(f"G0 Z{self.safe_z:.3f} ; Retract to Safe Z")

        gcode.append("M30 ; End of program")
        return "\n".join(gcode)
