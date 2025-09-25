import asyncio
from tkinter import *
from turtle import home
from async_tkinter_loop import async_handler, async_mainloop
from mavsdk import *
from mavsdk import System
from mavsdk.offboard import (OffboardError, VelocityBodyYawspeed)
import time
import webbrowser

drone = System()
lastPacketTime=time.time()-10

# Keyboard control variables
keyboard_control_active = False
movement_speed = 2.0  # meters per second
altitude_speed = 1.0  # meters per second for vertical movement

# Movement state
move_forward = False
move_backward = False
move_left = False
move_right = False
move_up = False
move_down = False

def hyperLink(url):
    webbrowser.open_new(url)

async def setup():
    """
    General configurations, setups, and connections are done here.
    :return:
    """

    await drone.connect(system_address="udp://127.0.0.1:14540")

    printPxh("Waiting for drone to connect...")
    global state
    global lastPacketTime
    global health

    async for state in drone.core.connection_state():
        lastPacketTime=time.time()
        if state.is_connected:
            printPxh(f"-- Connected to drone!")
            break

    
    asyncio.ensure_future(checkTelem())
    asyncio.ensure_future(print_health(drone))
    asyncio.ensure_future(print_position(drone))

    
    printPxh("Waiting for drone to have a global position estimate...")
    
    while True:
        await print_health(drone)
        if health.is_global_position_ok and health.is_home_position_ok:
            printPxh("-- Global position estimate OK")
            break

async def toggle_keyboard_control():
    """Toggle keyboard control mode on/off"""
    global keyboard_control_active
    
    if not keyboard_control_active:
        # Enable keyboard control
        try:
            printPxh("-- Starting offboard mode for keyboard control")
            # Start with zero velocity
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
            await drone.offboard.start()
            
            keyboard_control_active = True
            keyboardControlBtn.config(text="Stop Keyboard Control", bg="red")
            printPxh("-- Keyboard control ACTIVE")
            printPxh("-- Click on control buttons or use keyboard")
            
            # Start the keyboard control loop
            asyncio.ensure_future(keyboard_control_loop())
            
        except OffboardError as error:
            printPxh(f"Starting offboard mode failed with error: {error}")
            keyboard_control_active = False
    else:
        # Disable keyboard control
        try:
            # Stop with zero velocity
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0.0, 0.0, 0.0, 0.0))
            await drone.offboard.stop()
            keyboard_control_active = False
            reset_movement_state()
            keyboardControlBtn.config(text="Enable Keyboard Control", bg="lightgray")
            printPxh("-- Keyboard control DISABLED")
        except OffboardError as error:
            printPxh(f"Stopping offboard mode failed with error: {error}")

def reset_movement_state():
    """Reset all movement flags to False"""
    global move_forward, move_backward, move_left, move_right, move_up, move_down
    move_forward = move_backward = move_left = move_right = move_up = move_down = False

async def keyboard_control_loop():
    """Main loop for keyboard control - sends velocity commands"""
    global keyboard_control_active
    
    while keyboard_control_active:
        try:
            # Calculate velocity based on movement state
            forward_vel = 0.0
            right_vel = 0.0
            down_vel = 0.0
            yaw_rate = 0.0
            
            if move_forward:
                forward_vel = movement_speed
            elif move_backward:
                forward_vel = -movement_speed
                
            if move_right:
                right_vel = movement_speed
            elif move_left:
                right_vel = -movement_speed
                
            if move_up:
                down_vel = -altitude_speed
            elif move_down:
                down_vel = altitude_speed
            
            # Send velocity command
            await drone.offboard.set_velocity_body(
                VelocityBodyYawspeed(forward_vel, right_vel, down_vel, yaw_rate)
            )
            
        except OffboardError as error:
            printPxh(f"Keyboard control error: {error}")
            break
        
        await asyncio.sleep(0.1)  # 10Hz update rate

# Button control functions
def start_move_forward():
    global move_forward
    if keyboard_control_active:
        move_forward = True
        printPxh("Moving FORWARD")

def stop_move_forward():
    global move_forward
    move_forward = False
    printPxh("Stop FORWARD")

def start_move_backward():
    global move_backward
    if keyboard_control_active:
        move_backward = True
        printPxh("Moving BACKWARD")

def stop_move_backward():
    global move_backward
    move_backward = False
    printPxh("Stop BACKWARD")

def start_move_left():
    global move_left
    if keyboard_control_active:
        move_left = True
        printPxh("Moving LEFT")

def stop_move_left():
    global move_left
    move_left = False
    printPxh("Stop LEFT")

def start_move_right():
    global move_right
    if keyboard_control_active:
        move_right = True
        printPxh("Moving RIGHT")

def stop_move_right():
    global move_right
    move_right = False
    printPxh("Stop RIGHT")

def start_move_up():
    global move_up
    if keyboard_control_active:
        move_up = True
        printPxh("Moving UP")

def stop_move_up():
    global move_up
    move_up = False
    printPxh("Stop UP")

def start_move_down():
    global move_down
    if keyboard_control_active:
        move_down = True
        printPxh("Moving DOWN")

def stop_move_down():
    global move_down
    move_down = False
    printPxh("Stop DOWN")

# Keyboard event handlers
def on_key_press(event):
    """Handle key press events"""
    if not keyboard_control_active:
        return
    
    key = event.keysym.lower()
    
    if key == 'g' and not move_forward:
        start_move_forward()
    elif key == 'j' and not move_backward:
        start_move_backward()
    elif key == 'y' and not move_left:
        start_move_left()
    elif key == 'h' and not move_right:
        start_move_right()
    elif key == 'space' and not move_up:
        start_move_up()
    elif key in ['shift_l', 'shift_r'] and not move_down:
        start_move_down()

def on_key_release(event):
    """Handle key release events"""
    if not keyboard_control_active:
        return
        
    key = event.keysym.lower()
    
    if key == 'g':
        stop_move_forward()
    elif key == 'j':
        stop_move_backward()
    elif key == 'y':
        stop_move_left()
    elif key == 'h':
        stop_move_right()
    elif key == 'space':
        stop_move_up()
    elif key in ['shift_l', 'shift_r']:
        stop_move_down()

        
async def checkTelem():
    global lastPacketTime 
    while True:
        if (time.time() - lastPacketTime) > 1 :
            linkTextObj.config(fg="red")
        else:
            linkTextObj.config(fg="green")
        await asyncio.sleep(3)

async def disarm():
    printPxh("DisArming...")
    await drone.action.disarm()
    
async def shutdown():
    printPxh("Shutting Down the Drone")
    await drone.action.shutdown()
 
async def testArm():
    printPxh("-- Arming")
    await drone.action.arm()           
    await asyncio.sleep(5)
    printPxh("-- DisArming")
    await drone.action.disarm()
    
async def takeoff(alt=10):
    printPxh("-- Initializing")
    printPxh("-- Arming")
    await drone.action.arm()
    printPxh("-- Taking off")
    await drone.action.set_takeoff_altitude(int(altIn.get()))
    await drone.action.takeoff()

async def land():
    printPxh("-- Landing")
    # Stop keyboard control before landing
    if keyboard_control_active:
        await toggle_keyboard_control()
    altIn.delete(0,END)
    altIn.insert(0,0)
    await drone.action.land()

def printPxh(msg=""):
    pxhOut.insert(END, msg + '\n')
    print(msg)
    pxhOut.see("end")

async def print_health(drone):
        defColor = portLabelObj.cget("fg")
        async for health in drone.telemetry.health():
            if health.is_gyrometer_calibration_ok & health.is_accelerometer_calibration_ok & health.is_magnetometer_calibration_ok :
               ahrsTextObj.config(fg="green") 
               
            if health.is_local_position_ok & health.is_global_position_ok & health.is_home_position_ok :
               posTextObj.config(fg="green") 
        
            if health.is_armable:
               armTextObj.config(fg="green") 
            global lastPacketTime   
            lastPacketTime=time.time()

async def print_position(drone):
    global position
    async for position in drone.telemetry.position():
        altText.delete(1.0,"end")
        altText.insert(1.0, str(round(position.relative_altitude_m,1)) + " for "+altIn.get()+" m")
        global lastPacketTime 
        lastPacketTime=time.time()

# GUI Setup
root = Tk()
root.geometry("800x750")
root.title("PX4 MAVSDK GUI Example with Keyboard Control")

# Bind keyboard events
root.bind('<KeyPress>', on_key_press)
root.bind('<KeyRelease>', on_key_release)
root.focus_set()

labelPortText=StringVar()
labelPortText.set("Receiving Port: ")
portLabelObj=Label(root, textvariable=labelPortText, height=4)
portLabelObj.grid(row=1,column=1,rowspan=1,columnspan=1)

defPort = StringVar(root, value='14540')
portIn = Entry(root, textvariable=defPort)
portIn.grid(row=1,column=2,rowspan=1,columnspan=1)

Button(root, text="Connect", command=async_handler(setup)).grid(row=1,column=3,rowspan=1)

posTextStr=StringVar()
posTextStr.set("NAV")
posTextObj=Label(root, textvariable=posTextStr, height=1)
posTextObj.grid(row=2,column=1,rowspan=1,columnspan=1)
posTextObj.config(fg= "red")

ahrsTextStr=StringVar()
ahrsTextStr.set("AHRS")
ahrsTextObj=Label(root, textvariable=ahrsTextStr, height=1)
ahrsTextObj.grid(row=2,column=2,rowspan=1,columnspan=1)
ahrsTextObj.config(fg= "red")

linkTextStr=StringVar()
linkTextStr.set("LINK")
linkTextObj=Label(root, textvariable=linkTextStr, height=1)
linkTextObj.grid(row=3,column=1,rowspan=1,columnspan=1)
linkTextObj.config(fg= "red")

armTextStr=StringVar()
armTextStr.set("READY")
armTextObj=Label(root, textvariable=armTextStr, height=1)
armTextObj.grid(row=3,column=2,rowspan=1,columnspan=1)
armTextObj.config(fg= "red")

labelAltInText=StringVar()
labelAltInText.set("Desired Altitude: ")
labelAltInObj=Label(root, textvariable=labelAltInText, height=4)
labelAltInObj.grid(row=2,column=3,rowspan=1,columnspan=1)

defAlt = StringVar(root, value='5')
altIn = Entry(root, textvariable=defAlt)
altIn.grid(row=2,column=4,rowspan=1,columnspan=1)

Button(root, text="Take-Off", command=async_handler(takeoff),width=30).grid(row=3,column=3,rowspan=1,columnspan=2)

# Keyboard Control Button
keyboardControlBtn = Button(root, text="Enable Keyboard Control", 
                           command=async_handler(toggle_keyboard_control), 
                           width=30, bg="lightgray")
keyboardControlBtn.grid(row=4,column=3,rowspan=1,columnspan=2)

# Control Instructions
controlInstructions = Label(root, text="Keyboard: Y(←) G(↑) H(→) J(↓) SPACE(⬆) SHIFT(⬇)", 
                           fg="blue", font=("Arial", 9))
controlInstructions.grid(row=5,column=1,columnspan=4)

# Manual Control Buttons
control_frame = Frame(root)
control_frame.grid(row=6, column=1, columnspan=4, pady=10)

# Up/Down buttons
Button(control_frame, text="▲ UP", width=8, 
       command=lambda: (start_move_up() if not move_up else stop_move_up())).grid(row=0, column=1)

# Left/Right/Forward/Backward buttons  
Button(control_frame, text="← LEFT", width=8,
       command=lambda: (start_move_left() if not move_left else stop_move_left())).grid(row=1, column=0)

Button(control_frame, text="↑ FORWARD", width=8,
       command=lambda: (start_move_forward() if not move_forward else stop_move_forward())).grid(row=1, column=1)

Button(control_frame, text="→ RIGHT", width=8,
       command=lambda: (start_move_right() if not move_right else stop_move_right())).grid(row=1, column=2)

Button(control_frame, text="↓ BACKWARD", width=8,
       command=lambda: (start_move_backward() if not move_backward else stop_move_backward())).grid(row=2, column=1)

Button(control_frame, text="▼ DOWN", width=8,
       command=lambda: (start_move_down() if not move_down else stop_move_down())).grid(row=3, column=1)

# STOP ALL button
Button(control_frame, text="STOP ALL", width=15, bg="red", fg="white",
       command=reset_movement_state).grid(row=4, column=0, columnspan=3, pady=5)

Button(root, text="Land Current Position", command=async_handler(land),width=30).grid(row=8,column=3,columnspan=2)

labelAltText=StringVar()
labelAltText.set("Altitude AGL ")
altLabel=Label(root, textvariable=labelAltText, height=4)
altLabel.grid(row=8,column=1,rowspan=1)

altText = Text(root, height=2, width=30)
altText.grid(row=8,column=2,rowspan=1)
altText.insert(END,"0 for 0 m")

pxhOut = Text(
    root,
    height=15,
    width=100
)
pxhOut.grid(row=12,column=1,columnspan=4)
pxhOut.insert(END,"Drone state will be shown here..."+ '\n')

linkFooter = StringVar()
linkFooter.set("Alireza Ghaderi - GitHub: Alireza787b")

footerLink = Label( root, fg="green", cursor="hand2" ,textvariable=linkFooter )
footerLink.bind("<Button-1>", lambda e: hyperLink("https://github.com/alireza787b/mavsdk-gui-example"))
footerLink.grid(row=17,column=0,columnspan=20)

async_mainloop(root)