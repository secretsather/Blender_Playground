import bpy
import numpy as np
import math


bl_info = {
    "name": "Straighten",
    "author": "George Gardner",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "category": "Mesh",
}


class GTstraighten(bpy.types.Operator):
    """ Make a straight line from selected vertices or edges """
    bl_idname = "mesh.straight_line"
    bl_label = "Straighten"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # record mode
        previousMode = bpy.context.active_object.mode

        # switch to Object mode so the selection gets updated
        bpy.ops.object.mode_set(mode='OBJECT')

        # collect selected vertices and edges
        selectedVerts = [v for v in bpy.context.active_object.data.vertices if v.select]
        selectedEdges = [e for e in bpy.context.active_object.data.edges if e.select]

        self.vertEndpoints = []
        self.sVerts = selectedVerts
        self.sEdges = selectedEdges
        self.excludedEdgeIndex = []

        # find the vertices that are endpoints
        for i, v in enumerate(self.sVerts):
            vertEdgeCount = 0
            for e in self.sEdges:
                if v.index == e.vertices[0] or v.index == e.vertices[1]:
                    vertEdgeCount += 1
            if vertEdgeCount == 1:
                self.vertEndpoints.append(i)
            # vertEdgeCount 1 is endpoint, 2 is line, 3 is error
        # if len(vertEndpoints) > 2 then you have a problem

        # create ordered list and starting vert
        self.vertLine = []
        self.vertLine.append(self.Vert(self.vertEndpoints[0], self.sVerts[self.vertEndpoints[0]].index,
                                       self.sVerts[self.vertEndpoints[0]].co, endpoint=True))

        # follow the path, recording the verts along the way
        self.follow_path(self.vertEndpoints[0])

        # calulate total length
        totalLength = 0.000
        prevCoords = (0, 0, 0)
        for iv, v in enumerate(self.vertLine):
            if iv == 0:
                prevCoords = v.coords
                continue
            else:
                v.lengthFromPrevious = v.magnitude_to(prevCoords)
                totalLength += v.lengthFromPrevious
            prevCoords = v.coords

            # assign earch vertex a percentage of total length
        for iv, v in enumerate(self.vertLine):
            if v.lengthFromPrevious > 0:
                v.totalPercentFromPrevious = v.lengthFromPrevious / totalLength

        # get vector between two endpoints, then magnitude, then unit vector?
        displacementVector = self.vertLine[-1].coords - self.vertLine[0].coords
        # totalLength = math.sqrt(np.sum(displacementVector ** 2))

        # from start, each subsequent vert should have percentage of total magnitude in same vector direction - first
        # and last vector untouched
        runningCoords = self.vertLine[0].coords
        for iv, v in enumerate(self.vertLine):
            if v.endpoint:
                continue
            else:
                v.coords = runningCoords + (displacementVector * v.totalPercentFromPrevious)
                runningCoords = v.coords

        # assign locations to actual verts
        for v in self.vertLine:
            self.sVerts[v.localIndex].co = v.coords

            # switch back to the mode we were in
        bpy.ops.object.mode_set(mode=previousMode)

        return {'FINISHED'}

    class Vert:
        def __init__(self, local_index, global_index, coords, endpoint=False):
            self.localIndex = local_index
            self.globalIndex = global_index
            self.coords = np.array(coords, dtype=np.float64)
            self.endpoint = endpoint
            self.lengthFromPrevious = 0.000
            self.totalPercentFromPrevious = 0.000

        def displacement_vector_to(self, to_coords):  # displacement Vector of this vert to specified coords
            return to_coords - self.coords

        def magnitude_to(self, to_coords):  # length from this vert to specified coords
            return math.sqrt(np.sum(self.displacement_vector_to(to_coords) ** 2))

    def follow_path(self, v_index):
        for e in self.sEdges:
            if e.vertices[0] == self.sVerts[v_index].index or e.vertices[1] == self.sVerts[v_index].index:
                if e.index not in self.excludedEdgeIndex:
                    self.excludedEdgeIndex.append(e.index)
                    ep = True if len(self.excludedEdgeIndex) == len(self.sEdges) else False

                    otherVindex = 1 if e.vertices[0] == self.sVerts[v_index].index else 0
                    for iv, v in enumerate(self.sVerts):
                        # print(f'vert index = {v.index}')
                        if v.index == e.vertices[otherVindex]:
                            self.vertLine.append(self.Vert(iv, v.index, v.co, ep))
                            # if not an endpoint, loop
                            if iv not in self.vertEndpoints:
                                # print('moving')
                                self.follow_path(iv)


def menu_func(self, context):
    self.layout.operator(GTstraighten.bl_idname)


def register():
    bpy.utils.register_class(GTstraighten)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func)


def unregister():
    bpy.utils.unregister_class(GTstraighten)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func)


if __name__ == "__main":
    register()
