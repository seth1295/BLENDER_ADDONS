bl_info = {
    "name": "Scale Hierarchy to Size",
    "author": "Seth McLaughlin",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "3D Viewport > Object > Scale Hierarchy to Size (or F3)",
    "description": "Uniformly scale a parent and all its children to an exact overall world-space size",
    "category": "Object",
    "license": "MIT",
}

import bpy
from bpy.props import EnumProperty, FloatProperty
from mathutils import Vector

GEOMETRY_TYPES = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}


def hierarchy_extent(root, depsgraph, axis):
    """Measure the evaluated world-space bounds of root and its descendants."""
    low = [float('inf')] * 3
    high = [float('-inf')] * 3
    found = False
    for obj in (root, *root.children_recursive):
        if obj.type not in GEOMETRY_TYPES:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        bb = evaluated.bound_box
        if not bb:
            continue
        matrix = evaluated.matrix_world
        for corner in bb:
            p = matrix @ Vector(corner)
            for i in range(3):
                low[i] = min(low[i], p[i])
                high[i] = max(high[i], p[i])
            found = True
    if not found:
        return 0.0
    spans = [high[i] - low[i] for i in range(3)]
    return max(spans) if axis == 'LONGEST' else spans['XYZ'.index(axis)]


class OBJECT_OT_scale_hierarchy_to_size(bpy.types.Operator):
    """Resize the selected parent and all its descendants to an exact size"""
    bl_idname = "object.scale_hierarchy_to_size"
    bl_label = "Scale Hierarchy to Size"
    bl_options = {'REGISTER', 'UNDO'}

    target: FloatProperty(
        name="Target size",
        description="Desired overall dimension, in scene length units",
        default=2.5,
        min=0.000001,
        soft_max=100.0,
        unit='LENGTH',
    )
    axis: EnumProperty(
        name="Measure axis",
        description="Axis along which to measure the entire assembly",
        items=[
            ('LONGEST', 'Longest dimension', 'Largest of the world X/Y/Z spans'),
            ('X', 'World X', 'Overall X span'),
            ('Y', 'World Y', 'Overall Y span'),
            ('Z', 'World Z', 'Overall Z span'),
        ],
        default='LONGEST',
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.active_object is not None

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "axis")
        current = hierarchy_extent(context.active_object, context.evaluated_depsgraph_get(), self.axis)
        layout.label(text=f"Current size: {current:.6f} Blender units")
        layout.prop(self, "target")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=330)

    def execute(self, context):
        root = context.active_object
        current = hierarchy_extent(root, context.evaluated_depsgraph_get(), self.axis)
        if current < 1e-12:
            self.report({'ERROR'}, "No measurable geometry found under the active object")
            return {'CANCELLED'}
        factor = self.target / current
        root.scale *= factor
        context.view_layer.update()
        self.report({'INFO'}, f"{root.name}: {current:.6f} -> {self.target:.6f} Blender units")
        return {'FINISHED'}


def draw_object_menu(self, context):
    self.layout.separator()
    self.layout.operator(OBJECT_OT_scale_hierarchy_to_size.bl_idname)


def register():
    bpy.utils.register_class(OBJECT_OT_scale_hierarchy_to_size)
    bpy.types.VIEW3D_MT_object.append(draw_object_menu)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(draw_object_menu)
    bpy.utils.unregister_class(OBJECT_OT_scale_hierarchy_to_size)


if __name__ == "__main__":
    register()
