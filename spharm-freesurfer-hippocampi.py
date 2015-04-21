#!/usr/bin/python3

##----------------------------------------------------------------------
## Notes:
##
## My impression is that there are two typical ways to run SPHARM-PDM:
## 1. Load the extension into Slicer3D and process a volume that is 
##    specified by a "1" flag among a background of "0"s in a 3D array
##    stored in a gipl or nii file.
## 2. Use the command-line version of the same process, called 
##    "ShapeAnalysisModule" in the SPHARM-PDM distribution.
##
## The third way is to build your own pipeline (sort of, actually I am
## copying the original spharm-pdm pipeline with modifications rather
## than contributing anything original. The benefit of this is that 
## this is a text-based open python3 script that anyone can take and
## tweak for their own needs.
##
## This script is designed to take Freesurfer output, particularly the
## Freesurfer aseg.mgz file which contains the subcortical segmentation
## information, and pull pieces from it for processing with spharm-pdm.
##
##----------------------------------------------------------------------

# Imports
import sys
import os
import argparse
import subprocess
import datetime

# Globals
mgzfile = ""
niifile = ""
logfile = ""
pathin = ""
pathout = ""
programs = [ "SegPostProcessCLP", "GenParaMeshCLP", "ParaToSPHARMMeshCLP", "mri_convert" ]
LOG=None

# Argument Parsing
parser = argparse.ArgumentParser(description="Extract hippocampi from Freesurfer data and build sharm-pdm descriptions.",
                    usage=" I need a subject ID to continue.\n" \
                          " example: $ spharm-freesurfer-hippocampi.py X012345 \n" \
                          " example: $ spharm-freesurfer-hippocampi.py X012345 --outpath /home/mike/spharms\n")
parser.add_argument("fsid",
                    help="The subject id to process, generally a folder within the fspath.")
parser.add_argument("--outpath", required=False,
                    help="Where to put spharm data. We will embed it with Freesurfer data unless asked to put it elsewhere.")
parser.add_argument("--fspath", required=False,
                    help="We assume $SUBJECTS_DIR from freesurfer, but you can set your own.")
parser.add_argument("-v", "--verbose", required=False, action="store_true",
                    help="For verbose reporting of everything as it happens.")
args = parser.parse_args()


##----------------------------------------------------------------------
## Functions:
##

def PrintVerbose(longstring, shortstring="NOPE"):
	if args.verbose==True:
		print(" + {0}".format(longstring.replace('\n', '\n ++ ')))
	else:
		if shortstring == "DUPE":
			print(" - {0}".format(longstring))
		elif shortstring != "NOPE":
			print(" - {0}".format(shortstring))
			
	try:
		with open(logfile, 'a') as LOG:
			LOG.write(longstring)
			LOG.write("\n")
		LOG.close()
	except IOError:
		# We PrintVerbose before we know if the logfile will work.
		# Just don't worry about those.
		pass
		
def EnsureReady():
	global pathin
	global pathout
	global programs
	global mgzfile
	global niifile
	global logfile
	errorString = ""
	
	# Check arguments...
	if args.outpath==None:
		pathout = "{0}/{1}".format(os.getenv('SUBJECTS_DIR','.'), args.fsid)
		logfile = "{0}/{1}.log".format(args.outpath, args.fsid)
		PrintVerbose("Got no outpath, assuming {0}.".format(pathout))
	else:
		pathout = args.outpath
		logfile = "{0}/{1}.log".format(args.outpath, args.fsid)
		
	if args.fspath==None:
		pathin = "{0}/{1}".format(os.getenv('SUBJECTS_DIR','.'), args.fsid)
		PrintVerbose("Got no fspath, assuming {0}.".format(pathin))
	else:
		pathin = "{0}/{1}".format(args.fspath, args.fsid)
		
	PrintVerbose("Accepted fsid of {0}.".format(args.fsid), "Subject {0}".format(args.fsid))
	
	# Check validity of paths...
	mgzfile = "{0}/mri/aseg.mgz".format(pathin)
	if os.path.isdir(pathin):
		PrintVerbose("{0} exists and is a directory.".format(pathin))
		if os.path.isfile(mgzfile):
			PrintVerbose("{0} is right where I expect it. Input is OK.".format(mgzfile))
		else:
			errorString = "{0}\n**ERR** {1}".format(errorString, "{0}/mri/aseg.mgz does not exist. I cannot find {1}'s aseg data.".format(pathin,args.fsid))
	else:
		errorString = "{0}\n**ERR** {1}".format(errorString, "{0}/{1} does not exist. I cannot find any of {1}'s data.".format(pathin,args.fsid))
		
	if os.path.isdir(pathout):
		PrintVerbose("{0} exists and is a directory.".format(pathout))
	else:
		# Only ask to create the directory if it's specified on the command line and all else is good.
		# Otherwise, its absence will be handled above.
		if ( args.outpath!=None and errorString=="" ):
			print("{0} does not exist. Shall I create it? (Y/N)".format(pathout))
			retval=sys.stdin.read(1)
			if ( retval=="Y" or retval=="y" ):
				print("Creating new directory: {0}".format(pathout))
				os.mkdir(pathout)
			else:
				errorString = "{0}\n**ERR** {1}".format(errorString, "I have no path to output data.")
	
	niifile = "{0}/{1}.aseg.nii".format(pathout, args.fsid)
	

	# Do we even have software we need installed?
	for program in programs:
		exepath = subprocess.Popen("which {0}".format(program), shell=True, universal_newlines=True, stdout=subprocess.PIPE).stdout.read().strip()
		if len(exepath) == 0:
			errorString = "{0}\n**ERR** {1}".format(errorString, "{0} is not available. Check that SPHARM-PDM files are in your path.".format(program))
		else:
			PrintVerbose("{0} found at {1}".format(program, exepath))
	
	# Create a log file
	LOG = open(logfile, "a")
	
	return errorString

def WrapUp():
	# Close the log file
	LOG.close()
	
def MakeNifti():
	ret = subprocess.Popen("mri_convert {0}/mri/aseg.mgz {1}/{2}.aseg.nii".format(pathin, pathout, args.fsid), shell=True, universal_newlines=True, stdout=subprocess.PIPE)
	ret.wait()
	PrintVerbose("Converted Freesurfer aseg.mgz to {2}.aseg.nii".format(pathin, pathout, args.fsid))
	if ret.returncode == 0:		
		return "{0}/{1}.aseg.nii".format(pathout, args.fsid)
	else:
		print("mri_convert failed to generate a Nifti file, not sure why. Bailing out.")
		WrapUp()
		sys.exit(1)

def CheckSegmentation(niifile):
	retval=0

	for hipside,hipid in {"L":"17","R":"53"}.items():
		PrintVerbose("Timestamp: {0}".format(datetime.datetime.now()))
		with open(logfile, "a") as LOG:
			ret = subprocess.Popen("SegPostProcessCLP --label {3} {0}/{1}.aseg.nii {0}/{1}.{2}Hip.gipl".format(pathout, args.fsid, hipside, hipid),
									shell=True, universal_newlines=True, stdout=LOG, stderr=subprocess.STDOUT)
			ret.wait()
		LOG.close()
		#PrintVerbose(ret.stdout.read().strip(), "Checked {2}.aseg.nii for {3} Hippocampus".format(pathin, pathout, args.fsid, hipside))
		PrintVerbose("Checked {2}.aseg.nii for {3} Hippocampus".format(pathin, pathout, args.fsid, hipside), "DUPE")
		retval = retval + ret.returncode

	PrintVerbose("Timestamp: {0}".format(datetime.datetime.now()))

	return retval	

def GenerateMesh():
	retval=0
	for hipside,hipid in {"L":"17","R":"53"}.items():
		PrintVerbose("Timestamp: {0}".format(datetime.datetime.now()))
		with open(logfile, "a") as LOG:
			ret = subprocess.Popen("GenParaMeshCLP --iter 512 {0}/{1}.{2}Hip.gipl {0}/{1}.{2}Hip.para {0}/{1}.{2}Hip.surf".format(pathout, args.fsid, hipside, hipid),
								shell=True, universal_newlines=True, bufsize=0, stdout=LOG, stderr=subprocess.STDOUT)
			ret.wait()
		LOG.close()
		#PrintVerbose(ret.stdout.read().strip(), "Built meshes for {3} Hippocampus".format(pathin, pathout, args.fsid, hipside))
		PrintVerbose("Built meshes for {3} Hippocampus".format(pathin, pathout, args.fsid, hipside), "DUPE")
		retval = retval + ret.returncode
		
	PrintVerbose("Timestamp: {0}".format(datetime.datetime.now()))
	
	return retval	

def GenerateSpharm():
	retval=0
	for hipside,hipid in {"L":"17","R":"53"}.items():
		ret = subprocess.Popen("ParaToSPHARMMeshCLP --spharmDegree 12 {0}/{1}.{2}Hip_para {0}/{1}.{2}Hip_surf {0}/{1}.{2}Hip_".format(pathout, args.fsid, hipside, hipid),
								shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		ret.wait()
		#PrintVerbose(ret.stdout.read().strip(), "Built SPHARM for {3} Hippocampus".format(pathin, pathout, args.fsid, hipside))
		PrintVerbose("Built SPHARM for {3} Hippocampus".format(pathin, pathout, args.fsid, hipside), "DUPE")
		retval = retval + ret.returncode
	return retval	


##----------------------------------------------------------------------
## Now actually run things.
##
## This is where the action starts by calling functions defined above.
##----------------------------------------------------------------------

PrintVerbose("Timestamp: {0}".format(datetime.datetime.now()))
PrintVerbose("\n ( 1. ) Pre-flight check of the environment...")

errstring = EnsureReady()
if errstring != "":
	print(errstring)
	print("The program will exit without executing any of the spharm-pdm pipeline.")
	WrapUp()
	sys.exit()

PrintVerbose("\n ( 2. ) Convert Freesurfer segmentation to Nifti format...")
infile = MakeNifti()

PrintVerbose("\n ( 3. ) Checking hippocampi for sphericity...")
if CheckSegmentation(infile) == 0:
	PrintVerbose("\n ( 4. ) Generate the mesh...")
	GenerateMesh()
	
	PrintVerbose("\n ( 5. ) Generate the spherical harmonic description...")
	GenerateSpharm()
else:
	print("**ERR** encountered problems with the sphericity of the hippocampus, could not generate mesh or spharm")



PrintVerbose("Timestamp: {0}".format(datetime.datetime.now()))
print("Done!")
