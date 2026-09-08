# machining_logic.py
import numpy as np

class CNCController:
    def __init__(self):
        self.toolpath_planar = []
        self.toolpath_joints = {}

    def generate_planar_toolpath(self, surface_z, bounds, stepover):
        self.toolpath_planar = []
        x_min, x_max, y_min, y_max = bounds
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

    def generate_joint_machining_toolpath(self, joint_list):
        self.toolpath_joints = {}
        for joint in joint_list:
            joint_id = joint['id']
            center_x, center_y = joint['center']
            radius = joint['radius']
            depth = joint['depth']
            
            joint_path = []
            for z in np.arange(0, depth, 0.5):
                angles = np.linspace(0, 2 * np.pi, 36)
                for theta in angles:
                    x = center_x + radius * np.cos(theta)
                    y = center_y + radius * np.sin(theta)
                    joint_path.append((x, y, -z))
            
            self.toolpath_joints[joint_id] = joint_path
            
        return self.toolpath_joints

    def export_gcode(self, mode="all"):
        gcode = ["G21 ; Unit mm", "G90 ; Absolute positioning"]
        
        if mode in ["all", "planar"] and self.toolpath_planar:
            gcode.append("(--- START PLANAR MACHINING ---)")
            for pt in self.toolpath_planar:
                gcode.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f} Z{pt[2]:.3f} F1000")
                
        if mode in ["all", "joints"] and self.toolpath_joints:
            gcode.append("(--- START JOINT-BY-JOINT MACHINING ---)")
            for joint_id, path in self.toolpath_joints.items():
                gcode.append(f"( Toolpath for Joint: {joint_id} )")
                for pt in path:
                    gcode.append(f"G1 X{pt[0]:.3f} Y{pt[1]:.3f} Z{pt[2]:.3f} F800")
                    
        gcode.append("M30 ; End of program")
        return "\n".join(gcode)
