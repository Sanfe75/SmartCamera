/**
 *  Raspberry Pi - Computer Vision (Connect)
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

definition(
    name: "Smart Camera (Connect)",
    namespace: "Sanfe75",
    author: "Simone",
    description: "Open source Computer Vision Camera using a Computer and a Webcam",
    category: "SmartThings Labs",
    iconUrl: "https://opencv.org/assets/theme/logo.png",
    iconX2Url: "https://opencv.org/assets/theme/logo.png",
    singleInstance: true
)

preferences {
    page(name:"smartCameraDiscovery", title:"Serching for devices...", content:"smartCameraDiscovery")
}

def searchTarget(){
	return "urn:schemas-upnp-org:device:SmartCamera:1"
    }

def smartCameraDiscovery() {

	def options = [:]
    def devices = getVerifiedDevices()
    	devices.each {
		def value = it.value.name ?: "UPnP Device ${it.value.ssdpUSN.split(':')[1][-3..-1]}"
		def key = it.value.mac
		options["${key}"] = "${value} @${convertHexToIP(it?.value?.networkAddress)}"
	}
    
    ssdpSubscribe()
    ssdpDiscover()
    verifyDevices()

	return dynamicPage(name: "smartCameraDiscovery", title: "Discovery Started!", nextPage: "", refreshInterval: 5, install: true, uninstall: true) {
		section("Please wait while we discover your Smart Camera. Discovery can take five minutes or more, so sit back and relax! Select your device below once discovered.") {
			input "selectedDevices", "enum", required: true, title: "Select Devices (${options.size() ?: 0} found)", multiple: true, options: options
		}
    }
}

def installed() {
	log.debug "Installed with settings: ${settings}"

	initialize()
}

def updated() {
	log.debug "Updated with settings: ${settings}"

	unsubscribe()
	initialize()
    
    selectedDevices.each {
    	def child = getChildDevice(it)
        def mac = it
		if (child) {
            def selectedDevice = getDevices().find { mac == it.value.mac}
			child.update(selectedDevice.value.tvPort, selectedDevice.value.tvPSK)
		}
    }
}

def initialize() {

	unschedule()
    
    if (selectedDevices) {
		addDevices()
	}
}

void ssdpDiscover() {
	sendHubCommand(new physicalgraph.device.HubAction("lan discovery ${searchTarget()}", physicalgraph.device.Protocol.LAN))
}

void ssdpSubscribe() {
	subscribe(location, "ssdpTerm.${searchTarget()}", ssdpHandler)
}

Map verifiedDevices() {
	def devices = getVerifiedDevices()
	def map = [:]
	devices.each {
		def value = it.value.name ?: "UPnP Device ${it.value.ssdpUSN.split(':')[1][-3..-1]}"
		def key = it.value.mac
		map["${key}"] = value
	}
	map
}

void verifyDevices() {
	def devices = getDevices().findAll { it?.value?.verified != true }
	devices.each {
		int port = convertHexToInt(it.value.deviceAddress)
		String ip = convertHexToIP(it.value.networkAddress)
		String host = "${ip}:${port}"
		sendHubCommand(new physicalgraph.device.HubAction("""GET ${it.value.ssdpPath} HTTP/1.1\r\nHOST: $host\r\n\r\n""", physicalgraph.device.Protocol.LAN, host, [callback: deviceDescriptionHandler]))
	}
}

def getVerifiedDevices() {
	getDevices().findAll{ it.value.verified == true }
}

def getDevices() {
	if (!state.devices) {
		state.devices = [:]
	}
	state.devices
}

def addDevices() {
	def devices = getDevices()

	selectedDevices.each { dni ->
		def selectedDevice = devices.find { it.value.mac == dni }
		def d
		if (selectedDevice) {
			d = getChildDevices()?.find {
				it.deviceNetworkId == selectedDevice.value.mac
			}
		}

		if (!d) {

			addChildDevice("Sanfe75", "Smart Camera", selectedDevice.value.mac, selectedDevice?.value.hub, [
				"label": selectedDevice.value?.tvName ?: selectedDevice.value.name,
				"data": [
					"ip": convertHexToIP(selectedDevice.value.networkAddress),
                    "port": convertHexToInt(selectedDevice.value.deviceAddress)
				]
			])
		}
	}
}

def ssdpHandler(evt) {

	def description = evt.description
	def hub = evt?.hubId
    def parsedEvent = parseLanMessage(description)
	parsedEvent << ["hub":hub]

	log.debug "ssdpHandler parsedEvent: ${parsedEvent}"
    
	def devices = getDevices()
	String ssdpUSN = parsedEvent.ssdpUSN.toString()
	if (devices."${ssdpUSN}") {
		def d = devices."${ssdpUSN}"
		if (d.networkAddress != parsedEvent.networkAddress || d.deviceAddress != parsedEvent.deviceAddress) {
			d.networkAddress = parsedEvent.networkAddress
			d.deviceAddress = parsedEvent.deviceAddress
			def child = getChildDevice(parsedEvent.mac)
			if (child) {
				child.sync(convertHexToIP(parsedEvent.networkAddress))
			}
		}
	} else {
		devices << ["${ssdpUSN}": parsedEvent]
	}
}

void deviceDescriptionHandler(physicalgraph.device.HubResponse hubResponse) {

	def body = hubResponse.xml
    log.debug "body ${body}"
    body.children().each {
    	log.debug "deviceDescriptionHandler children: ${it.name()} --> ${it.text()}"
    }  
    body.device.children().each {
    	log.debug "deviceDescriptionHandler device.children: ${it.name()} --> ${it.text()}"
    }    
    
	def devices = getDevices()
	def device = devices.find { it?.key?.contains(body?.device?.UDN?.text()) }
	if (device) {
		device.value << [name: body?.device?.friendlyName?.text(), model:body?.device?.modelName?.text(), serialNumber:body?.device?.serialNum?.text(), verified: true]
	}
}

private Integer convertHexToInt(hex) {
	Integer.parseInt(hex,16)
}

private String convertHexToIP(hex) {
	[convertHexToInt(hex[0..1]),convertHexToInt(hex[2..3]),convertHexToInt(hex[4..5]),convertHexToInt(hex[6..7])].join(".")
}