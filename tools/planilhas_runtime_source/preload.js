const {
  contextBridge,
  ipcRenderer,
  clipboard,
} = require("electron");

contextBridge.exposeInMainWorld(
  "api",
  {
    start:
      () =>
        ipcRenderer.invoke(
          "motor:start"
        ),

    startLogin:
      () =>
        ipcRenderer.invoke(
          "motor:start-login"
        ),

    stop:
      () =>
        ipcRenderer.invoke(
          "motor:stop"
        ),

    getStatus:
      () =>
        ipcRenderer.invoke(
          "status:get"
        ),

    testProxy:
      cfg =>
        ipcRenderer.invoke(
          "proxy:test",
          cfg
        ),

    getConfig:
      () =>
        ipcRenderer.invoke(
          "config:get"
        ),

    saveConfig:
      cfg =>
        ipcRenderer.invoke(
          "config:save",
          cfg
        ),

    openConfigFolder:
      () =>
        ipcRenderer.invoke(
          "config:open-folder"
        ),

    readClipboardText:
      () =>
        clipboard.readText(),

    onStatus:
      cb =>
        ipcRenderer.on(
          "status",
          (_, data) =>
            cb(data)
        ),

    onLog:
      cb =>
        ipcRenderer.on(
          "log",
          (_, data) =>
            cb(data)
        ),
  }
);
