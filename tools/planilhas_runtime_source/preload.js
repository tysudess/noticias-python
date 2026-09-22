const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  start: () => ipcRenderer.invoke("motor:start"),
  stop: () => ipcRenderer.invoke("motor:stop"),
  getStatus: () => ipcRenderer.invoke("status:get"),
  testProxy: () => ipcRenderer.invoke("proxy:test"),
  getConfig: () => ipcRenderer.invoke("config:get"),
  saveConfig: cfg => ipcRenderer.invoke("config:save", cfg),
  openConfigFolder: () => ipcRenderer.invoke("config:open-folder"),
  onStatus: cb => ipcRenderer.on("status", (_, data) => cb(data)),
  onLog: cb => ipcRenderer.on("log", (_, data) => cb(data))
});
