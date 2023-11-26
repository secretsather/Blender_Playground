bl_info = {
    "name": "Curvify",
    "author": "George Gardner",
    "version": (1,1),
    "blender": (3,0,0),
    "category": "Mesh",
    }

import bpy
import numpy as np
import math

class GTcurvify(bpy.types.Operator):
    '''Apply Bezier Curve of given proportion to selected vertices or edges'''
    
    bl_idname="mesh.curvify_line"
    bl_label = "Curvify"
    bl_options = {'REGISTER', 'UNDO'}
    
    bulgeAmt: bpy.props.FloatProperty(name="Bulge", default=.25, min=.01, max=10.0)
    
    class vert:
        def __init__(self, localIndex, globalIndex, coords, endpoint=False):
            self.localIndex = localIndex
            self.globalIndex = globalIndex
            self.coords = np.array(coords, dtype=np.float64)
            self.endpoint = endpoint
            self.lengthFromPrevious = 0.000
            self.totalPercentFromPrevious = 0.000
            
        def dvectTo(self, toCoords): #displacement Vector of this vert to specified coords
            return toCoords - self.coords
        
        def magnitudeTo(self, toCoords): #length from this vert to specified coords
            return math.sqrt(np.sum(self.dvectTo(toCoords)**2))     
        
    class Bezier():
        def TwoPoints(t, P1, P2):
            """
            Returns a point between P1 and P2, parametised by t.
            INPUTS:
                t     float/int; a parameterisation.
                P1    numpy array; a point.
                P2    numpy array; a point.
            OUTPUTS:
                Q1    numpy array; a point.
            """

            if not isinstance(P1, np.ndarray) or not isinstance(P2, np.ndarray):
                raise TypeError('Points must be an instance of the numpy.ndarray!')
            if not isinstance(t, (int, float)):
                raise TypeError('Parameter t must be an int or float!')

            Q1 = (1 - t) * P1 + t * P2
            return Q1

        def Points(t, points):
            """
            Returns a list of points interpolated by the Bezier process
            INPUTS:
                t            float/int; a parameterisation.
                points       list of numpy arrays; points.
            OUTPUTS:
                newpoints    list of numpy arrays; points.
            """
            newpoints = []
            #print("points =", points, "\n")
            for i1 in range(0, len(points) - 1):
                #print("i1 =", i1)
                #print("points[i1] =", points[i1])

                newpoints += [GTcurvify.Bezier.TwoPoints(t, points[i1], points[i1 + 1])]
                #print("newpoints  =", newpoints, "\n")
            return newpoints

        def Point(t, points):
            """
            Returns a point interpolated by the Bezier process
            INPUTS:
                t            float/int; a parameterisation.
                points       list of numpy arrays; points.
            OUTPUTS:
                newpoint     numpy array; a point.
            """
            newpoints = points
            #print("newpoints = ", newpoints)
            while len(newpoints) > 1:
                newpoints = GTcurvify.Bezier.Points(t, newpoints)
                #print("newpoints in loop = ", newpoints)

            #print("newpoints = ", newpoints)
            #print("newpoints[0] = ", newpoints[0])
            return newpoints[0]

        def Curve(t_values, points):
            """
            Returns a point interpolated by the Bezier process
            INPUTS:
                t_values     list of floats/ints; a parameterisation.
                points       list of numpy arrays; points.
            OUTPUTS:
                curve        list of numpy arrays; points.
            """

            if not hasattr(t_values, '__iter__'):
                raise TypeError("`t_values` Must be an iterable of integers or floats, of length greater than 0 .")
            if len(t_values) < 1:
                raise TypeError("`t_values` Must be an iterable of integers or floats, of length greater than 0 .")
            if not isinstance(t_values[0], (int, float)):
                raise TypeError("`t_values` Must be an iterable of integers or floats, of length greater than 0 .")

            curve = np.array([[0.0] * len(points[0])])
            for t in t_values:
                #print("curve                  \n", curve)
                #print("Bezier.Point(t, points) \n", Bezier.Point(t, points))

                curve = np.append(curve, [GTcurvify.Bezier.Point(t, points)], axis=0)

                #print("curve after            \n", curve, "\n--- --- --- --- --- --- ")
            curve = np.delete(curve, 0, 0)
            #print("curve final            \n", curve, "\n--- --- --- --- --- --- ")
            return curve
        
    def followPath(self, vIndex):
        for e in self.sEdges:
            if e.vertices[0] == self.sVerts[vIndex].index or e.vertices[1] == self.sVerts[vIndex].index: #if the vert is in this edge
                if e.index not in self.excludedEdgeIndex:
                    self.excludedEdgeIndex.append(e.index)
                    ep = True if len(self.excludedEdgeIndex) == len(self.sEdges) else False
                    
                    otherVindex = 1 if e.vertices[0] == self.sVerts[vIndex].index else 0
                    for iv, v in enumerate(self.sVerts):
                        #print(f'vert index = {v.index}')
                        if v.index == e.vertices[otherVindex]:
                            self.vertLine.append(self.vert(iv,v.index,v.co, ep))
                            #if not an endpoint, loop
                            if iv not in self.vertEndpoints:
                                #print('moving')
                                self.followPath(iv)
    
    def execute(self, context):
        #record mode
        previousMode = bpy.context.active_object.mode

        #switch to Object mode so the selection gets updated
        bpy.ops.object.mode_set(mode='OBJECT')

        #collect selected vertices and edges
        self.sVerts = [v for v in bpy.context.active_object.data.vertices if v.select]
        self.sEdges = [e for e in bpy.context.active_object.data.edges if e.select]       
        
        #find the local index of the vertices that are endpoints
        self.vertEndpoints = []
        for i, v in enumerate(self.sVerts):
            vertEdgeCount = 0
            for e in self.sEdges:
                if v.index == e.vertices[0] or v.index == e.vertices[1]:
                    vertEdgeCount += 1
            if vertEdgeCount == 1: 
                self.vertEndpoints.append(i)
            #vertEdgeCount 1 is endpoint, 2 is line, 3 is error
        if len(self.vertEndpoints) > 2: 
            #switch back to the mode we were in
            bpy.ops.object.mode_set(mode=previousMode) 
            return {'FINISHED'}       
            
        #create ordered list and starting vert
        self.vertLine = []
        self.vertLine.append(self.vert(self.vertEndpoints[0], self.sVerts[self.vertEndpoints[0]].index, self.sVerts[self.vertEndpoints[0]].co, endpoint=True))

        #follow the path, recording the verts along the way
        self.excludedEdgeIndex = []
        self.followPath(self.vertEndpoints[0])

        #get the middle point of the 2 endpoints
        displacementVector = self.vertLine[-1].coords - self.vertLine[0].coords
        middlePoint = self.vertLine[0].coords + (displacementVector / 2)
        
        #normalize the displacement vector of end points (for future use)
        displacementUnitVector = displacementVector / math.sqrt(np.sum(displacementVector**2))
            
        #get direction curve should be headed
        avgEnds = (self.vertLine[0].coords + self.vertLine[-1].coords) / 2      
        avgMiddles = np.array((0,0,0), dtype=np.float64)
        dividend = 0
        for i in range(1, len(self.vertLine) - 1,1):
            dividend += 1
            avgMiddles += self.vertLine[i].coords
        avgMiddles /= dividend
        directionVector = avgMiddles - avgEnds
        
        #project direction vector on the line formed by the end points
        projectDirection = np.dot(directionVector, displacementUnitVector)
        
        #find projected direction perpendicular to end points
        directionVector -= displacementUnitVector * projectDirection
        
        #take the unit vector of the direction
        curveDirectionUV = directionVector / math.sqrt(np.sum(directionVector**2))

        #create a 3rd point to use for our curve, the other two of which are the endpoints
        bezierCurvePoint = middlePoint + (curveDirectionUV * self.bulgeAmt)

        #Bezier Class by Byron Torres (GITHUB - torresjrjr)
        #defines how many steps to take - currently 100
        t_points = np.arange(0, 1, 0.01)

        points = np.array([self.vertLine[0].coords, bezierCurvePoint, self.vertLine[-1].coords])
        curvePoints = self.Bezier.Curve(t_points, points)

        #assign new positions to vertices
        curveSteps = len(self.vertLine) - 1
        for iv, v in enumerate(self.vertLine):
            if v.endpoint == True:
                continue
            v.coords = curvePoints[int((len(t_points) / curveSteps) * (iv))]
                
        #assign locations to actual verts
        for v in self.vertLine:
            self.sVerts[v.localIndex].co = v.coords 
     
        #switch back to the mode we were in
        bpy.ops.object.mode_set(mode=previousMode) 
    
        return {'FINISHED'}
        
def menu_func(self, context):
    self.layout.operator(GTcurvify.bl_idname)

def register():
    bpy.utils.register_class(GTcurvify)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(GTcurvify)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func)
        
if __name__ == "__main":
    register()     









    
