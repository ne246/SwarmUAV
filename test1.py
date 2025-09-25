import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udp://127.0.0.1:14540")  # Change IP if needed

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Drone discovered!")
            break

    print("Waiting for global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("✅ Global position estimate OK")
            break

    print("Arming drone...")
    await drone.action.arm()

    print("Taking off...")
    await drone.action.takeoff()
    await asyncio.sleep(15)  # Hover for 5 seconds

    print("Landing...")
    await drone.action.land()

    # Wait until it's landed
    is_in_air = True
    async for in_air in drone.telemetry.in_air():
        is_in_air = in_air
        if not in_air:
            print("✅ Landed!")
            break

    print("Disarming drone...")
    await drone.action.disarm()

asyncio.run(run())
