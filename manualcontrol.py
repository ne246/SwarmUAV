import airsim
import keyboard
import time

def connect_drone():
    print("Connecting to AirSim...")
    client = airsim.MultirotorClient()
    
    try:
        client.confirmConnection()
        print("Connected to AirSim!")
        
        # Wait a moment for vehicle to be ready
        time.sleep(2)
        
        # Check if we can get vehicle state
        state = client.getMultirotorState()
        print(f"Vehicle position: {state.kinematics_estimated.position}")
        
        print("Enabling API control...")
        client.enableApiControl(True)
        
        print("Arming drone...")
        client.armDisarm(True)
        
        return client
        
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure AirSim is running")
        print("2. Select 'Multirotor' when AirSim starts")
        print("3. Wait for the environment to fully load")
        print("4. Make sure you see a drone in the 3D view")
        return None

def main():
    # Connect to drone
    client = connect_drone()
    if not client:
        return
    
    try:
        print("Taking off...")
        client.takeoffAsync().join()
        print("Takeoff complete!")
        
        # Control parameters
        velocity = 3  # m/s (reduced for better control)
        duration = 0.1
        
        print("\nDrone control ready!")
        print("Controls:")
        print("Y - Forward")
        print("G - Left") 
        print("H - Backward")
        print("J - Right")
        print("Space - Up")
        print("Shift - Down")
        print("Q - Quit and land")
        print("\nPress keys to control the drone...")
        
        while True:
            moved = False
            
            if keyboard.is_pressed('y'):
                client.moveByVelocityAsync(velocity, 0, 0, duration)
                moved = True
            elif keyboard.is_pressed('h'):
                client.moveByVelocityAsync(-velocity, 0, 0, duration)
                moved = True
            elif keyboard.is_pressed('g'):
                client.moveByVelocityAsync(0, -velocity, 0, duration)
                moved = True
            elif keyboard.is_pressed('j'):
                client.moveByVelocityAsync(0, velocity, 0, duration)
                moved = True
            elif keyboard.is_pressed('space'):
                client.moveByVelocityAsync(0, 0, -velocity, duration)
                moved = True
            elif keyboard.is_pressed('shift'):
                client.moveByVelocityAsync(0, 0, velocity, duration)
                moved = True
            elif keyboard.is_pressed('q'):
                print("Landing...")
                break
            
            # If no movement, hover in place
            if not moved:
                client.moveByVelocityAsync(0, 0, 0, duration)
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    except Exception as e:
        print(f"Error during flight: {e}")
    
    finally:
        print("Landing drone...")
        try:
            client.landAsync().join()
            client.armDisarm(False)
            client.enableApiControl(False)
            print("Drone landed and disconnected.")
        except:
            print("Error during landing, but drone should be safe.")

if __name__ == "__main__":
    print("Make sure to run as administrator for keyboard detection!")
    main()
