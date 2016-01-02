import pymel.core as pymel


def create_shape_circle(size=1.0, normal=(1, 0, 0), *args, **kwargs):
    transform, make = pymel.circle(*args, **kwargs)
    make.radius.set(size)
    make.normal.set(normal)

    # Expose the rotateOrder
    make.radius.set(size)
    make.degree.set(1)
    make.sections.set(8)
    return transform, make


def create_shape_needle(size=1, length=None, radius=None, normal=(0, 1, 0), *args, **kwargs):
    # TODO: docstring
    # Resolve length
    # Default length is 4x the provided size
    if length is None:
        length = size * 4.0

    # Resolve radius
    if radius is None:
        radius = size * 0.25
    radius_mid = radius * 0.75

    y_circle_mid_max = length + radius_mid
    y_circle_mid_min = length - radius_mid
    y_circle_min = length - radius
    y_circle_max = length + radius
    xz_circle_rad = radius
    xz_circle_mid_rad = xz_circle_rad * 0.75

    shape1 = pymel.curve(d=1, p=[
        (0.0, 0.0, 0.0),
        (0.0, y_circle_min, 0.0)
    ])
    shape2 = pymel.curve(d=1, p=[
        (0.0, y_circle_max, -0.0),
        (0.0, y_circle_max, 0.0),
        (xz_circle_mid_rad, y_circle_mid_max, 0.0),
        (xz_circle_rad, length, 0.0),
        (xz_circle_mid_rad, y_circle_mid_min, 0.0),
        (0.0, y_circle_min, 0),
        (-xz_circle_mid_rad, y_circle_mid_min, -0.0),
        (-xz_circle_rad, length, 0.0),
        (-xz_circle_mid_rad, y_circle_mid_max, 0.0),
        (0.0, y_circle_max, 0.0),
        (xz_circle_mid_rad, y_circle_mid_max, 0.0)
    ])
    shape3 = pymel.curve(d=1, p=[
        (-xz_circle_mid_rad, length, -xz_circle_mid_rad),
        (-xz_circle_rad, length, 0.0),
        (-xz_circle_mid_rad, length, xz_circle_mid_rad),
        (0.0, length, xz_circle_rad),
        (xz_circle_mid_rad, length, xz_circle_mid_rad),
        (xz_circle_rad, length, 0.0),
        (xz_circle_mid_rad, length, -xz_circle_mid_rad),
        (0.0, length, -xz_circle_rad),
        (-xz_circle_mid_rad, length, -xz_circle_mid_rad),
        (-xz_circle_rad, length, 0.0),
        (-xz_circle_rad, length, 0.0)
    ])
    shape2.getShape().setParent(shape1, shape=True, relative=True)
    shape3.getShape().setParent(shape1, shape=True, relative=True)
    pymel.delete(shape2)
    pymel.delete(shape3)

    # Apply normal parameter
    # TODO: Find a better way
    need_identity = True
    normal_x, normal_y, normal_z = normal
    if normal_x:
        if normal_x < 0:
            shape1.rotateZ.set(90)
        else:
            shape1.rotateZ.set(-90)
    elif normal_y:
        if normal_y < 0:
            shape1.rotateX.set(180)
        else:
            need_identity = False
    elif normal_z:
        if normal_z < 0:
            shape1.rotateX.set(-90)
        else:
            shape1.rotateX.set(90)
    if need_identity:
        pymel.makeIdentity(shape1, apply=True, rotate=True)

    return shape1


def create_shape_double_needle(normal=(0, 1, 0), *args, **kwargs):
    normal_inv = (normal[0] * -1, normal[1] * -1, normal[2] * -1)  # TODO: find an eleguant way
    shape1 = create_shape_needle(normal=normal, *args, **kwargs)
    shape2 = create_shape_needle(normal=normal_inv, *args, **kwargs)
    for shape in shape2.getShapes():
        shape.setParent(shape1, shape=True, relative=True)
    pymel.delete(shape2)
    return shape1


def create_shape_cross(size=1.0, **kwargs):
    s1 = size * 0.5
    s2 = size
    node = pymel.curve(d=1, p=[
        (0,-s1,s1),
        (0,-s1,s2),
        (0,s1,s2),
        (0,s1,s1),
        (0,s2,s1),
        (0,s2,-s1),
        (0,s1,-s1),
        (0,s1,-s2),
        (0,-s1,-s2),
        (0,-s1,-s1),
        (0,-s2,-s1),
        (0,-s2,s1),
        (0,-s1,s1)
    ], **kwargs)
    return node


def create_shape_attrholder(size=1.0, **kwargs):
    s1 = size
    s2 = s1 * 0.7
    node = pymel.curve(d=1, p=[(0,0,s1),(0,s2,s2),(0,s1,0),(0,s2,-s2),(0,0,-s1),(0,-s2,-s2),(0,-s1,0),(0,-s2,s2),(0,0,s1),(-s2,0,s2),(-s1,0,0),(-s2,s2,0),(0,s1,0),(s2,s2,0),(s1,0,0),(s2,0,-s2),(0,0,-s1),(-s2,0,-s2),(-s1,0,0),(-s2,-s2,0),(0,-s1,0),(s2,-s2,0),(s1,0,0),(s2,0,s2),(0,0,s1),(-s2,0,s2)], k=range(26), *kwargs)

    return node
