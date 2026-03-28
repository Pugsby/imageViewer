# Image Viewer
Image Viewer is a booru-inspired server made in python with a clean-looking client with basic metadata support.<br>
! WARNING ! This is only intended for personal use, there is a lot of vulnerabilities that may cause a crash. 
## Features
- Images (png, jpg, webp)
- Video (mp4, webm, ogg)
- Basic metadata support
- Multiple Collections
- Multiple images (and videos) in one
- Simple server-side plugin support

## JSON Metadata Format
Metadata files must be placed next to images/videos in order to be read, the name of the json must be the same as the image (not including extension). If a image is in a multi-image post, you can either place the json file next to the image or give the multi-image post the metadata.
```
{
    "name": "Post Name",
    "description": "Post Description",
    "tags": ["tag1", "tag2", "tag3", "etc"],
    "artist": "Artist Name"
}
```
Metadata is completely optional and is not needed.
## Usage
Add images and videos to imageViewer/images/collection. You can change the name of this folder and even add multiple collections. You can also add multiple images in one post by adding each image into a new subfolder.
## API
The API is very simple, there's very few endpoints.
### [GET] /api/images/
Returns a requested image. (Ex: /api/images/collection/image.png)
### [GET] /api/metadata/
Returns the metadata for a image. (Ex: /api/metadata/collection/image.png.json)
### [GET] /api/lsImages
Returns the tree of the images folder.
## Installation
Installation is pretty easy, all you do is clone the repo. (Linux)
```
git clone https://github.com/Pugsby/imageViewer
cd imageViewer
pip install -r requirements.txt
```
## Running
Run the server by running server.py
```
python server.py
```
You can view your images through http://localhost:8282/
## Planned Features
- Blacklist and Whitelist support
- Administration Features
- Pagintation
- Optimization