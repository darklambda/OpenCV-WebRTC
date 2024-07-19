#!/usr/bin/env python

import asyncio
import json
import os
import signal

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaRelay
from dotenv import load_dotenv
from websockets import server, WebSocketServerProtocol, ConnectionClosedOK
from os.path import join, dirname

from VideoTransform.transform import VideoTransformTrack

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

connections: list[WebSocketServerProtocol] = list()

MAX_CONNECTIONS = 3

relay = MediaRelay()

peerCreated = False

async def create_peer(request: dict, websocket: WebSocketServerProtocol):
    global peerCreated
    peerCreated = True

    print("-"*70)
    if "X-Forwarded-For" in websocket.request_headers.keys():
        print("Creating Peer for {0}".format(str(websocket.request_headers["X-Forwarded-For"])))
    else:
        print("Creating Peer for {0}".format(str(websocket.remote_address[0])))

    print("Creating Offer")
    offer = RTCSessionDescription(sdp=request["sdp"], type=request["type"])

    ice_servers = [
        RTCIceServer(urls = os.environ.get('STUN_SV_URL')),  # Google's public STUN server
        #RTCIceServer(urls = os.environ.get('TURN_SV_URL'),
        #             username = os.environ.get('TURN_SV_USER'),
        #             credential = os.environ.get('TURN_SV_PASSWORD'))
    ]

    print("Creating RTC Peer")
    pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        global peerCreated
        print("Connection state is {0}.".format(str(pc.connectionState)))
        if pc.connectionState == "failed":
            print("Connection Stats".center(70, "-"))
            stats = await pc.getStats()
            print(stats)
            await pc.close()
            print("-"*70)
            peerCreated = False
        elif pc.connectionState == "closed":
            peerCreated = False

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print("ICE Connection state is {0}.".format(str(pc.iceConnectionState)))


    @pc.on("icegatheringstatechange")
    async def on_icegatheringstatechange():
        print("ICE Gathering state is {0}.".format(str(pc.iceGatheringState)))

    @pc.on("track")
    def on_track(track):
        print("Track {0} received".format(str(track.kind)))

        if track.kind == "video":
            pc.addTrack(
                VideoTransformTrack(
                    relay.subscribe(track), transform=request["video_transform"]
                )
            )

        @track.on("ended")
        async def on_ended():
            await pc.close()
            print("Track {0} ended, closing connection.".format(str(track.kind)))
            print("-"*70)

    print("Setting Remote Description")
    await pc.setRemoteDescription(offer)

    print("Creating Answer")
    answer = await pc.createAnswer()
    print("Setting Local Description")
    try:
        await pc.setLocalDescription(answer)
    except Exception as error:
        print(error)
        pass
    await websocket.send(json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ))
    await websocket.close(reason='WebRTC Connection Successfull')


async def connection_handler(websocket: WebSocketServerProtocol):
    global peerCreated
    if len(connections) >= MAX_CONNECTIONS:
        await websocket.close(reason='Maximum Websocket Connection Reached')
    connections.append(websocket)
    try:
        while True:
            index = connections.index(websocket)
            if (index == 0) and (not peerCreated):
                await websocket.send("2-")
                rqs = await websocket.recv()
                rqs = json.loads(rqs)
                await create_peer(rqs, websocket)
            else:
                await websocket.send("1-" + str(index))
                await asyncio.sleep(1)
    except ConnectionClosedOK:
        connections.remove(websocket)
    except Exception as error:
        print(error)
        connections.remove(websocket)

async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with server.serve(connection_handler, "0.0.0.0", 8764, close_timeout=1.0):
        print("Starting Websocket Server on port 8764")
        await stop


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Server Closed")