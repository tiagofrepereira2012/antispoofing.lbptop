#!/usr/bin/env python
#Tiago de Freitas Pereira <tiagofrepereira@gmail.com>
#Thu Jul 19 12:49:15 CET 2012

"""Support methods to compute the Local Binary Pattern (LBP) histogram of an image
"""

import os, sys
import numpy
import math
import bob.ip.color
import bob.ip.base

""""
" Convert a sequence of RGB Frames to a sequence of Gray scale frames and do the face normalization over a given bounding box (bbx) in an image (around the detected face for example).

Keyword Parameters:
  rgbFrameSequence
    The sequence of frames in the RGB
  
  locations
    The face locations
  sz
   The size of the rescaled face bounding box

  bbxsize
    Considers as invalid all the bounding boxes with size smaller then this value

"""
def rgbVideo2grayVideo_facenorm(rgbFrameSequence,locations,sz,bbxsize_filter=0):
  grayFaceNormFrameSequence = numpy.empty(shape=(0,sz,sz))
  
  for k in range(0, rgbFrameSequence.shape[0]):
    bbx = locations[k]
    
    if bbx and bbx.is_valid() and bbx.height > bbxsize_filter:
      frame = bob.ip.color.rgb_to_gray(rgbFrameSequence[k,:,:,:])
      cutframe = frame[bbx.y:(bbx.y+bbx.height),bbx.x:(bbx.x+bbx.width)] # cutting the box region
      tempbbx = numpy.ndarray((sz, sz), 'float64')
      normbbx = numpy.ndarray((sz, sz), 'uint8')
      bob.ip.base.scale(cutframe, tempbbx) # normalization
      tempbbx_ = tempbbx + 0.5 #TODO: UNDERSTAND THIS
      tempbbx_ = numpy.floor(tempbbx_)
      normbbx = numpy.cast['uint8'](tempbbx_)
      
      #Preparing the data to append.
      #TODO: Maybe a there is a better solution
      grayFaceNormFrame = numpy.empty(shape=(1,sz,sz))
      grayFaceNormFrame[0] = normbbx
      grayFaceNormFrameSequence = numpy.append(grayFaceNormFrameSequence,grayFaceNormFrame,axis=0)

  return grayFaceNormFrameSequence


"""
" Select the reference bounding box for a volume, which means to select only one bounding box for a volume.
  The valid bounding box is the center; if it is not exists, take the first valid, otherwise none is  returned

  @param locations The dictionary with face locations
  @param rangeValues The range of the volume to be analysed

  @return The bounding box to use in the volume

"""
def getReferenceBoundingBox(locations,rangeValues):
  
  #First trying to get the center frame
  center = (max(rangeValues)+min(rangeValues))/2
  bbx = locations[center]

  if bbx and bbx.is_valid():
    return bbx

  bbx = None
  #if the center is invalid, try to get the first valid
  for i in rangeValues:
    if(i==center):
      continue

    if locations[i] and locations[i].is_valid():
      bbx = locations[i]
      break

  return bbx


"""
 Get a volume with normalized faces. 
 This function will analize a specific range of frames, with the same bounding box a will return a numpy array with the normalized faces

 @param grayFrameSequence The all frame sequence
 @param rangeValues The range of the volume to be analysed
 @param locations The all face locations
 @param the size of normalized faces. Tuple of the form (height, width). If None, then normalization will be performed depending on the size of the middle frame

 @return The selected volume (selected with the rangeValues) with the normalized faces

"""
def getNormFacesFromRange(grayFrameSequence,rangeValues,locations,sz):

  #If there is no bounding boxes, this volume will no be analised  
  bbx = getReferenceBoundingBox(locations,rangeValues)
  if(bbx is None):
    return None

  if sz == None: # normalization should be done with respect to face bbx of the middle frame
    refframe = rangeValues[len(rangeValues)/2] # the middle frame
    sz = [locations[refframe].height, locations[refframe].width]

  selectedFrames = grayFrameSequence[rangeValues]
  nFrames = selectedFrames.shape[0]
  selectedNormFrames = numpy.zeros(shape=(nFrames,sz[0],sz[1]),dtype='uint8')

  for i in range(nFrames):
    frame = selectedFrames[i]
    cutframe = frame[bbx.y:(bbx.y+bbx.height),bbx.x:(bbx.x+bbx.width)] # cutting the box region
    tempbbx = numpy.ndarray(sz, 'float64')
    #normbbx = numpy.ndarray((sz, sz), 'uint8')
    bob.ip.base.scale(cutframe, tempbbx) # normalization
    tempbbx_ = tempbbx + 0.5
    tempbbx_ = numpy.floor(tempbbx_)
    selectedNormFrames[i] = numpy.cast['uint8'](tempbbx_)
    
  return selectedNormFrames

"""
" Calculate the LBPTop histograms
"
" Keyword parameters
"
"  @param grayFaceNormFrameSequence
"     The sequence of FACE frames in grayscale
"  @param  nXY
"     Number of points around the center pixel in the XY direction
"  @param  nXT
"     Number of points around the center pixel in the XT direction
"  @param nYT
"     Number of points around the center pixel in the YT direction
"  @param rX
"     The radius of the circle on which the points are taken (for circular LBP) in the X axis
"  @param rY
"     The radius of the circle on which the points are taken (for circular LBP) in the Y axis
"  @param rT
"     The radius of the circle on which the points are taken (for circular LBP) in the T axis
"  @param cXY
"     True if circular LBP is needed in the XY plane, False otherwise
"  @param cXT
"     True if circular LBP is needed in the XT plane, False otherwise
"  @param cYT
"     True if circular LBP is needed in the YT plane, False otherwise
"  @param lbptype
"     The type of the LBP operator (regular, uniform or riu2)
"  @param histrogramOutput
"     If the output is really a histogram. Otherwise a LBPTop volume for each plane will be returned 
"
"  @returns A sequence of 3 histograms or 3 LBPTOP images. Is the grayFaceNormFrameSequence was equal to None, a NaN histograms will be returned
"""
def lbptophist(grayFaceNormFrameSequence,nXY,nXT,nYT,rX,rY,rT,cXY,cXT,cYT,lbptypeXY,lbptypeXT,lbptypeYT,elbptypeXY,elbptypeXT,elbptypeYT,histrogramOutput=True):
  
  elbps = {'regular':'regular', 'transitional':'trainsitional', 'direction_coded':'direction-coded', 'modified':'regular'}

  uniformXY = False
  riu2XY    = False

  uniformXT = False
  riu2XT    = False

  uniformYT = False
  riu2YT    = False

  if(lbptypeXY=='uniform'):
    uniformXY = True
  else:    
    if(lbptypeXY=='riu2'):
      riu2XY=True

  if(lbptypeXT=='uniform'):
    uniformXT = True
  else:
    if(lbptypeXT=='riu2'):
      riu2XT=True

  if(lbptypeYT=='uniform'):
    uniformYT = True
  else:
    if(lbptypeYT=='riu2'):
      riu2YT=True

  ## mLBP
  #XY
  mctXY = False
  if elbptypeXY=='modified': 
    mctXY = True

  #XT
  mctXT = False
  if elbptypeXT=='modified': 
    mctXT = True

  #YT
  mctYT = False
  if elbptypeYT=='modified': 
    mctYT = True

  #Creating the LBP operators for each plane
  lbp_XY = 0
  lbp_XT = 0
  lbp_YT = 0

  #XY
  lbp_XY = bob.ip.base.LBP(neighbors = nXY, radius_x=rX, radius_y=rY, circular=cXY, uniform=uniformXY, rotation_invariant=riu2XY, to_average=mctXY, elbp_type=elbps[elbptypeXY])
  #lbp_XY.radius2 = rY

  #XT
  lbp_XT = bob.ip.base.LBP(neighbors = nXT, radius_x=rX, radius_y=rT, circular=cXT, uniform=uniformXT, rotation_invariant=riu2XT, to_average=mctXT, elbp_type=elbps[elbptypeXT])
  #lbp_XT.radius2 = rT

  
  #YT
  lbp_YT = bob.ip.base.LBP(neighbors = nYT, radius_x=rY, radius_y=rT, circular=cYT, uniform=uniformYT, rotation_invariant=riu2YT, to_average=mctYT,elbp_type=elbps[elbptypeYT])
  #lbp_YT.radius2 = rT
  
  #If there is no face in the volume, returns an nan sequence
  if(grayFaceNormFrameSequence is None):
    histXY = numpy.zeros(shape=(1,lbp_XY.max_label)) * numpy.NaN
    histXT = numpy.zeros(shape=(1,lbp_XT.max_label)) * numpy.NaN
    histYT = numpy.zeros(shape=(1,lbp_YT.max_label)) * numpy.NaN
    return histXY,histXT,histYT

  #Creating the LBPTop object
  lbpTop = bob.ip.base.LBPTop(lbp_XY,lbp_XT,lbp_YT)

  #Alocating the LBPTop Images
  max_radius = max(lbp_XY.radii[0],lbp_XY.radii[1],lbp_XT.radii[0])

  #Allocating for LBPTOP images
  timeLength = grayFaceNormFrameSequence.shape[0]
  width      = grayFaceNormFrameSequence.shape[1]
  height     = grayFaceNormFrameSequence.shape[2]

  xy_width  = int(width      - (max_radius * 2))
  xy_height = int(height     - (max_radius * 2))
  tLength   = int(timeLength - (max_radius * 2))


  #Creating the LBP Images for each direction
  XY = numpy.zeros(shape=(tLength,xy_width,xy_height),dtype='uint16')
  XT = numpy.zeros(shape=(tLength,xy_width,xy_height),dtype='uint16')
  YT = numpy.zeros(shape=(tLength,xy_width,xy_height),dtype='uint16')

  #If the is no face in the volume, returns an nan sequence
  if(grayFaceNormFrameSequence is None):
    histXY = numpy.zeros(shape=(XY.shape[0],lbp_XY.max_label)) * numpy.NaN
    histXT = numpy.zeros(shape=(XT.shape[0],lbp_XT.max_label)) * numpy.NaN
    histYT = numpy.zeros(shape=(YT.shape[0],lbp_YT.max_label)) * numpy.NaN
    return histXY,histXT,histYT 

  #Calculanting the LBPTop Images

  lbpTop(grayFaceNormFrameSequence,XY,XT,YT)

  ### Calculating the histograms
  if(histrogramOutput):
    #XY
    histXY = numpy.zeros(shape=(XY.shape[0],lbp_XY.max_label))
    for i in range(XY.shape[0]):
      histXY[i] = bob.ip.base.histogram(XY[i], (0, lbp_XY.max_label-1), lbp_XY.max_label)
      #histogram normalization
      histXY[i] = histXY[i] / sum(histXY[i])

    #XT
    histXT = numpy.zeros(shape=(XT.shape[0],lbp_XT.max_label))
    for i in range(XT.shape[0]):
      histXT[i] = bob.ip.base.histogram(XT[i], (0, lbp_XT.max_label-1), lbp_XT.max_label)
      #histogram normalization
      histXT[i] = histXT[i] / sum(histXT[i])

    #YT
    histYT = numpy.zeros(shape=(YT.shape[0],lbp_YT.max_label))
    for i in range(YT.shape[0]):
      histYT[i] = bob.ip.base.histogram(YT[i], (0, lbp_YT.max_label-1), lbp_YT.max_label)
      #histogram normalization
      histYT[i] = histYT[i] / sum(histYT[i])

    return histXY,histXT,histYT

  else:
    #returning the volume
    return XY,XT,YT


"""
 Return a numpy array with all LBPTOP features
 
 @param files List of file objects with the data
 @param files Retrieve the nan Lines

 @return Return a list with 5 numpy arrays; one of each LBPTOP planes (XY,XT,YT) and combinations (XT+YT and XY+XT+YT).
"""
def create_full_dataset(files,inputDir,retrieveNanLines=False):
  dataset = None

  for obj in files:

    filename = str(obj.make_path(inputDir,extension='.hdf5'))
    fvs = bob.io.base.load(filename)

    if dataset is None:
      #each individual plane
      dataset = fvs
    else:
      #appending each individual plane
      dataset = numpy.concatenate((dataset,fvs),axis=0)

  #Will remove the Nan data 
  if(not retrieveNanLines):
    nanLines = numpy.array([numpy.sum(numpy.isnan(dataset[j,:])) for j in range(dataset.shape[0])])
    nanLines = numpy.where(nanLines>0)[0]

    #removing the lines with nan
    dataset = numpy.delete(dataset,nanLines,axis=0)

  return dataset


def map_scores(indir, score_dir, objects, score_list):
  """Maps frame scores to frames of the objects. Writes the scores for each frame in a file, NaN for invalid frames

  Keyword parameters:

  indir: the directory with the feature vectors (needed to read which frames are invalid)

  score_dir: the directory where the score files are going to be written

  objects: list of objects

  score_list: list of scores for the given objects
  """
  num_scores = 0 # counter for how many valid frames have been processed so far in total of all the objects
  for obj in objects:
    filename = os.path.expanduser(obj.make_path(indir, '.hdf5'))
    feat = bob.io.load(filename)
    indices = ~numpy.isnan(feat).any(axis=1) #find the indices of invalid frames (they are set to False in the resulting array)
    scores = numpy.ndarray((len(indices), 1), dtype='float64') 
    scores[indices] = score_list[num_scores:num_scores + sum(indices)] # set the scores of the valid frames only
    scores[~indices] = numpy.NaN # set NaN for the scores of the invalid frames
    num_scores += sum(indices) # increase the number of valid scores that have been already maped
    obj.save(scores, score_dir, '.hdf5') # save the scores
   
