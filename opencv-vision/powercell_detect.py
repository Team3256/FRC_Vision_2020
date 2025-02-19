from imutils.video import VideoStream
import numpy as np
import argparse
import cv2
import imutils
import time
import constants

from networktables import NetworkTables

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video",
	help="path to the (optional) video file")
args = vars(ap.parse_args())

# NetworkTables

NetworkTables.initialize(server=constants.SERVER_IP)
sd = NetworkTables.getTable("SmartDashboard")

# define the lower and upper boundaries of the yellow powercell in the HSV color
# scheme, then initialize the list of tracked points
yellowLower = constants.LOWER_YELLOW
yellowUpper = constants.UPPER_YELLOW
# if a video path was not supplied, grab the reference
# to the webcam
if not args.get("video", False):
	vs = VideoStream(src=0).start()
# otherwise, grab a reference to the video file
else:
	vs = cv2.VideoCapture(args["video"])
# allow the camera or video file to warm up
time.sleep(2.0)

def getAngle(px):
    nx = (1.0/300.0) * (px - 299.5)
    vpw = 2* np.tan(constants.FIELD_OF_VIEW_X/2)
    x = vpw/2 * nx
    theta = np.arctan2(1,x) * (180/np.pi)
    return -(theta - 90)

# keep looping
while True:
	# grab the current frame
	frame = vs.read()
	# handle the frame from VideoCapture or VideoStream
	frame = frame[1] if args.get("video", False) else frame
	# if we are viewing a video and we did not grab a frame,
	# then we have reached the end of the video
	if frame is None:
		break
	# resize the frame, blur it, and convert it to the HSV color space
	frame = imutils.resize(frame, width=constants.FRAME_WIDTH)
	blurred = cv2.GaussianBlur(frame, (11, 11), 0)
	hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
	# construct a mask for the color yellow, then perform
	# a series of dilations and erosions to remove any small
	# blobs left in the mask
	mask = cv2.inRange(hsv, yellowLower, yellowUpper)
	mask = cv2.erode(mask, None, iterations=2)
	mask = cv2.dilate(mask, None, iterations=2)

    # find contours in the mask and initialize the current (x, y) center
	# of the ball
	cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)
	cnts = imutils.grab_contours(cnts)
	center = None
	# only proceed if at least one contour was found
	if len(cnts) > 0:
		# find the largest contour in the mask, then use
		# it to compute the minimum enclosing circle and
		# centroid
		c = max(cnts, key=cv2.contourArea)
		((x, y), radius) = cv2.minEnclosingCircle(c)
		M = cv2.moments(c)
		center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
		# only proceed if the radius meets a minimum size
		if radius > constants.MIN_CIRCLE_RADIUS:
			# draw the circle and centroid on the frame,
			# then update the list of tracked points
			cv2.circle(frame, (int(x), int(y)), int(radius),
				(0, 0, 255), 2)
			cv2.circle(frame, center, 5, (0, 0, 255), -1)
			x_angle = getAngle(center[0])
			sd.putNumber("visionHorizontalAngle", x_angle)
			cv2.putText(frame, 'Angle: ' + str(x_angle), (5, 80), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
			cv2.putText(frame, 'Center: ' + str(center), (5, 32), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
	# if the 'q' key is pressed, stop the loop
	if key == ord("q"):
		break
# if we are not using a video file, stop the camera video stream
if not args.get("video", False):
	vs.stop()
# otherwise, release the camera
else:
	vs.release()
# close all windows
cv2.destroyAllWindows()
