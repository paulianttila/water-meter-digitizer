# Meter digitizer

Meter digitizer to readout of an analog and digital meters with the help of a camera, image processing and neural network processing.

This is completely rewritten fork from original jomjol version which is archived in 2021.

Docker container is available for an x386 and arm based systems.

## Docker-compose

### Example docker-compose.yaml

```
version: "3.5"

services:
  meter-digitizer:
    container_name: ${NAME:-meter-digitizer}
    image: paulianttila/meter-digitizer
    restart: unless-stopped
    environment:
      - TZ=Europe/Helsinki
    volumes:
        - ${DIR_DATA:-.}/config:/config
        - temp:/image_tmp
    ports:
        - 3000:3000
```

### Environament variables

## Configuration parameters

## GUI

