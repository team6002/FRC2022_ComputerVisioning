from cscore import CameraServer
from networktables import NetworkTablesInstance
from networktables import NetworkTables

import cv2
import numpy as np
import logging
import sys
import time
import math

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

# # ball detection cameras
# camera1 = cs.startAutomaticCapture(dev=1)
# camera1.setResolution(160, 120)

# sink1 = cs.getVideo()

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
   # timeAH, input_img1 = sink1.grabFrame(img)

   # if timeAH == 0: # There is an error
   #    output.notifyError(sink1.getError())
   #    continue

   # # gets rid of high frequency noise and converts to a HSV color space
   # blurred = cv2.GaussianBlur(input_img1, (11, 11), 0)
   # hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

   # # masks the blue ball
   # mask = cv2.inRange(hsv, lowerBlue, upperBlue)
   # mask = cv2.erode(mask, None, iterations=2)
   # mask = cv2.dilate(mask, None, iterations=2)

   # _, contour_list1, _ = cv2.findContours(mask.copy(), mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

   # center = 0
   # if len(contour_list1) > 0:
   #    # finds largest contour, masks it, and finds the radius
   #    c = max(contour_list1, key=cv2.contourArea)
   #    ((x,y), radius) = cv2.minEnclosingCircle(c)
   #    M = cv2.moments(c)
   #    center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))


   # turret camera
   timeAH, input_img = sink.grabFrame(img)
   output_img = np.copy(input_img)

   if timeAH == 0: # There is an error
      output.notifyError(sink.getError())
      continue

   grayImage = cv2.cvtColor(input_img, cv2.COLOR_BGR2GRAY)
   thresh, blackAndWhiteImage = cv2.threshold(grayImage, 127, 255, cv2.THRESH_BINARY)

   _, contour_list, _ = cv2.findContours(blackAndWhiteImage, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

   cen = []

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
      
      # add center of contours to list
      center = rect[0]
      cen.append(center)

      # TEXT
      image = cv2.putText(output_img, "{:.2f}".format(ratioArea), (int(rect[0][0]), int(rect[0][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 255, 0), 1, cv2.LINE_AA)
      
      cv2.drawContours(output_img, [cv2.boxPoints(rect).astype(int)], -1, color = (0, 0, 255), thickness = 1)

   # shooter_nt.putNumber("number of contours", len(cen))

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
   
   output.putFrame(blackAndWhiteImage)
   output2.putFrame(output_img)