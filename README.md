# media_conveyor


**By: James Berkheimer**

**End goal full automation!!!**

**<span style="text-decoration:underline;">Project Overview</span>:**
1) The primary goal of this project is to serve as display project to showcase
my development and engineering skills.  A coding demo reel in a sense.

2) The secondary goal is to learn new skills and techniques.

3) The final goal of this project is to provide the owner of any file repository the ability to safely and easily open up that repository to outside users to access and download files from that repo.  This will be done by leveraging the following:


**<span style="text-decoration:underline;">Technologies</span>:**
* AWS EC2 and Elasticache Redis to store a database of local data file data.
* Django to provide a public web interface that will be hosted on AWS and displays
the files available for download.
* Python to develop the backend.  This includes building of the database and to
provide interconnectivity and authentication for host to client file transfer.
* Github Copilot to assist in the development process.

**<span style="text-decoration:underline;">Goals and Non-Goals</span>:**
* My initial goal is to develop the app considering my private Plex setup.
But I would like this app to be more agnostic so as to provide anyone with a
file database to utilize this app.
* Full automation.
* Use AWS to host the metadata DB and the web app.
* **This app is NOT meant for distribution in the sense that it's going to be a
functional tool for the community.  I will not be maintaining it beyond my personal
preferences.  But other developers are free to use this code and further develop
it on their own.**

**<span style="text-decoration:underline;">Steps for use:</span>**
1. Install & launch application
2. EC2 instance is generated
3. Redis instance is created and populated with data from Plex
4. Public facing web app so users can select which files they want to download
5. Download directly from the local server.

**<span style="text-decoration:underline;">First Steps</span>:**
1. Grab metadata from Plex and create a Redis DB to store it.
    * Learn Plex API to get metadata.
2. Create an AWS EC2 instance and migrate that Redis DB to it.
    * Create an AWS EC2 instance.
    * Setup and configure Redis.
    * Process for updating the data cache.
3. Create a Django web app that can display the data from the Redis DB following the REST model.
    * Learn how to build a Django app.
    * Leverage AWS to host the react web app.
    * User logins and authentication.
4. Add functionality for downloading each video.
    * ?

**<span style="text-decoration:underline;">Milestones</span>:**
1. ~~Establish code to interface with Plex and gather metadata from its database.~~
    1. ~~This code should gather local authentication credentials to use for connecting to the local Plex server.~~
2. ~~Create a Redis database using the metadata from Plex~~
    2. ~~Learn how to upload that database to an AWS EC2 instance~~
3. ~~Establish code to automate the creation of an EC2 instance~~
4. Develop a web app using Django that can display Metadata from the Redis database.
5. Learn how to safely allow a user to download files via links.