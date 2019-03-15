# Dandelion
![alt text](https://img.shields.io/badge/aiohttp-2.2.0-orange.svg)
![alt text](https://img.shields.io/badge/python-3.6-blue.svg)
![alt text](https://img.shields.io/badge/coverage-57%25-green.svg)
![alt text](https://img.shields.io/dub/l/vibe-d.svg)


## Introduction
Dandelion platform aims to optimize bandwidth usage by re-allocating idle bandwidth in households for other purposes, 
such as live streaming. The platform comprises an entrance server, a plurality of boxes, and a plurality of publishers. 

Boxes are microprocessors that are distributed among households and collect any unused bandwidth. The location and 
system information of each box is recorded onto the entrance server's database. All recorded boxes periodically
send pertinent information, such as measured bandwidth, available memory space and GEOIP info, etc., to the 
entrance server. If the entrance server does not receive any updates from a box after some given time, the entrance 
server will remove that box from its database.

To explain the function of the publisher, it is apposite to take live streaming as an example. Every caster has a 
publisher installed in his or her local machine. The publisher will then ask the entrance server for a list of proper 
boxes and make connection to each of them. After this process, the publisher is ready to do its real job - 
publishing files to boxes. The publisher randomly selects a box as a target to store a specific file or a segment 
of the live streaming and record this action to the publisher's database, which will be queried later to search for the location
of the file. When a viewer tries to access the web page of the caster's live streaming, the web server will query
the caster's publisher, return these locations back to the viewer's browser and redirect the browser to the 
box to get the file. 

In sum, it is clear to see that by making full use of the idle bandwidth in each household via the box, the web server has saved its network traffic, which is the main 
purpose of this project because the amount of the network traffic is proportional to the cost of data transfer.


## Graph
![Screenshot](screenshot.png)

## Before Start
### Make sure that python's version is higher than 3.5 and run command below
```
sudo pip3 install -r requirements.txt
python3 setup.py install
```
### Other required Installation (without using docker)
- Redis
- Nginx (as a proxy server)

## Get started
- Duplicate the config.yaml.example file and rename it to config.yaml(entrance-config.yaml for entrance server). Please configure the settings in the file properly according to your character (Entrance server, box and publisher).

- Box Config
```
cp config.yaml.example config.yaml
```
   - Publisher Config
```
cp config.yaml.example config.yaml
```
   - Entrance Config
```
cp config.yaml.example entrance-config.yaml
```
- Run
```
python3 run_box.py
python3 run_entrance.py
python3 run_publisher.py
```

- You can also fire up by docker, which is much easier.
```
sudo docker-compose -f <compose-filename> build
sudo docker-compose -f <compose-filename> up 
```

## Testing
##### Run all test cases
```
python3 -m unittest
```
##### Coverage
```
coverage run -m unittest
coverage report
```

## Developer Document
### Point to Point Exchange Info format
##### Box to Entrance (EXCHANGE REQUEST)
- ID
- IP
- PORT
- COMMAND: EXCHANGE
- TYPE: BOX
- CONNECT_WS  (url where web socket should connect to)
- SYSTEM INFO (for box)
    - CPU
    - Network Bandwidth
    - Storage Size

- GEOIP
    - IP
    - HOSTNAME
    - COUNTRY
    - CITY
    - REGION
    - ORG
    - LOC
    
- {box-id}:TRAFFIC_FLOW:log_id (a dictionary of a log data, could be many of this term with different id but same prefix.)
    - datetime (e.g. 27/Sep/2017:03:20:10)
    - url
    - status (http status)
    - size
    
##### Entrance to Box (EXCHANGE RESPONSE)
- ID
- IP
- PORT
- COMMAND: EXCHANGE
- TYPE: Entrance
- ENTRANCE_URLS
    - {Entrance URL}

##### Publisher to Entrance (SEARCH REQUEST)
- ID
- IP
- COMMAND: SEARCH
- TYPE: PUBLISHER
- GEOIP
    - IP
    - HOSTNAME
    - COUNTRY
    - CITY
    - REGION
    - ORG
    - LOC

##### Entrance to Publisher (SEARCH RESPONSE)
- ID
- IP
- PORT
- URL
- COMMAND: SEARCH
- TYPE: ENTRANCE
- BOX_SET (a dict, box_id as key, box's exchange as value)
    - BOX_ID 
        - {BOX_EXCHANGE}
- ENTRANCE_URLS
    - {Entrance URL}

##### Publisher to Box 
###### SEARCHING (PUBLISH REQUEST)
- ID
- IP
- COMMAND: PUBLISH
- TYPE: PUBLISHER

###### SEARCHING (PUBLISH RESPONSE)
- ID
- IP
- PORT
- COMMAND: PUBLISH
- TYPE: BOX
- MESSAGE: "ACCEPTED" or ERROR: error message


###### TRANSFER FILES (BINARY REQUEST)
- Format: b'<Dandelion>'+ (BINARY HEADERS IN JSON) + b'</Dandelion>' + file's content
- HEADERS
    - FILE_PATH
    - TTL

###### TRANSFER FILES (BINARY RESPONSE)
None


### Info format in each role
##### Box

###### ID
- box-(HASH)

###### Redis KEY Namespace
- {ID}:SELF_EXCHANGE
- {ID}:EXCHANGE
- {ID}:SUBSCRIBE:{PUBLISHER ID}
- {ID}:EXPIRE_FILES  (sorted set)
- {ID}:TRAFFIC_FLOW:log-<uuid> (hash, storing nginx logging data. Expired after ping_entrance_freq*2)
    - datetime (e.g. 27/Sep/2017:03:20:10)
    - url
    - status (http status)
    - size

##### Publisher
###### ID
- publisher-(HASH)

###### Redis KEY Namespace
- {ID}:SEARCH:{BOX_ID} (hash)
- {ID}:SELF_INFO (hash)
- {ID}:BOX_RANKING  (sorted set)
- {ID}:FILE:FILES_SENDING_QUEUE (list, for api to push file path into it)
- {ID}:FILE:BOX_LIST
- {ID}:FILE:PROCESSED_FILES


##### Entrance Server 
###### ID
- entrance-(HASH)
##### URL (Base_url/)
- index
- ws_change/ : handling incoming websocket

###### Redis KEY Namespace
- {ID}:ENTRANCE_URLS: Set that contains other_entrance_urls so that if the user desires 
                      to expand it when the client has started.(Should not include this 
                      entrance server's url!!)
- {ID}:BOX_SET: Set that contains all the available box
- {ID}:EXCHANGE:<box_id>: Hash that contains exchange messages from boxes
- {ID}:OWN_INFO (hash)

## License
Released under [the MIT License](https://github.com/ktshen/Dandelion/blob/master/License)
