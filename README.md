# ntrip_ros
NTRIP client, imports RTCM streams to ROS topic

This was forked from github.com/tilk/ntrip_ros

My service did not have /n/r characters. So I parsed out individual messages and published each on one the /rtcm ROS topic.
It would crash with IncompleteRead error. I added patch at top of file.
But the connection had closed and it would crash again. I ended up detecting zero length data and closing and reopening the data stream.
It continues on without a glitch.

I intend to use it with https://github.com/ros-agriculture/ublox_f9p (which may not be committed yet).

t may also require this package: https://github.com/tilk/rtcm_msgs
