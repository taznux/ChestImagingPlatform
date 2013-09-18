#!/usr/bin/python

import sys
import string
import subprocess
import os

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-c", dest="caseId")
parser.add_option("--cipPython", dest="cipPythonDirectory")
parser.add_option("--tmpDir", dest="tmpDirectory")
parser.add_option("--dataDir", dest="dataDirectory")
parser.add_option("--cleanCache", action="store_true", dest="cleanCache", default="False")

(options, args) = parser.parse_args()

sys.path.append(options.cipPythonDirectory)
from cip_python import GenerateAirwayParticles
from cip_python import GenerateFeatureStrengthMap
from cip_python.vessel_particles import VesselParticles

caseId = options.caseId

region = [2,3]
region=[2]
regionTag = ['right','left']
plFileName = os.path.join(options.dataDirectory,caseId + "_partialLungLabelMap.nhdr")
ctFileName = os.path.join(options.dataDirectory,caseId + ".nhdr")

minFeatureStrength = -60


for ii in range(len(region)):
    tmpDir = os.path.join(options.tmpDirectory,regionTag[ii])
    if os.path.exists(tmpDir) == False:
        os.mkdir(tmpDir)

    # Define FileNames that will be used
    plFileNameRegion= os.path.join(tmpDir,caseId + "_" + regionTag[ii] + "_partialLungLabelMap.nhdr")
    ctFileNameRegion= os.path.join(tmpDir,caseId + "_" + regionTag[ii] + ".nhdr")
    featureMapFileNameRegion = os.path.join(tmpDir,caseId + "_" + regionTag[ii] + "_featureMap.nhdr")
    maskFileNameRegion = os.path.join(tmpDir,caseId + "_" + regionTag[ii] + "_mask.nhdr")
    particlesFileNameRegion = os.path.join(options.dataDirectory,caseId + "_" + regionTag[ii] + "AirwayParticles.vtk")

    #Create SubVolume Region
    tmpCommand ="CropLung -r %(region)d -m 1 -v 0 -i %(ct-in)s --plf %(lm-in)s -o %(ct-out)s --opl %(lm-out)s"
    tmpCommand = tmpCommand % {'region':region[ii],'ct-in':ctFileName,'lm-in':plFileName,'ct-out':ctFileNameRegion,'lm-out':plFileNameRegion}
    tmpCommand = os.path.join(options.cipBuildDirectory,"bin",tmpCommand)
    print tmpCommand
    subprocess.call( tmpCommand, shell=True )

    #Extract Lung Region + Distance map to peel lung
    tmpCommand ="ExtractChestLabelMap -r %(region)d -i %(lm-in)s -o %(lm-out)s"
    tmpCommand = tmpCommand % {'region':region[ii],'lm-in':plFileNameRegion,'lm-out':plFileNameRegion}
    tmpCommand = os.path.join(options.cipBuildDirectory,"bin",tmpCommand)
    print tmpCommand
    subprocess.call( tmpCommand, shell=True )

    tmpCommand ="unu 2op gt %(lm-in)s 0.5 -o %(lm-out)s"
    tmpCommand = tmpCommand % {'lm-in':plFileNameRegion,'lm-out':plFileNameRegion}
    print tmpCommand
    subprocess.call( tmpCommand, shell=True )

    tmpCommand ="ComputeDistanceMap -l %(lm-in)s -d %(distance-map)s -s 2"
    tmpCommand = tmpCommand % {'lm-in':plFileNameRegion,'distance-map':plFileNameRegion}
    tmpCommand = os.path.join(options.cipBuildDirectory,"bin",tmpCommand)
    print tmpCommand
    subprocess.call( tmpCommand, shell=True )

    tmpCommand ="unu 2op lt %(distance-map)s -2 -t short -o %(lm-out)s"
    tmpCommand = tmpCommand % {'distance-map':plFileNameRegion,'lm-out':plFileNameRegion}
    print tmpCommand
    subprocess.call( tmpCommand, shell=True )


    # Create Feature Strength Map for the Region
    strengthMap = FeatureStrengthMap("ridge_line",ctFileNameRegion,featureMapFileNameRegion,tmpDir)
    strengthMap._clean_tmp_dir=False
    strengthMap._max_scale = 4
    strengthMap._scale_samples = 5
    strengthMap._max_feature_strength = 10000
    strengthMap._probe_scales = [0.75,1,1.75,3]

    strengthMap.execute()

    # Threshold Feature Strength Map
    tmpCommand ="unu 2op gt %(input)s %(min-strength)f -t short -o %(output)s; unu 2op gt %(lm-input)s 0.5 | unu 2op x - %(output)s -o %(output)s"
    tmpCommand = tmpCommand % {'input':featureMapFileNameRegion,'min-strength':minFeatureStrength,'lm-input':plFileNameRegion,'output':maskFileNameRegion}
    print tmpCommand
    subprocess.call( tmpCommand, shell=True )

    # Old Airway Particles For the Region
    particlesGenerator = VesselParticles(ctFileNameRegion,particlesFileNameRegion,tmpDir,maskFileNameRegion)
    particlesGenerator._clean_tmp_dir=options.cleanCache
    particlesGenerator.execute()

