const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('extratorAPI', {
  extrair: (opcoes) => ipcRenderer.invoke('extrair-materia', opcoes),
  abrirUltimo: () => ipcRenderer.invoke('abrir-ultimo'),
  abrirHistorico: () => ipcRenderer.invoke('abrir-historico'),
  abrirPasta: () => ipcRenderer.invoke('abrir-pasta'),
  obterEstado: () => ipcRenderer.invoke('obter-estado'),
  obterCredenciaisAssinante: (provedor) => ipcRenderer.invoke('obter-credenciais-assinante', provedor),
  salvarCredenciaisAssinante: (provedor, dados) => ipcRenderer.invoke('salvar-credenciais-assinante', provedor, dados),
  apagarCredenciaisAssinante: (provedor) => ipcRenderer.invoke('apagar-credenciais-assinante', provedor),
  revisarTextoRigido: (texto) => ipcRenderer.invoke('revisar-texto-rigido', texto),
  onStatus: (callback) => ipcRenderer.on('extracao-status', (_event, mensagem) => callback(mensagem))
});
