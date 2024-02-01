import sys
import os
import pathlib
import argparse

import tifffile
import numpy as np
import numpy.lib.recfunctions as rf
from scipy.spatial.transform import Rotation

import preprocess.extended_heightfield

data_representation = []
config_path = pathlib.Path('config_data/')

file_names = os.listdir(config_path)

def read_noncomment_line( file ):
    found = False
    while not found:
        line = file.readline()
        if not line.startswith("#"):
            found = True
    return line    

def read_int( file ):
    return int( read_noncomment_line( file ) )

def read_data( file, expected_length ):
    tokens = read_noncomment_line( file ).split()    
    result = [ int(tokens[0]) ]
    for token in tokens[1:]:
        result.append( float(token) )       
    if len(result) != expected_length:
        raise AssertionError( "incorrect input line", str(result) , "length != " + str(expected_length) )
    return result

def read_sphere( file ):
    data = read_data( file, 5 )
    return data

def read_cylinder( file ):
    data = read_data( file, 9 )
    return data

def read_cubes( file ):
    data = read_data( file, 10 )
    return data

def sphere_data_to_numpy( spheres ):
    spheres_np        = np.zeros( (len(spheres), 4), dtype=np.float32 )
    for i,sphere in enumerate(spheres):
        _,x,y,z,r = sphere
        spheres_np[i,0] = x + 0.5
        spheres_np[i,1] = y + 0.5
        spheres_np[i,2] = z + 0.5
        spheres_np[i,3] = r
    return spheres_np

def cylinder_data_to_numpy( cylinders ):
    cylinders_np        = np.zeros( (len(cylinders), 9), dtype=np.float32 )
    for i,cylinder in enumerate( cylinders ):
        _,x,y,z,euler1,euler2,euler3,r,l = cylinder
        cylinders_np[i,0] = x + 0.5
        cylinders_np[i,1] = y + 0.5
        cylinders_np[i,2] = z + 0.5
        rotation_quaternion = Rotation.from_euler("ZXZ", [euler1,euler2,euler3]).as_quat()
        cylinders_np[i,3] = rotation_quaternion[0]
        cylinders_np[i,4] = rotation_quaternion[1]
        cylinders_np[i,5] = rotation_quaternion[2]
        cylinders_np[i,6] = rotation_quaternion[3]
        cylinders_np[i,7] = r 
        cylinders_np[i,8] = l * 0.5
    return cylinders_np

def cube_data_to_numpy( cylinders ):
    cubes_np        = np.zeros( (len(cubes), 10), dtype=np.float32 )
    for i,cube in enumerate( cubes ):
        _,x,y,z,euler1,euler2,euler3,r1,r2,r3 = cube
        cubes_np[i,0] = x + 0.5
        cubes_np[i,1] = y + 0.5
        cubes_np[i,2] = z + 0.5
        rotation_quaternion = Rotation.from_euler("ZXZ", [euler1,euler2,euler3]).as_quat()
        cubes_np[i,3:7] = rotation_quaternion
        cubes_np[i,7] = r1
        cubes_np[i,8] = r2
        cubes_np[i,9] = r3
    return cubes_np

output_size = 850

for filename in file_names:
    file = open( config_path/filename, mode = 'r', encoding = 'utf-8' )
    
    num_spheres   = read_int(file)
    num_cylinders = read_int(file)
    num_cubes     = read_int(file)

    spheres = []
    cylinders = []
    cubes = []

    for i in range( num_spheres ):
        spheres.append( read_sphere(file) )
    for i in range( num_cylinders ):
        cylinders.append( read_cylinder(file) )
    for i in range( num_cubes ):
        cubes.append( read_cubes(file) )

    preprocessor = preprocess.extended_heightfield.HeightFieldExtractor( (output_size, output_size), 2, 256 )

    if num_spheres > 0:
        spheres_np = sphere_data_to_numpy( spheres )
        preprocessor.add_spheres( spheres_np )
    
    if num_cylinders > 0:
        cylinders_np = cylinder_data_to_numpy( cylinders )
        preprocessor.add_cylinders( cylinders_np )

    if num_cubes > 0:
        cubes_np = cube_data_to_numpy( cubes )
        preprocessor.add_cuboids( cubes_np )

    extended_heightfield, normal_map = preprocessor.extract_data_representation( 0.0 )
    extended_heightfield = extended_heightfield.reshape( ( output_size, output_size, 4 ) )

    extended_heightfield[ extended_heightfield > 256.0 ] = 256.0
    normal_map = normal_map.squeeze( 2 )
    normal_map = rf.structured_to_unstructured( normal_map );

    normal_map = ( normal_map + 1.0 ) * 127.5

    tifffile.imwrite( filename + "_normal_map.tif", normal_map.astype( np.uint8 ), photometric='rgb')

