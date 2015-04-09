#!/bin/bash

## Objective:
## From a DICOM set, generate a Nifti file, pull all slices out in each plane,
## then put them all together into four mp4 videos.
##
## Dependencies:
## FSL must be installed
## dmc2nii from mricron must be installed.
## ImageMagick must be installed.
## ffmpeg must be installed.
##
## Arguments:
## One argument, the name of one of the files in the DICOM set.

# Make sure we can do this. Check dependencies.
BAIL="0"
Ldcm2nii=$(which dcm2nii)
if [[ "${#Ldcm2nii}" -lt "1" ]] ; then
  echo "I cannot find dcm2nii from the mricron package. Quitting."
  BAIL="1"
fi
Lfslinfo=$(which fslinfo)
if [[ "${#Lfslinfo}" -lt "1" ]] ; then
  echo "I cannot find fslinfo from the fsl package. Quitting."
  BAIL="1"
fi
Lslicer=$(which slicer)
if [[ "${#Lslicer}" -lt "1" ]] ; then
  echo "I cannot find slicer from the fsl package. Quitting."
  BAIL="1"
fi
Lconvert=$(which convert)
if [[ "${#Lconvert}" -lt "1" ]] ; then
  echo "I cannot find convert from the imagemagick package. Quitting."
  BAIL="1"
fi
if [[ "$BAIL" -eq "1" ]] ; then
  exit 1
fi

# Make a nice place to work
mkdir working

dcm2nii $1
mv *.gz ./working/
cd working

## Find the oriented nifti file and extract its dimensions
NII=o*.gz
Los=$(2>/dev/null ls -1f $NII | wc -l)
if [[ "$Los" -eq "0" ]] ; then
  NII=*.gz
  Los=$(2>/dev/null ls -1f $NII | wc -l)
  if [[ "$Los" -eq "0" ]] ; then
    echo "I was unable to convert the DICOMs to Nifti. Quitting."
    exit 1
  fi
fi
fslinfo $NII > info.txt
Linfo=$(wc -l info.txt)
if [[ "$Linfo" -eq "0" ]] ; then
  echo "Trouble getting header information from fslinfo. Quitting."
  exit 1
fi

Xdim=$(grep -Po "(?<=^dim1 ).*" info.txt)
Ydim=$(grep -Po "(?<=^dim2 ).*" info.txt)
Zdim=$(grep -Po "(?<=^dim3 ).*" info.txt)

Xdim="$(echo -e "${Xdim}" | tr -d '[[:space:]]')"
Ydim="$(echo -e "${Ydim}" | tr -d '[[:space:]]')"
Zdim="$(echo -e "${Zdim}" | tr -d '[[:space:]]')"

echo "Image dimensions: $Xdim, $Ydim, $Zdim"

## Loop through all slices in each dimension
declare -A dims
dims[x]=$Xdim; dims[y]=$Ydim; dims[z]=$Zdim;

for axis in "${!dims[@]}" ; do
  maxslice=${dims[$axis]}
  echo "Dim $axis = $maxslice"
  for oneslice in $(seq $maxslice) ; do
    printf -v n "%04d" $oneslice
    echo "Making ${axis} frame ${n} / ${maxslice}"
    slicer $NII -${axis} -${oneslice} fr_${axis}_${n}.png
  done
done


## Resize them to HD for video
echo "Resizing images for HD"
for f in $(ls -1f fr_*.png) ; do
  # No rotation should be necessary due to smart dcm2nii earlier
  # but if it were, uncomment this and tweak angle
  # convert $f -rotate 0 $f
  
  # Resize and pad background
  convert $f -resize 1024x1024 -gravity center -background black -extent 1920x1080 "_${f}"
done

## And stitch them together into a video
echo "Making a video from the sagittal slices."
ffmpeg -framerate 10 -i _fr_x_%04d.png -c:v libx264 -r 30 -pix_fmt yuv420p sagittal.ts
ffmpeg -i sagittal.ts -acodec copy -vcodec copy ../sagittal.mp4
echo "Making a video from the coronal slices."
ffmpeg -framerate 10 -i _fr_y_%04d.png -c:v libx264 -r 30 -pix_fmt yuv420p coronal.ts
ffmpeg -i coronal.ts -acodec copy -vcodec copy ../coronal.mp4
echo "Making a video from the axial slices."
ffmpeg -framerate 10 -i _fr_z_%04d.png -c:v libx264 -r 30 -pix_fmt yuv420p axial.ts
ffmpeg -i axial.ts -acodec copy -vcodec copy ../axial.mp4
echo "Putting them all together."
ffmpeg -i "concat:sagittal.ts|coronal.ts|axial.ts" -c copy -bsf:a aac_adtstoasc ../combined.mp4

cd -
echo ""
echo "Done!"
echo "I left a lot of garbage in the working folder, though. You can delete the following:"
echo "- Three *.gz files are the Nifti versions of your DICOM set."
echo "- Lots of *.png files are individual frames of your video; keep them or chuck them."
echo "- Three *.ts files are the videos for individual planes of section."
echo "Your videos are called axial, coronal, sagittal, and combined.mp4."
echo "You should rename them to something that makes more sense."
