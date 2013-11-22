aurora
======

Virtualization and SDI for wireless access points (SAVI Testbed)

It is split into three components: Client, Manager and Access Point (AP)
Each is a seperate program that runs on a different computer. The Access Point
code, for example, runs on wireless access points with limited processing
power and RAM, and configures WiFi, virtual bridges and virtual
interfaces based on commands sent to it by the Manager.  The Manager,
in turn, runs on a server and keeps track of multiple access points and their
configuration.  It also interprets and formats requests coming from clients,
controlled by users.  These clients run on a user's computer, and allow
users to control these access points through simple to complex commands,
depending on their needs.


Dependencies
===

Client: 

None for now

Manager:

python paste: http://bitbucket.org/ianb/paste
1.7.5.1 tested

requests: www.python-requests.org
Version 2.0.1 tested

=======
Access Point:

psutil : http://code.google.com/p/psutil/
Version 1.0.1 tested

pika: http://pika.readthedocs.org
Version 0.9.13 tested

requests: www.python-requests.org
Version 2.0.1 tested

The last two dependecies above will install automatically, assuming at least 
easy_install (distribute) exists on the access point.

Known bugs:
=======
Wireless configuration can be tricky on the Access Points, due to the
number of workarounds involved in adding or removing BSS on the fly.  Specifically,
if a user lets others use a radio he owns, and then deletes the radio and BSS,
the BSS of the other users will be deleted as well.  At the moment, slice data
is not updated when this happens (only the hardware data is updated), 
so the other users must manually recreate their slices.
