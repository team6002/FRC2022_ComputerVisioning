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

camera = cs.startAutomaticCapture()
camera.setResolution(160, 120)

sink = cs.getVideo()
output = cs.putVideo("Black and White", 160, 120) 
output2 = cs.putVideo("Contour", 160, 120) 
img = np.zeros(shape=(120, 160, 3), dtype=np.uint8)

print("done")
counter = 450

time.sleep(2)

#filters out everything but rectangles
def is_contour_bad(c):
   #approximates contour
   peri = cv2.arcLength(c, True)
   approx = cv2.approxPolyDP(c, 0.02*peri, True)

   #returns if not a rectangle
   return not len(approx) == 4

def computeYoshi(TUPLE, TPLEU):
   return math.sqrt((TUPLE[0] - TPLEU[0])**2 + (TUPLE[1] - TPLEU[1])**2)

lastYoshi = (0,0)

while True:
   timeAH, input_img = sink.grabFrame(img)
   output_img = np.copy(input_img)

   if timeAH == 0: # There is an error
      output.notifyError(sink.getError())
      continue

   grayImage = cv2.cvtColor(input_img, cv2.COLOR_BGR2GRAY)
   thresh, blackAndWhiteImage = cv2.threshold(grayImage, 200, 255, cv2.THRESH_BINARY)

   _, contour_list, _ = cv2.findContours(blackAndWhiteImage, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

   cen = []
   filteredContours = []
   ratio = []

   mask = np.ones(output_img.shape[:2], dtype="uint8") * 255

   for contour in contour_list:
      if is_contour_bad(contour) == False:
         filteredContours.append(contour)

   for index, contour in enumerate(contour_list):
      rect = cv2.minAreaRect(contour)

      #finding the area of minRect and rectangular contour
      rectArea = rect[1][0] * rect[1][1]
      contourArea = cv2.contourArea(contour)

      #if rectArea = 0, continue to the next contour
      if rectArea == 0:
         continue

      #take ratio of min rect and contour
      ratioArea = contourArea / rectArea

      if counter == 500:
         print("IDEX")
         print(index)
         print("PRINT rectArea")
         print(rectArea)
         print("PRINT contourArea")
         print(contourArea)
         print("PRINT ratio")
         print(ratioArea)


      #TEXT
      image = cv2.putText(output_img, str(index), (int(rect[0][0]), int(rect[0][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1, cv2.LINE_AA)

      #if the ratio is larger than 90%, add contour
      if ratioArea < .90:
         center = rect[0]
         cen.append(center)
      
      cv2.drawContours(output_img, [cv2.boxPoints(rect).astype(int)], -1, color = (0, 0, 255), thickness = 1)
   
   if counter == 500:
      counter = 0
   else:
      counter += 1

   #if there aren't any contours, set x and y to -1
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

      yoshi = computeYoshi(averageCen, lastYoshi)
      if yoshi < 10:
         averageCen = lastYoshi
      else:
         lastYoshi = averageCen
      
      shooter_nt.putNumber('yoshiX', lastYoshi[0])
      shooter_nt.putNumber('yoshiY', lastYoshi[1])
      shooter_nt.putNumber('yoshiyoshi', yoshi)

      #places a crosshair at center
      cv2.drawMarker(output_img, (int(averageCen[0]),int(averageCen[1])), color=(0,255,0), markerType=cv2.MARKER_CROSS, thickness=1)

      #puts number to networktable
      shooter_nt.putNumber('cX', averageCen[0])
      shooter_nt.putNumber('cY', averageCen[1])
   
   output.putFrame(blackAndWhiteImage)
   output2.putFrame(output_img)  