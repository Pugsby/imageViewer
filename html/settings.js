document.getElementById("clientSettings").onclick = function () {
    console.log("open settings")
    document.getElementById("lightbox").style.top = "50%"
    const host = window.location.hostname
    const pluginAllowed = host === 'localhost' || host === '127.0.0.1' || host === '::1'
    document.getElementById("lightbox").innerHTML = `
    <img src="${closePng}" class="closeButton" onclick="document.getElementById('lightbox').style.top = '150%'"></img>
    <h2 style="margin-bottom: 0px; margin-top: 4px">Theme</h2>
    <button class="noMargin" onclick="theme('themes/default.css')">Default</button>
    <button class="noMargin" onclick="theme('themes/simple.css')">Simple</button>
    <br><br>
    <h2 class="noMargin">Image Settings</h2>
    <p> <button id="toggleSwitchAPG" onclick="toggleAPG()"></button> Autoplay GIFs in grid</p>
    <br>
    <h2 class="noMargin">Plugins</h2>
    <div id="pluginList">${pluginAllowed ? 'Loading plugins…' : 'Plugins disabled — available only on localhost'}</div>
    <p>Note: Please edit config of installed plugins and restart the server when you're ready to use them.</p>
    `
    document.getElementById("toggleSwitchAPG").innerText = autoPlayGifs
    if (pluginAllowed) loadPlugins()
    console.log(autoPlayGifs)
}

async function loadPlugins() {
    const container = document.getElementById('pluginList')
    container.innerText = 'Loading plugins...'
    try {
        const res = await fetch('/api/remotePlugins')
        if (!res.ok) throw new Error('Network')
        const data = await res.json()
        container.innerHTML = ''
        for (const p of data.serverPlugins) {
            const wrap = document.createElement('div')
            wrap.style.display = 'flex'
            wrap.style.gap = '8px'
            wrap.style.alignItems = 'center'

            const img = document.createElement('img')
            img.src = p.thumbnail
            img.style.width = '500px'
            img.style.height = '130px'
            img.style.objectFit = 'cover'
            img.style.borderRadius = '8px'
            wrap.appendChild(img)

            const info = document.createElement('div')
            info.style.flex = '1'
            info.innerHTML = `<b>${p.name}</b><br><small>${p.description}</small><br><small>by ${p.author}</small>`
            wrap.appendChild(info)

            const actions = document.createElement('div')
            if (p.installed) {
                const installed = document.createElement('div')
                installed.innerText = 'Installed'
                installed.style.marginBottom = '4px'
                actions.appendChild(installed)

                const updateBtn = document.createElement('button')
                updateBtn.style.marginRight = '4px'
                if (p.updateAvailable) {
                    updateBtn.innerText = 'Update'
                    updateBtn.onclick = async () => {
                        updateBtn.disabled = true
                        updateBtn.innerText = 'Updating...'
                        try {
                            const r = await fetch('/api/updatePlugin', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({file: p.file})})
                            if (!r.ok) throw new Error('Update failed')
                            updateBtn.innerText = 'Updated'
                            await loadPlugins()
                        } catch (e) {
                            updateBtn.innerText = 'Error'
                            updateBtn.disabled = false
                        }
                    }
                } else {
                    updateBtn.innerText = 'Up to date'
                    updateBtn.disabled = true
                }
                actions.appendChild(updateBtn)

                const editBtn = document.createElement('button')
                editBtn.innerText = 'Edit Config'
                editBtn.onclick = () => { showConfigEditor(p) }
                actions.appendChild(editBtn)
            } else {
                const btn = document.createElement('button')
                btn.innerText = 'Install'
                btn.onclick = async () => {
                    btn.disabled = true
                    btn.innerText = 'Installing...'
                    try {
                        const r = await fetch('/api/installPlugin', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({file: p.file})})
                        if (!r.ok) throw new Error('Install failed')
                        btn.innerText = 'Installed'
                        btn.disabled = true
                        // refresh plugins
                        loadPlugins()
                    } catch (e) {
                        btn.innerText = 'Error'
                        btn.disabled = false
                    }
                }
                actions.appendChild(btn)
            }
            wrap.appendChild(actions)

            container.appendChild(wrap)
            const hr = document.createElement('hr')
            container.appendChild(hr)
        }
    } catch (e) {
        container.innerText = 'Failed to load plugins.'
    }
}

function showConfigEditor(p) {
    const lightbox = document.getElementById('lightbox')
    const cfg = p.config || {}
    let html = `<h2>${p.name} — Config</h2>`
    html += `<div id="pluginConfigForm">`;
    for (const k of Object.keys(cfg)) {
        const v = cfg[k]
        html += `<div style="margin-bottom:8px"><label style="display:block">${k}</label><input id="cfg_${k}" style="width:100%" value="${String(v).replace(/"/g,'&quot;')}"></div>`
    }
    html += `</div><button id="savePluginConfig">Save</button> <button onclick="document.getElementById('lightbox').style.top='150%';">Close</button>`
    lightbox.innerHTML = html
    document.getElementById('savePluginConfig').onclick = async () => {
        const newCfg = {}
        for (const k of Object.keys(cfg)) {
            const el = document.getElementById('cfg_' + k)
            if (!el) continue
            let val = el.value
            // try to coerce booleans and numbers
            if (val === 'true') val = true
            else if (val === 'false') val = false
            else if (!isNaN(val) && val !== '') val = Number(val)
            newCfg[k] = val
        }
        try {
            const r = await fetch('/api/pluginConfig', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({file: p.file, config: newCfg})})
            if (!r.ok) throw new Error('save failed')
            document.getElementById('lightbox').style.top = '150%'
            loadPlugins()
        } catch (e) {
            alert('Failed to save config')
        }
    }
}

const sheet = document.createElement("link")
sheet.rel = "stylesheet"
document.head.appendChild(sheet)

function theme(link) {
    sheet.href = link
    localStorage.setItem("theme", link)
}

const savedTheme = localStorage.getItem("theme") || "themes/default.css"
theme(savedTheme)

function toggleAPG () {
    autoPlayGifs = !autoPlayGifs
    localStorage.setItem("apGifs", autoPlayGifs)
    document.getElementById("toggleSwitchAPG").innerText = autoPlayGifs
}