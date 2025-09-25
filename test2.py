import asyncio, time, airsim
from mavsdk import System

# ------- CONFIG -------------------------------------------------------------
AIRSIM_HOST = ""   # Windows host-side address, put your own 
AIRSIM_PORT =            # check with netstat if unsure, put your own 
FOLLOW_OFFSET = 5             # metres behind leader
SIDE_OFFSET   = 4             # metres left/right
# ---------------------------------------------------------------------------

async def connect_leader():
    drone = System()
    await drone.connect(system_address="127.0.0.1:50051")   # MAVSDK-server gRPC
    print("🔌 Connecting to PX4_1 …")
    async for s in drone.core.connection_state():
        if s.is_connected:
            print("✅ PX4_1 connected")
            break
    return drone

def connect_followers():
    print(f"🔌 Connecting to followers on {AIRSIM_HOST}:{AIRSIM_PORT} …")
    client = airsim.MultirotorClient(ip=AIRSIM_HOST, port=AIRSIM_PORT)
    client.confirmConnection()

    for name in ("Drone2", "Drone3"):
        client.enableApiControl(True, vehicle_name=name)
        client.armDisarm(True,    vehicle_name=name)
    print("✅ Drone2 & Drone3 armed and ready")
    return client

async def swarm_follow():
    px4    = await connect_leader()
    client = connect_followers()

    # take-off all aircraft
    await px4.action.arm()
    await px4.action.takeoff()
    client.takeoffAsync(vehicle_name="Drone2").join()
    client.takeoffAsync(vehicle_name="Drone3").join()
    time.sleep(4)

    print("🚁 Formation loop - Ctrl-C to stop")
    try:
        async for pv in px4.telemetry.position_velocity_ned():
            x, y, z = (pv.position.north_m,
                       pv.position.east_m,
                       pv.position.down_m)

            client.moveToPositionAsync(x - FOLLOW_OFFSET,
                                       y + SIDE_OFFSET,  z, 3,
                                       vehicle_name="Drone2")
            client.moveToPositionAsync(x - FOLLOW_OFFSET,
                                       y - SIDE_OFFSET,  z, 3,
                                       vehicle_name="Drone3")
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛬 Landing …")
        await px4.action.land()
        for name in ("Drone2", "Drone3"):
            client.landAsync(vehicle_name=name).join()
            client.armDisarm(False,        vehicle_name=name)
            client.enableApiControl(False, vehicle_name=name)
        print("✅ Done.")

if __name__ == "__main__":
    asyncio.run(swarm_follow())
