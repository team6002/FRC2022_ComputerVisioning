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

camera = cs.startAutomaticCapture()
camera.setResolution(160, 120)

sink = cs.getVideo()
output = cs.putVideo("Black and White", 160, 120) 
output2 = cs.putVideo("Contour", 160, 120) 
img = np.zeros(shape=(120, 160, 3), dtype=np.uint8)

print("done")
counter = 0 

time.sleep(2)

while True:
   timeAH, input_img = sink.grabFrame(img)
   output_img = np.copy(input_img)

   if timeAH == 0: # There is an error
      output.notifyError(sink.getError())
      continue

   grayImage = cv2.cvtColor(input_img, cv2.COLOR_BGR2GRAY)
   thresh, blackAndWhiteImage = cv2.threshold(grayImage, 127, 255, cv2.THRESH_BINARY)

   _, contour_list, _ = cv2.findContours(blackAndWhiteImage, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

   cen = []
   area = []

   for contour in contour_list:
      rect = cv2.minAreaRect(contour)
      # area.append(rect[1][0] * rect[1][1])

      #if the rectangle is within a certain size, display it and add it's center
      if rect[1][0] * rect[1][1] < 20:
         center = rect[0]
         cen.append(center)

         cv2.drawContours(output_img, [cv2.boxPoints(rect).astype(int)], -1, color = (0, 0, 255), thickness = 1)

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

      #places a crosshair at center
      cv2.drawMarker(output_img, (int(averageCen[0]),int(averageCen[1])), color=(0,255,0), markerType=cv2.MARKER_CROSS, thickness=1)

      #puts number to networktable
      shooter_nt.putNumber('cX', averageCen[0])
      shooter_nt.putNumber('cY', averageCen[1])
   
   output.putFrame(blackAndWhiteImage)
   output2.putFrame(output_img)

   # if counter == 20:
   #    print("printing area: ")
   #    print(area)
   #    counter = 0
   # else:
   #    counter += 1