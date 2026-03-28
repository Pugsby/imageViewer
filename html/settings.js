document.getElementById("clientSettings").onclick = function () {
    console.log("open settings")
    document.getElementById("lightbox").style.top = "50%"
    document.getElementById("lightbox").innerHTML = `
    <img src="${closePng}" class="closeButton" onclick="document.getElementById('lightbox').style.top = '150%'"></img>
    <h2 style="margin-bottom: 0px; margin-top: 4px">Theme</h2>
    <button class="noMargin" onclick="theme('themes/default.css')">Default</button>
    <button class="noMargin" onclick="theme('themes/simple.css')">Simple</button>
    
    `
}
const sheet = document.createElement("link")
sheet.rel = "stylesheet"
document.head.appendChild(sheet)
function theme (link) {
    sheet.href = link
}

theme("themes/default.css")