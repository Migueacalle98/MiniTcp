# Trapy

> Miguel Angel Gonzalez Calles 

Aplication Layer Project in Python.
It has been implemented the TCP protocol, without an appropied checksum computation, using only, raw_sockets, meneing using only network layer sockets.

It has been added the original roject orientation.

# Problems:

- Really slow compared to normal sockets
- Conn does not manage multiole clients
- The only part of TCP protocola that it does not propertly computes is the checksum header.

# Set Up:

to get the initial test files run:

sudo ./create_data.sh

# Testing:
 
> Simply run on the root of the project:

sudo python3 -m unittest discover tests


