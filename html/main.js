function getImageSrc(collectionName, item) {
  const base = `api/images/${collectionName}/${item.name}`;
  var tn = "?thumbnail"
  if (item.type == "gif" && autoPlayGifs) {
    tn = ""
  }
  return (item.type === "folder" ? `${base}/${item.content[0].name}` : base) + tn;
}

async function openImage(path, item, imageNumber, totalImages) {
  if (item.type == "folder") {
    path = path + "/" + item.content[imageNumber].name;
  }
  const metadata = await getMetadata(path, item);
  const lightbox = document.getElementById("lightbox");
  lightbox.style.top = "50%";
  lightbox.dataset.basePath = item.type === "folder"
    ? path.substring(0, path.lastIndexOf("/"))
    : path;
  lightbox.dataset.item = JSON.stringify(item);
  lightbox.dataset.totalImages = totalImages;
  imgTag = item.type == "mp4" || item.type == "webm" || item.type == "ogg"
  ? `<video src="${"api/images/" + path}" controls></video>`
  : `<img src="${"api/images/" + path}"></img>`
  lightbox.innerHTML = `
    <h1 class="noMargin">${metadata.name}</h1>
    <p class="noMargin">${metadata.artist}</p><br>
    ${imgTag}<br>
    ${totalImages > 0 ? `<p class="filename">${item.content[imageNumber].name}</p>` : ""}
    ${imageNumber > 0 ? `<button onclick="navigateImage(${imageNumber - 1})" class="prev">Previous Image</button>` : ""}
    ${imageNumber < totalImages - 1 ? `<button onclick="navigateImage(${imageNumber + 1})" class="next">Next Image</button>` : ""}
    <p>${marked.parse(metadata.description)}</p>
    <p>Tags:<br><sect class='tag'>${metadata.tags.join(" </sect><sect class='tag'>")} </sect></p>
    <img src="${closePng}" class="closeButton" onclick="document.getElementById('lightbox').style.top = '150%'"></img>
  `;
  twemoji.parse(lightbox);
}

function navigateImage(imageNumber) {
  const lightbox = document.getElementById("lightbox");
  const item = JSON.parse(lightbox.dataset.item);
  const basePath = lightbox.dataset.basePath;
  const totalImages = parseInt(lightbox.dataset.totalImages);
  openImage(basePath, item, imageNumber, totalImages);
}

function createImage(src, itemSrc, item, totalImages) {
  const img = document.createElement("img");
  img.src = src;
  img.onclick = function() { openImage(itemSrc, item, 0, totalImages); };
  img.classList.add("gridImg");
  return img;
}

function createLabel(text) {
  const p = document.createElement("p");
  p.innerText = text;
  p.style.marginBottom = "0"
  return p;
}

async function getMetadata(path, item) {
  try {
    const response = await fetch(`api/metadata/${path}.json`);
    return response.json();
  } catch (error) {
    console.error("Fetch error:", error.message);
  }
}

async function listCollections(search) {
  try {
    var url = "api/lsImages";
    if (search) {
      url = "api/search";
      url += "?q=" + search.query + "&type=" + search.type;
    }
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

    const collections = await response.json();

    document.getElementById("imageGrid").innerHTML = "";
    for (const collection of collections) {
      document.getElementById("imageGrid").appendChild(createLabel(collection.name));

      const grid = document.createElement("div");
      grid.classList.add("imageGrid");
      document.getElementById("imageGrid").appendChild(grid);

      const images = collection.content.filter(item => item.type !== "json");
      for (const item of images) {
        let totalImages = 0;
        if (item.type == "folder") {
          totalImages = item.content.length;
        }
        grid.appendChild(createImage(getImageSrc(collection.name, item), collection.name + "/" + item.name, item, totalImages));
      }
    }
  } catch (error) {
    console.error("Fetch error:", error.message);
  }
}

document.getElementById("searchForm").onsubmit = function(event) {
  event.preventDefault();
  const query = document.getElementById("searchInput").value;
  const type = document.getElementById("searchType").options[document.getElementById("searchType").selectedIndex].value;
  listCollections({ query, type });
}

listCollections();