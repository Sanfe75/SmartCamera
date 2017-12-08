/**
 *  Computer Vision Room Presence (Device Handler)
 *
 *  Copyright 2017 Simone <sanfe75@gmail.com>
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 */
metadata {
	definition (name: "Smart Camera", namespace: "Sanfe75", author: "Simone") {
		capability "Motion Sensor"
		capability "Sensor"
        capability "Refresh"
        command "subscribe"        
	}

	tiles(scale: 2) {
		multiAttributeTile(name:"motion", type: "generic", width: 6, height: 4){
			tileAttribute ("device.motion", key: "PRIMARY_CONTROL") {
				attributeState "active", label:'motion', icon:"st.motion.motion.active", backgroundColor:"#53a7c0"
				attributeState "inactive", label:'no motion', icon:"st.motion.motion.inactive", backgroundColor:"#ffffff"
			}
		}
		standardTile("refresh", "device.refresh", inactiveLabel: false, decoration: "flat", width: 2, height: 2) {
			state "default", action:"refresh.refresh", icon:"st.secondary.refresh"
		}

        main "motion"
        details (["motion", "refresh"])
	}
    
    preferences {
		input name: "server_PSK", type: "text", title: "PSK Passphrase set on conf.json file", description: "Enter passphrase", required: true, displayDuringSetup: true
        input name: "inactive_delay", type: "number", title: "Delay in seconds before disactivation (1..60)", description: "Delay in seconds", range: "1..60",
        	required: true, displayDuringSetup: true
    }
}

def installed() {

	initialize()
}

def updated() {

	//unsubscribe()
    unschedule()
	initialize()
}

def initialize() {
	log.debug "Executing 'initialize'"
	subscribeAction()
    pushStatusUpdate()
    runEvery3Hours(subscribeAction)
}

// parse events into attributes
def parse(String description) {

    def msg = parseLanMessage(description)
    log.debug "parse Message '${msg}'"
    log.debug "msg.body ${msg.body}"
    def value
    def delay = 1
    if (msg.body == "Motion") {
    	value="active"
    } else if (msg.body == "No motion") {
        value = "inactive"
        delay = inactive_delay? inactive_delay : 1
    }
    log.debug "Value: ${value}"
    runIn(delay, eventCreator, [data:[value: value]])
}

def eventCreator(data) {
    sendEvent(name:"motion", value:data.value)
}

def refresh() {
    log.debug "Executing 'refresh'"
    initialize()    
}

def subscribe() {
    subscribeAction()
}

private subscribeAction(callbackPath="") {

    log.debug "Executing 'subscribeAction'"
    def hubip = device.hub.getDataValue("localIP")
    def hubport = device.hub.getDataValue("localSrvPortTCP")
    def result = new physicalgraph.device.HubAction(
        method: "SUBSCRIBE",
        path: getDataValue("ssdpPath"),
        headers: [
            HOST: getHostAddress(),
            CALLBACK: "<http://${hubip}:${hubport}/notify$callbackPath>",
            NT: "upnp:event",
            TIMEOUT: "Second-28800",
            'X-Auth-PSK': "${server_PSK}"
            ])
    sendHubCommand(result)
}

private pushStatusUpdate() {

	def statusJson = "{\"id\":2,\"method\":\"getStatus\",\"version\":\"1.0\",\"params\":[]}"
    def path='/'

    def result = new physicalgraph.device.HubAction(
        method: 'POST',
        path: "${path}",
        body: statusJson,
        headers: ['HOST':getHostAddress(), 'Content-Type': "application/json", 'X-Auth-PSK':"${server_PSK}"]
        )
    sendHubCommand(result)
}

private getHostAddress() {
    def host = getDataValue("ip") + ":" + getDataValue("port")
    return host
}