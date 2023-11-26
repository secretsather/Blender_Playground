import bpy
from mathutils import Vector

sphere_diameter = 100  # mm
wall_thickness = 2.5    # mm

sphere_radius = sphere_diameter / 2
sphere_center = Vector((0, 0, sphere_radius))

point_light = Vector((0,0,23.7))

attempt_connecting_edges = False


class Stereographic:
    def __init__(self, mesh1, name, center, radius, thickness, point_light):
        # Point light at top of sphere
        #self.point_light = center + Vector((0, 0, sphere_radius))
        self.point_light = point_light

        # Calculate inner & outer intersections with sphere
        outer_vertices = self.sphere_collisions(mesh1, center, radius)
        inner_vertices = self.sphere_collisions(mesh1, center, radius - thickness)

        # Increase references to indices so you can double up the mesh (for inner & outer)
        original_vcount = len(mesh1.vertices)  # Original vertex count
        inner_edges = [(e.vertices[0] + original_vcount, e.vertices[1] + original_vcount) for e in mesh1.edges]
        inner_faces = [[v_idx + original_vcount for v_idx in p.vertices] for p in mesh1.polygons]

        # Double up the mesh using the outer and inner data
        self.vertices = outer_vertices + inner_vertices
        self.edges = [e.vertices[:] for e in mesh1.edges] + inner_edges
        self.faces = [f.vertices[:] for f in mesh1.polygons] + inner_faces

        # Find all vertices which have either 2 or 3 connected edges
        perimeter_vert_indices = self.find_perimeter_vert_indices(mesh)

        # Get connecting geometry between inner & outer mesh
        c_edges, c_faces = self.return_connect_mesh(perimeter_vert_indices, mesh1, original_vcount)
        self.edges += c_edges
        self.faces += c_faces

        # Create new mesh, object
        name = name + "_stereographic"
        mesh2 = bpy.data.meshes.new(name=name)
        obj = bpy.data.objects.new(name, mesh2)
        bpy.context.collection.objects.link(obj)  # Link the object to the scene
        mesh2.from_pydata(self.vertices, self.edges, self.faces)  # Set the mesh data
        
        # Ensure the newly created object is active and in edit mode
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        # Recalculate normals (equivalent to Shift+N in edit mode)
        bpy.ops.mesh.normals_make_consistent(inside=False)

        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        mesh2.update()  # Update the mesh with new data

    def return_connect_mesh(self, p_verts, _mesh, vcount):
        connected_verts = []
        _edges = []
        _faces = []
        for ek in _mesh.edge_keys:
            if ek[0] in p_verts and ek[1] in p_verts:
                if ek[0] not in connected_verts:
                    _edges.append([ek[0], ek[0] + vcount])
                    connected_verts.append(ek[0])
                if ek[1] not in connected_verts:
                    _edges.append([ek[1], ek[1] + vcount])
                    connected_verts.append(ek[1])
                _faces.append([ek[0], ek[1], ek[1] + vcount, ek[0] + vcount])
        return _edges, _faces

    def find_perimeter_vert_indices(self, m):
        # Dictionary to count edges per vertex
        edge_count = {i: 0 for i in range(len(m.vertices))}

        # Count the edges for each vertex
        for edge in m.edges:
            edge_count[edge.vertices[0]] += 1
            edge_count[edge.vertices[1]] += 1

        # Find vertices connected to only two edges
        return [v for v, count in edge_count.items() if count == 2 or count == 3]

    def sphere_collisions(self, _mesh, center, radius):
        verts = []

        # Iterate through all vertices, returning location of intersections with sphere
        for v in _mesh.vertices:
            intersections = self.find_line_sphere_intersection(v.co, self.point_light, center, radius)
            # todo may intersect more than once, also handle empty set returned
            verts.append(tuple(intersections[-1]))

        assert len(verts) == len(_mesh.vertices)

        return verts

    def find_line_sphere_intersection(self, v1, v2, s_center, s_radius):
        """
        Finds the intersection point of a line segment and a sphere.

        :param v1: First vertex of the line segment as a Vector
        :param v2: Second vertex of the line segment as a Vector
        :param s_center: Center of the sphere as a Vector
        :param s_radius: Radius of the sphere
        :return: A list of intersection points (each as a Vector), or an empty list if no intersection
        """
        # Direction vector of the line
        line_dir = v2 - v1

        # Vector from sphere center to first vertex
        vec = v1 - s_center

        # Coefficients for the quadratic equation (a*t^2 + b*t + c = 0)
        a = line_dir.dot(line_dir)
        b = 2 * vec.dot(line_dir)
        c = vec.dot(vec) - s_radius ** 2

        # Discriminant
        discriminant = b ** 2 - 4 * a * c

        # If discriminant is negative, there are no real roots (no intersection)
        if discriminant < 0:
            return []

        # Calculate the two solutions of t
        sqrt_discriminant = discriminant ** 0.5
        t1 = (-b + sqrt_discriminant) / (2 * a)
        t2 = (-b - sqrt_discriminant) / (2 * a)

        # Check if these solutions lie within the line segment (0 <= t <= 1)
        intersection_points = []
        if 0 <= t1 <= 1:
            intersection_points.append(v1 + t1 * line_dir)
        if 0 <= t2 <= 1:
            intersection_points.append(v1 + t2 * line_dir)

        return intersection_points


# Get the active object
active_obj = bpy.context.active_object

# Check if MESH object type
if active_obj and active_obj.type == 'MESH':
    mesh = active_obj.data

    _ = Stereographic(mesh, active_obj.name, sphere_center, sphere_radius, wall_thickness, point_light)
