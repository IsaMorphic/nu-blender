# nu-blender
# Copyright (C) 2025 Seán de Búrca

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class NupImport(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""

    bl_idname = "import_scene.lsw1_nup"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import NUP"

    # ImportHelper mix-in class uses this.
    filename_ext = ".nup"

    filter_glob: StringProperty(
        default="*.nup",
        options={"HIDDEN"},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        from .nup import import_nup

        return import_nup(context, self.filepath)


def menu_func_import(self, context):
    self.layout.operator(NupImport.bl_idname, text="LSW1 Scene (.nup)")


def register():
    bpy.utils.register_class(NupImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(NupImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # Test call.
    bpy.ops.import_scene.lsw1_nup("INVOKE_DEFAULT")
