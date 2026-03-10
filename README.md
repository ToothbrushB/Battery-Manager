# Project title and description
Battery Manger
An app to manage your batteries. Integrates with Snipe-IT Asset Management to sync assets. Allows for easy display and editing of custom fields, including displaying a graph.
# Explanation of what the project does
Manages your batteries. Scans QR codes and displays battery information.
# Technologies used
html5-qrcode
Flask
Redis and redis queue
sqlalchemy
sqlite
See requirements.txt for more detail
# How to run the project
Install Redis
Install pip requirements
Configure stuff in .env file
Run Flask

# Any design decisions or tradeoffs made
Wanted to add more robust support for locations (like a grid view of the battery cart) and ability to sync with match schedule but no time.
Also wanted to integrate with hardware to facilitate auto location changes/checkouts but that's not done either. 