# mfsutils
Mike's utility scripts and programs

This is a central repository of scripts that make my life easier and may do the same for you. It's a miscellaneous grab bag that I try to keep well documented.


### animate-a-dicom.sh

a bash script that reads a DICOM set of neuroimages and creates an mp4 video scanning through in each direction.
	
dependencies:
- FSL
- ImageMagick
- ffmpeg
- dcm2nii (from mricron)


### spharm-freesurfer-hippocampi.py

a python script that allows full SPHARM processing of a batch of many hippocampi.
	
The original SPHARM-PDM software from Martin Styner's lab does the same thing, but for a single neuroimage within Slicer.


### mfs_dupefiles.py

a python script that is probably not useful to anyone else. It checks a file against a database of all other files on my network to determine whether it is a duplicate.
	
dependencies:
- a mysql database already created with appropriate credentials and structure

