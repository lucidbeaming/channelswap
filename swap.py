import numpy as np
from PIL import Image, ImageEnhance
import os
import argparse
from itertools import zip_longest
import logging
import time
import hashlib
import random

def generate_filename_hash():
    """Generate a short hash based on current timestamp for unique filenames."""
    current_time = str(int(time.time() * 1000))
    hash_object = hashlib.md5(current_time.encode())
    return hash_object.hexdigest()[:6]

def grouper(iterable, n):
    """Group items from an iterable into groups of n."""
    args = [iter(iterable)] * n
    return zip_longest(*args)

def get_section_dimensions(image_path, target_height=4096, width_ratio=1.25):
    """
    Calculate section dimensions for an image.
    
    Args:
        image_path: Path to the image file
        target_height: Target height for sections (default: 4096)
        width_ratio: Ratio of section width to height (default: 1.25, i.e., 5/4)
    
    Returns:
        Tuple of (section_width, section_height)
    """
    with Image.open(image_path) as img:
        width, height = img.size
        
        scale_factor = target_height / height
        
        scaled_width = int(width * scale_factor)
        
        section_width = int(target_height * width_ratio)
        
        if section_width * 3 > scaled_width:
            section_width = scaled_width // 3
            
        return section_width, target_height

def find_common_section_size(image_paths, target_height=4096, width_ratio=1.25):
    """
    Find the common section size across multiple images.
    
    Args:
        image_paths: List of image file paths
        target_height: Target height for sections (default: 4096)
        width_ratio: Ratio of section width to height (default: 1.25)
    
    Returns:
        Tuple of (min_width, min_height) or (None, None) if error
    """
    if None in image_paths:
        return None, None
        
    try:
        dimensions = [get_section_dimensions(path, target_height, width_ratio) for path in image_paths]
        
        min_width = min(dim[0] for dim in dimensions)
        min_height = min(dim[1] for dim in dimensions)
        
        return min_width, min_height
        
    except Exception as e:
        logging.error(f"Error calculating common section size: {str(e)}")
        return None, None

def split_into_sections(image_path, section_width, section_height, bright=False, brightness_variation=0.15):
    """
    Split an image into left, middle, and right sections.
    
    Args:
        image_path: Path to the image file
        section_width: Width of each section
        section_height: Height of each section
        bright: Whether to apply random brightness variation (default: False)
        brightness_variation: Maximum brightness variation factor (default: 0.15)
    
    Returns:
        Tuple of (left_section, middle_section, right_section) PIL Images
    """
    img = Image.open(image_path)
    
    current_width, current_height = img.size
    scale_factor = section_height / current_height
    new_width = int(current_width * scale_factor)
    
    img = img.resize((new_width, section_height), Image.Resampling.LANCZOS)

    left_box = (0, 0, section_width, section_height)
    middle_box = (
        ((new_width / 2) - (section_width / 2)),
        0,
        ((new_width / 2) - (section_width / 2)) + section_width,
        section_height
    )
    right_box = ((new_width - section_width), 0, new_width, section_height)
    
    left_section = img.crop(left_box).resize((section_width, section_height), Image.Resampling.LANCZOS)
    middle_section = img.crop(middle_box).resize((section_width, section_height), Image.Resampling.LANCZOS)
    right_section = img.crop(right_box).resize((section_width, section_height), Image.Resampling.LANCZOS)
    
    if bright:
        adjusted = []
        for section in [left_section, middle_section, right_section]:
            brightness_factor = 1.0 + (random.choice([-brightness_variation, brightness_variation]))
            enhancer = ImageEnhance.Brightness(section)
            adjusted.append(enhancer.enhance(brightness_factor))
        left_section, middle_section, right_section = adjusted
    
    img.close()
    
    return left_section, middle_section, right_section

def swap_color_channels_from_sections(image_paths, output_path, bright=False, cycle=False, 
                                     target_height=4096, width_ratio=1.25, brightness_variation=0.15):
    """
    Combine RGB channels from three different images' sections.
    
    Args:
        image_paths: List of three image file paths
        output_path: Path for the output image
        bright: Whether to apply random brightness variation (default: False)
        cycle: Whether to create three versions with rotated channel assignments (default: False)
        target_height: Target height for sections (default: 4096)
        width_ratio: Ratio of section width to height (default: 1.25)
        brightness_variation: Maximum brightness variation factor (default: 0.15)
    """
    if None in image_paths:
        return
        
    try:
        section_height = target_height
        section_width = int(section_height * width_ratio)
            
        logging.debug(f"Using section size: {section_width}x{section_height}")
        
        left, _, _ = split_into_sections(image_paths[0], section_width, section_height, bright, brightness_variation)
        _, middle, _ = split_into_sections(image_paths[1], section_width, section_height, bright, brightness_variation)
        _, _, right = split_into_sections(image_paths[2], section_width, section_height, bright, brightness_variation)
        
        if not all(section.size == (section_width, section_height) 
                  for section in [left, middle, right]):
            raise ValueError("Section sizes do not match")
        
        left_array = np.array(left)
        middle_array = np.array(middle)
        right_array = np.array(right)
        
        if cycle:
            # Create three different versions with rotated channel assignments
            for cycle_index in range(3):
                result = np.zeros_like(left_array)
                
                # Rotate the channel assignments based on cycle_index
                # Cycle 0: R=left, G=middle, B=right
                # Cycle 1: R=middle, G=right, B=left  
                # Cycle 2: R=right, G=left, B=middle
                if cycle_index == 0:
                    result[:,:,0] = left_array[:,:,0]    # Red from left section
                    result[:,:,1] = middle_array[:,:,1]  # Green from middle section
                    result[:,:,2] = right_array[:,:,2]   # Blue from right section
                elif cycle_index == 1:
                    result[:,:,0] = middle_array[:,:,0]  # Red from middle section
                    result[:,:,1] = right_array[:,:,1]   # Green from right section
                    result[:,:,2] = left_array[:,:,2]    # Blue from left section
                else:  # cycle_index == 2
                    result[:,:,0] = right_array[:,:,0]   # Red from right section
                    result[:,:,1] = left_array[:,:,1]    # Green from left section
                    result[:,:,2] = middle_array[:,:,2]  # Blue from middle section
                
                # Create cycle-specific output path
                cycle_output_path = output_path.replace('.png', f'_cycle{cycle_index}.png')
                result_image = Image.fromarray(result)
                result_image.save(cycle_output_path)
                result_image.close()
        else:
            result = np.zeros_like(left_array)
            
            result[:,:,0] = left_array[:,:,0]
            result[:,:,1] = middle_array[:,:,1]
            result[:,:,2] = right_array[:,:,2]
            
            result_image = Image.fromarray(result)
            result_image.save(output_path)
            result_image.close()
        
        left.close()
        middle.close()
        right.close()
        
    except Exception as e:
        logging.error(f"Error in swap_color_channels_from_sections: {str(e)}")
        raise

def process_single_image(image_path, output_path, bright=False, cycle=False, 
                        target_height=4096, width_ratio=1.25, brightness_variation=0.15):
    """
    Process a single image by splitting it into sections and swapping color channels.
    
    Args:
        image_path: Path to the input image
        output_path: Path for the output image
        bright: Whether to apply random brightness variation (default: False)
        cycle: Whether to create three versions with rotated channel assignments (default: False)
        target_height: Target height for sections (default: 4096)
        width_ratio: Ratio of section width to height (default: 1.25)
        brightness_variation: Maximum brightness variation factor (default: 0.15)
    """
    try:
        section_height = target_height
        section_width = int(section_height * width_ratio)
        
        if not section_width or not section_height:
            raise ValueError("Could not determine section size")
            
        logging.debug(f"Using section size: {section_width}x{section_height}")
        
        left, middle, right = split_into_sections(image_path, section_width, section_height, bright, brightness_variation)
        
        left_array = np.array(left)
        middle_array = np.array(middle)
        right_array = np.array(right)
        
        if cycle:
            # Create three different versions with rotated channel assignments
            for cycle_index in range(3):
                result = np.zeros_like(left_array)
                
                # Rotate the channel assignments based on cycle_index
                # Cycle 0: R=left, G=middle, B=right
                # Cycle 1: R=middle, G=right, B=left  
                # Cycle 2: R=right, G=left, B=middle
                if cycle_index == 0:
                    result[:,:,0] = left_array[:,:,0]    # Red from left section
                    result[:,:,1] = middle_array[:,:,1]  # Green from middle section
                    result[:,:,2] = right_array[:,:,2]   # Blue from right section
                elif cycle_index == 1:
                    result[:,:,0] = middle_array[:,:,0]  # Red from middle section
                    result[:,:,1] = right_array[:,:,1]   # Green from right section
                    result[:,:,2] = left_array[:,:,2]    # Blue from left section
                else:  # cycle_index == 2
                    result[:,:,0] = right_array[:,:,0]   # Red from right section
                    result[:,:,1] = left_array[:,:,1]    # Green from left section
                    result[:,:,2] = middle_array[:,:,2]  # Blue from middle section
                
                # Create cycle-specific output path
                cycle_output_path = output_path.replace('.png', f'_cycle{cycle_index}.png')
                result_image = Image.fromarray(result)
                result_image.save(cycle_output_path)
                result_image.close()
        else:
            result = np.zeros_like(left_array)
            
            result[:,:,0] = left_array[:,:,0]
            result[:,:,1] = middle_array[:,:,1]
            result[:,:,2] = right_array[:,:,2]
            
            result_image = Image.fromarray(result)
            result_image.save(output_path)
            result_image.close()
        
        left.close()
        middle.close()
        right.close()
        
    except Exception as e:
        logging.error(f"Error processing single image {image_path}: {str(e)}")
        raise

def process_directory(input_dir, output_dir, mode='group', bright=False, cycle=False,
                     target_height=4096, width_ratio=1.25, brightness_variation=0.15):
    """
    Process all images in a directory.
    
    Args:
        input_dir: Directory containing input images
        output_dir: Directory for output images
        mode: Processing mode - 'single', 'group', or 'random' (default: 'group')
        bright: Whether to apply random brightness variation (default: False)
        cycle: Whether to create three versions with rotated channel assignments (default: False)
        target_height: Target height for sections (default: 4096)
        width_ratio: Ratio of section width to height (default: 1.25)
        brightness_variation: Maximum brightness variation factor (default: 0.15)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    image_files.sort()
    total_images = len(image_files)
    
    if mode == 'single':
        for image_file in image_files:
            try:
                input_path = os.path.join(input_dir, image_file)
                filename = f'single_{generate_filename_hash()}.png'
                output_path = os.path.join(output_dir, filename)
                
                process_single_image(input_path, output_path, bright, cycle, target_height, width_ratio, brightness_variation)
                print(f'Processed image: {image_file} -> {filename}')
                
            except Exception as e:
                logging.error(f"Error processing {image_file}: {str(e)}")
                continue
    
    elif mode == 'group':
        for i in range(total_images):
            try:
                current_group = []
                for offset in range(3):
                    if i + offset < total_images:
                        current_group.append(image_files[i + offset])
                    else:
                        break
                
                if len(current_group) < 3:
                    logging.info(f"Reached end of directory, not enough images remaining for group starting with {image_files[i]}")
                    break
                
                input_paths = [os.path.join(input_dir, f) for f in current_group]
                filename = f'group_{generate_filename_hash()}.png'
                output_path = os.path.join(output_dir, filename)
                
                swap_color_channels_from_sections(input_paths, output_path, bright, cycle, target_height, width_ratio, brightness_variation)
                print(f'Processed group starting with {image_files[i]}: {", ".join(current_group)} -> {filename}')
                
            except Exception as e:
                logging.error(f"Error processing group starting with {image_files[i]}: {str(e)}")
                continue
    else:
        for i in range(total_images):
            try:
                current_group = []
                for offset in range(3):
                    if i < total_images and offset == 0:
                        current_group.append(image_files[i])
                    elif i < total_images:
                        current_group.append(image_files[random.randint(0, total_images - 1)])
                    else:
                        break
                
                if len(current_group) < 3:
                    logging.info(f"Reached end of directory, not enough images remaining for group starting with {image_files[i]}")
                    break
                
                input_paths = [os.path.join(input_dir, f) for f in current_group]
                filename = f'group_{generate_filename_hash()}.png'
                output_path = os.path.join(output_dir, filename)
                
                swap_color_channels_from_sections(input_paths, output_path, bright, cycle, target_height, width_ratio, brightness_variation)
                print(f'Processed group: {", ".join(current_group)} -> {filename}')
                
            except Exception as e:
                logging.error(f"Error processing group starting with {image_files[i]}: {str(e)}")
                continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Combine RGB channels from image sections to create artistic color-swapped images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process images in groups of three
  python swap.py input/ output/
  
  # Process each image individually
  python swap.py input/ output/ --mode single
  
  # Create three rotated versions of each output
  python swap.py input/ output/ --cycle
  
  # Use custom dimensions
  python swap.py input/ output/ --height 2048 --width-ratio 1.5
        """
    )
    parser.add_argument('input_dir', help='Directory containing input images')
    parser.add_argument('output_dir', help='Directory for output images')
    parser.add_argument('--mode', choices=['single', 'group', 'random'], default='group',
                      help='Process mode: single (one image at a time), group (three consecutive images), or random (random combinations)')
    parser.add_argument('--bright', action='store_true', 
                      help='Apply random brightness variation to sections (±15%% by default)')
    parser.add_argument('--cycle', action='store_true', 
                      help='Create three versions of each output with rotated channel assignments')
    parser.add_argument('--height', type=int, default=4096,
                      help='Target height for image sections in pixels (default: 4096)')
    parser.add_argument('--width-ratio', type=float, default=1.25,
                      help='Ratio of section width to height (default: 1.25)')
    parser.add_argument('--brightness-variation', type=float, default=0.15,
                      help='Maximum brightness variation factor when --bright is used (default: 0.15)')
    parser.add_argument('--log-file', type=str, default='channel_swap.log',
                      help='Path to log file (default: channel_swap.log)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    logging_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler()
        ]
    )
    
    try:
        process_directory(
            args.input_dir, 
            args.output_dir, 
            args.mode, 
            args.bright, 
            args.cycle,
            args.height,
            args.width_ratio,
            args.brightness_variation
        )
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")
        exit(1)
