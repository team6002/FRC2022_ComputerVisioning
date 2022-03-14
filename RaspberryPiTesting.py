from pydoc import apropos
from cscore import CameraServer
from networktables import NetworkTablesInstance
from networktables import NetworkTables

import cv2
import numpy as np
import logging
import sys
import time

print("start")
team = 6002
server = False 

# start NetworkTables
ntinst = NetworkTablesInstance.getDefault()
if server:
   print("Setting up NetworkTables server")
   ntinst.startServer()
else:
   print("Setting up NetworkTables client for team {}".format(team))
   ntinst.startClientTeam(team)
   ntinst.startDSClient()

shooter_nt = NetworkTables.getTable('Turret')

cs = CameraServer.getInstance()
cs.enableLogging()

# infrared camera
camera = cs.startAutomaticCapture()
camera.setResolution(160, 120)

sink = cs.getVideo()
output = cs.putVideo("Black and White", 160, 120) 
output2 = cs.putVideo("Contour", 160, 120) 
img = np.zeros(shape=(120, 160, 3), dtype=np.uint8)

# camera = cs.startAutomaticCapture()
# camera.setResolution(320, 240)

# sink = cs.getVideo()
# output = cs.putVideo("Black and White", 320, 240) 
# output2 = cs.putVideo("Contour", 320, 240) 
# img = np.zeros(shape=(320, 240, 3), dtype=np.uint8)

print("done")
counter = 450

# time for networktables to boot up
time.sleep(2)

# def computeYoshi(TUPLE, TPLEU):
#    return math.sqrt((TUPLE[0] - TPLEU[0])**2 + (TUPLE[1] - TPLEU[1])**2)

# lastYoshi = (0, 0)

# CONSTANTS
MAX_CONTOUR_AREA = 45
MIN_CONTOUR_AREA = 5

# input lower and upper bounds of the color balls
lowerBlue = ()
upperBlue = ()

while True:
   # turret camera
   timeAH, input_img = sink.grabFrame(img)
   output_img = np.copy(input_img)

   if timeAH == 0: # There is an error
      output.notifyError(sink.getError())
      continue

   grayImage = cv2.cvtColor(input_img, cv2.COLOR_BGR2GRAY)
   blurred = cv2.GaussianBlur(grayImage, (7, 7), 0)
   thresh, blackAndWhiteImage = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
   edged = cv2.Canny(blackAndWhiteImage, 50, 150)

   _, contour_list, _ = cv2.findContours(edged, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

   cen = []

   # for c in contour_list:
   #    #approx contour
   #    peri = cv2.arcLength(c, True)
   #    approx = cv2.approxPolyDP(c, 0.01*peri, True)

   #    #if contour is retangular
   #    if len(approx) >= 4 and len(approx) <= 6:
   #       #bounding box of contour
   #       (x, y, w, h) = cv2.boundingRect(approx)
   #       aspectRatio = w / float(h)

   #       #area of og contour
   #       area = cv2.contourArea(c)
   #       hullArea = cv2.contourArea(cv2.convexHull(c))
   #       solidity = area / float(hullArea)

   #       #check the bounding box to og contour
   #       godDims = w > 25 and h > 25
   #       godSolidity = solidity > 0.9
   #       godRatio = aspectRatio >= 0.8 and aspectRatio <= 1.2

   #       #if contour is god tier
   #       if godDims and godSolidity and godRatio:
   #          #outline target
   #          cv2.drawContours(output_img, [approx], -1, (0, 0, 255), 1)
   #          # print("GOD TIER")
   #          cen.append((x, y))

   for index, contour in enumerate(contour_list):
      rect = cv2.minAreaRect(contour)

      # finding the area of minRect and rectangular contour
      rectArea = rect[1][0] * rect[1][1]
      contourArea = cv2.contourArea(contour)

      # if rectArea = 0, continue to the next contour
      if rectArea == 0:
         continue

      # take ratio of min rect and contour
      ratioArea = contourArea / rectArea

      # get rid of contours beyond the size of hub rects
      if contourArea >= MAX_CONTOUR_AREA or contourArea <= MIN_CONTOUR_AREA:
         continue

      # if the ratio is larger than 65%, add contour
      if ratioArea < .65:
         continue

      #if the contour is below a certain y value, reject
      if rect[0][1] < 50:
         continue
      
      # add center of contours to list
      center = rect[0]
      cen.append(center)

      # TEXT
      image = cv2.putText(output_img, "{:.2f}".format(ratioArea), (int(rect[0][0]), int(rect[0][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 255, 0), 1, cv2.LINE_AA)
      
      cv2.drawContours(output_img, [cv2.boxPoints(rect).astype(int)], -1, color = (0, 0, 255), thickness = 1)

   #  there aren't any contours, set x and y to -1
   if len(cen) == 0:
      shooter_nt.putNumber('cX', -1)
      shooter_nt.putNumber('cY', -1)
   else:
      # sort list based on x position
      sortedCen = sorted(cen, key=lambda x: (x[0], x[1]))

      # if even, take the first and last contour and average
      if len(sortedCen) % 2 == 0:
         averageX = (sortedCen[0][0] + sortedCen[-1][0]) / 2
         averageY = (sortedCen[0][1] + sortedCen[-1][1]) / 2
         averageCen = (averageX, averageY)
      else: # if odd, take the middle  
         midRect = int(len(sortedCen)/2)
         averageCen = sortedCen[midRect]

      # yoshi = computeYoshi(averageCen, lastYoshi)
      # if yoshi < 10:
      #    averageCen = lastYoshi
      # else:
      #    lastYoshi = averageCen
      
      # shooter_nt.putNumber('yoshiX', lastYoshi[0])
      # shooter_nt.putNumber('yoshiY', lastYoshi[1])
      # shooter_nt.putNumber('yoshiyoshi', yoshi)

      # places a crosshair at center
      cv2.drawMarker(output_img, (int(averageCen[0]),int(averageCen[1])), color=(0, 255, 0), markerType=cv2.MARKER_CROSS, thickness=1)

      # puts number to networktable
      shooter_nt.putNumber('cX', averageCen[0])
      shooter_nt.putNumber('cY', averageCen[1])

      #debugging hunt function
      # shooter_nt.putNumber('cX', -1)
      # shooter_nt.putNumber('cY', -1)

   # cv2.drawMarker(output_img, 80, 60, color=(0, 255, 0), markerType=cv2.MARKER_CROSS, thickness=1)
   cv2.line(output_img, (0, 60), (160, 60), color=(0, 0, 255), thickness=1)
   cv2.line(output_img, (80, 0), (80, 120), color=(255, 0, 0), thickness=1)

   verticalFlip = cv2.flip(output_img, 0)
   horizontalFlip = cv2.flip(verticalFlip, 1)

   # output.putFrame(blackAndWhiteImage)
   output2.putFrame(horizontalFlip)