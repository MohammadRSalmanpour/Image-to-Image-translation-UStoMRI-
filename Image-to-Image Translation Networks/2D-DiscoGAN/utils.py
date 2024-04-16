import os
import nibabel as nib
from tqdm import tqdm
import tensorflow as tf
import glob
import numpy as np
import math

from scipy import ndimage

import matplotlib.pylab as plt



def create_dataset(path, val_ratio=0.1, test_ratio=0.15, shuffle=True, seed=None):
    train_ratio = 1 - (val_ratio + test_ratio)

    train_id_dirs = glob.glob(os.path.join(path, "train", "*"))
    val_id_dirs = glob.glob(os.path.join(path, "val", "*"))
    test_id_dirs = glob.glob(os.path.join(path, "test", "*"))

    train_npz_files = multi_folder_glob(train_id_dirs, "*.npz")
    val_npz_files = multi_folder_glob(val_id_dirs, "*.npz")
    test_npz_files = multi_folder_glob(test_id_dirs, "*.npz")

    # suffeling the data
    if shuffle:
        np.random.seed(seed)
        np.random.shuffle(train_npz_files)
        np.random.seed(seed)
        np.random.shuffle(val_npz_files)
        np.random.seed(seed)
        np.random.shuffle(test_npz_files)

    file_names = {
        'train':train_npz_files,
        'val':val_npz_files,
        'test':test_npz_files
        }
    
    train_dataset = tf.data.Dataset.from_tensor_slices(train_npz_files)
    train_dataset = train_dataset.map(
        lambda file_path: tf.py_function(load_sample, [file_path], (tf.float32, tf.float32))
    )
    val_dataset = tf.data.Dataset.from_tensor_slices(val_npz_files)
    val_dataset = val_dataset.map(
        lambda file_path: tf.py_function(load_sample, [file_path], (tf.float32, tf.float32))
    )
    test_dataset = tf.data.Dataset.from_tensor_slices(test_npz_files)
    test_dataset = test_dataset.map(
        lambda file_path: tf.py_function(load_sample, [file_path], (tf.float32, tf.float32))
    )

    return train_dataset, val_dataset, test_dataset, file_names



def multi_folder_glob(dirs, glob_pattern):
    """
    runs glob in a list of folder and merges their results
    """
    files = []
    for dir in dirs:
        files.extend(glob.glob(os.path.join(dir, glob_pattern)))
    return files


def load_sample(file_path):
    data = np.load(file_path.numpy(), allow_pickle=True)  # convert Tensor to numpy
    return data['us'], data['mri']



def min_max_normalize(image): 
    image_min = np.min(image)
    image_max = np.max(image)

    image = (image - image_min ) / ( image_max - image_min)

    return image


def resize_volume(img, resize_to):
    """Resize across z-axis"""
    # Set the desired depth
    desired_depth = resize_to[-1]
    desired_width = resize_to[0]
    desired_height = resize_to[1]
    # Get current depth
    current_depth = img.shape[-1]
    current_width = img.shape[0]
    current_height = img.shape[1]
    # Compute depth factor
    depth = current_depth / desired_depth
    width = current_width / desired_width
    height = current_height / desired_height
    depth_factor = 1 / depth
    width_factor = 1 / width
    height_factor = 1 / height
    # Rotate
    #img = ndimage.rotate(img, 90, reshape=False)
    # Resize across z-axis
    img = ndimage.zoom(img, (width_factor, height_factor, depth_factor), order=1)
    return img



def get_usable_US_and_MRI_names(US_dataset_path, MRI_dataset_path):
    '''
    This function finds the intersection of the names of MRI data and US data. 
    In other words, it considers the name of each US data when there is a corresponding MRI data and vice versa.
    each data which does not have a corresponding pair will be ignored.
    '''
    US_data_names = os.listdir(US_dataset_path)
    MRI_data_names = os.listdir(MRI_dataset_path)

    # Extracting usable US names
    replaced_name_from_MRI_to_US = lambda MRI_name:rename_data_based_on_type(MRI_name, replace_type_with='US')
    MRIs_replaced_temp = list(map(replaced_name_from_MRI_to_US, MRI_data_names))

    usable_US_names = list(set(US_data_names).intersection(set(MRIs_replaced_temp)))
    
    replaced_name_from_US_to_MRI = lambda US_name:rename_data_based_on_type(US_name, replace_type_with='MRI')
    usable_MRI_names = list(map(replaced_name_from_US_to_MRI, usable_US_names))

    return usable_US_names, usable_MRI_names


def rename_data_based_on_type(data_name, replace_type_with):
    new_name_list = data_name.split('_')
    new_name_list[1] = replace_type_with
    return '_'.join(new_name_list)


def get_volume_metadata(vol_dataset_path):
    '''returns image volume's metadata based on the first image volume in a given dataset path'''
    sample_volume_name = os.listdir(vol_dataset_path)[0]
    sample_volume_path = os.path.join(vol_dataset_path, sample_volume_name)
    nii_img = nib.load(sample_volume_path)
    images_metadata = {'affine':nii_img.affine, 'header':nii_img.header}
    return images_metadata
    
