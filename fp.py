# color_tracking_v1.py
# usb camera: Microsoft HD-3000 target: orange basketball
# This program was designed to have SCUTTLE following a basketball.
# The calibration was made in a brightly lit indoor environment.
# Video demo: https://youtu.be/9t1XHcomlIs
# color Tracking
print("loading libraries for color tracking...")
import argparse         # For fetching user arguments
import numpy as np      # Kernel
import os                                           # for making commands directly to the OS
import time                                         # only required if we run this program  in a loop
import L1_gamepad as gamepad                        # allows us to read all inputs from gamepad
import L2_log as log                                # log live data to local files
import L1_adc as bat                                #import battery status  
import cv2              # For image capture and processing

print("loading rcpy.")
import rcpy                 # Import rcpy library
import rcpy.motor as motor  # Import rcpy motor module
print("finished loading libraries.")
#    Camera

camera_input = 0        # Define camera input. Default=0. 0=/dev/video0

size_w  = 240   # Resized image width. This is the image width in pixels.
size_h = 160	# Resized image height. This is the image height in pixels.

#    Color Range, described in HSV

v1_min = 90     # Minimum H value
v2_min = 90     # Minimum S value
v3_min = 80    # Minimum V value

v1_max = 120     # Maximum H value
v2_max = 255    # Maximum S value
v3_max = 255    # Maximum V value

#    RGB or HSV

filter = 'HSV'  # Use HSV to describe pixel color values

def main():

    camera = cv2.VideoCapture(camera_input)     # Define camera variable
    camera.set(3, size_w)                       # Set width of images that will be retrived from camera
    camera.set(4, size_h)                       # Set height of images that will be retrived from camera

    tc = 70     # Too Close     - Maximum pixel size of object to track
    tf = 6      # Too Far       - Minimum pixel size of object to track
    tp = 65     # Target Pixels - Target size of object to track

    band = 40   #range of x considered to be centered

    x = 0  # will describe target location left to right
    y = 0  # will describe target location bottom to top

    radius = 0  # estimates the radius of the detected target
    duty = 0
    duty_l = 0 # initialize motor with zero duty cycle
    duty_r = 0 # initialize motor with zero duty cycle

    print("initializing rcpy...")
    rcpy.set_state(rcpy.RUNNING)        # initialize rcpy
    print("finished initializing rcpy.")
    
    p = 0           #Boolean to stop until ___
    reloading = 0
    button = 0
    shooting = 0
    
    scale_t = .8	# a scaling factor for speeds
    scale_d = .8	# a scaling factor for speeds

    motor_S = 3 	# Trigger Motor assigned to #3
    motor_r = 2 	# Right Motor assigned to #2
    motor_l = 1 	# Left Motor assigned to #1
    state = 1
    battery = 0
    shots = 0
    integrate = 0
    ki = 0.001
    error = 0
    
    try:
        while p != 1:
            p = gamepad.getGP()
            p = p[7]
            print("waiting for input")
        while rcpy.get_state() != rcpy.EXITING:
            if  p == 1:
                print(state)
                
                battery = bat.getDcJack()
                log.tmpFile(state,"state.txt")         #States
                log.tmpFile(shots,"shots.txt")         #Shots left
                log.tmpFile(radius,"radius.txt")         #radius (distance from tartget)
                log.tmpFile(battery,"battery.txt")         #battery voltage
                log.tmpFile(duty_l,"dcL.txt")         #motor duty cycle L
                log.tmpFile(duty_r,"dcR.txt")         #motor duty cycle R
                
                if rcpy.get_state() == rcpy.RUNNING:
                    
                    #Camera code
                    
                    ret, image = camera.read()  # Get image from camera
    
                    height, width, channels = image.shape   # Get size of image
    
                    if not ret:
                        break
    
                    if filter == 'RGB':                     # If image mode is RGB switch to RGB mode
                        frame_to_thresh = image.copy()
                    else:
                        frame_to_thresh = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)    # Otherwise continue reading in HSV
    
                    thresh = cv2.inRange(frame_to_thresh, (v1_min, v2_min, v3_min), (v1_max, v2_max, v3_max))   # Find all pixels in color range
    
                    kernel = np.ones((5,5),np.uint8)                            # Set gaussian blur strength.
                    mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)     # Apply gaussian blur
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
                    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[-2]     # Find closed shapes in image
                    center = None   # Create variable to store point
    
                    #End of camera code
                    
                    
                    
                    if state == 1 and len(cnts) > 0:   # If more than 0 closed shapes exist
                        state = 2
                        
                    if state == 2 and len(cnts) == 0:
                        state = 1
                        
                    if shooting == 1 and state == 2:
                        state = 3
                        
                    if state == 3 and reloading == 1:
                        state = 4
                        
                    if state == 4 and button == 1:
                        state = 1
                    
                    if state == 1:
                        #case = "turning"
                        duty_l = 1
                        duty_r = -1
                        integrate = 0
                    
                    if state == 2 and len(cnts) > 0:
                        #Case = Target Aquesition
                        c = max(cnts, key=cv2.contourArea)              # Get the properties of the largest circle
                        ((x, y), radius) = cv2.minEnclosingCircle(c)    # Get properties of circle around shape
    
                        radius = round(radius, 2)   # Round radius value to 2 decimals
                        print(radius)
                        x = int(x)          # Cast x value to an integer
                        M = cv2.moments(c)  # Gets area of circle contour
                        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))   # Get center x,y value of circle

                        # handle centered condition
                        if x > ((width/2)-(band/2)) and x < ((width/2)+(band/2)):       # If center point is centered
                            if radius > 38:    # Too Close
    
                                #case = "too close"
                                case = "Back Up"
    
                                duty = -1.2
                                print("too close")
                                shooting = 0
                                duty_l = duty
                                duty_r = duty
                                
                            elif radius >= 34 and radius <= 38:
                                case = "On target"
                                duty = 0
                                shooting = 1
                                print("on target")
                                duty_l = duty
                                duty_r = duty
    
                            elif radius < 34:   # Too Far
    
                                case = "Bruh where it at"
    
                                duty = 1.2
                                duty = scale_d * duty
                                print("too far")
                                shooting = 0
                                duty_l = duty
                                duty_r = duty
                                
                        else:
                            #case = "turning"
                            case = "Looking For Target"
                            print(x)
                            """
                            if x>50:
                                duty_l = .2
                                duty_r = -.2
                            elif x<50:
                                duty_l = -.2
                                duty_r = .2"""
                            
                            error = 50 - x
                            integrate =integrate + error
                            
                            duty_l = round((x-0.5*width)/(0.5*width) + ki*integrate,2)     # Duty Left
                                #duty_l = duty_l*scale_t
        
                            #duty_r = round((0.5*width-x)/(0.5*width),2)     # Duty Right
                                #duty_r = duty_r*scale_t
                            print("turning")
                            shooting = 0
                                

                        print(duty_l)
                    
                    if state == 3:
                        #State = Shooting
                        motor.set(motor_l, 0)
                        motor.set(motor_r, 0)                        
                        print("Getting ready to shoot")
                        motor.set(motor_S, -.45)
                        time.sleep(.3)
                        motor.set(motor_S, .45)
                        time.sleep(.3)
                        motor.set(motor_S, 0)
                        print("Gotcha Bitch")
                        reloading = 1
                        button = 0

                    
                    if state == 4:
                        reloading = 0
                        print("Waiting for reload, press A when done")
                        button = gamepad.getGP()
                        button = button[4]
                        duty_l = 0
                        duty_r = 0
                        shots = shots + 1
 
                        
                                     # Keep duty cycle within range
    
                    if duty_r > 1:
                        duty_r = 1
        
                    elif duty_r < -1:
                        duty_r = -1
        
                    if duty_l > 1:
                        duty_l = 1
        
                    elif duty_l < -1:
                        duty_l = -1
        
                    duty_l = duty_l*scale_t
                    duty_r = duty_r*scale_t
                    
                    # Round duty cycles
                    duty_l = round(duty_l,2)
                    duty_r = round(duty_r,2)
                    print(duty_l)
                    print(duty_r)
        
                    # Set motor duty cycles
                    motor.set(motor_l, duty_l)
                    motor.set(motor_r, duty_r)                   

                elif rcpy.get_state() == rcpy.PAUSED:
                    pass

    except KeyboardInterrupt: # condition added to catch a "Ctrl-C" event and exit cleanly
        rcpy.set_state(rcpy.EXITING)
        pass

    finally:

    	rcpy.set_state(rcpy.EXITING)
    	print("Exiting Color Tracking.")

# exiting program will automatically clean up cape

if __name__ == '__main__':
    main()