const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const axios = require("axios");
const { spawn } = require("child_process");

let win = null;
let motor = null;
let encerramentoManual = false;
let reiniciosAutomaticos = 0;
let reinicioTimer = null;
let capturandoNoticia = false;
let capturandoVideo = false;

let stats = {
  status: "PARADO",
  whatsapp: "DESCONHECIDO",
  planilha: "AGUARDANDO",
  proxy: "DESCONHECIDO",
  processadas: 0,
  videos: 0,
  erros: 0,
  ultimaLinha: "",
  ultimaMensagem: "",
  ultimaAtualizacao: "--",
  ultimaNoticia: { titulo:"Nenhuma notícia processada ainda", veiculo:"--", grupo:"--", data:"--", assunto:"--", analise:"--", autor:"--", link:"" }
};

function baseDir(){ return process.env.PORTABLE_EXECUTABLE_DIR || (app.isPackaged ? path.dirname(process.execPath) : __dirname); }
function configPath(){ return path.join(baseDir(), "config.json"); }
function enginePath(){ return app.isPackaged ? path.join(app.getAppPath(), "engine", "index.js") : path.join(__dirname, "engine", "index.js"); }
function appIcon(){ return path.join(__dirname, "build", "icon.png"); }
function ensureConfig(){
  const target = configPath();
  if(!fs.existsSync(target)){
    const source = app.isPackaged ? path.join(process.resourcesPath, "config.default.json") : path.join(__dirname, "config.json");
    fs.copyFileSync(source, target);
  }
  return target;
}
function readConfig(){ return JSON.parse(fs.readFileSync(ensureConfig(), "utf8")); }
function proxyFromConfig(cfg){
  const p = cfg?.proxy || {};
  if(!p.ativo || !p.host || !Number(p.porta)) return undefined;
  const proxy = { protocol:"http", host:String(p.host).trim(), port:Number(p.porta) };
  if(String(p.usuario || "").trim()) proxy.auth = { username:String(p.usuario).trim(), password:String(p.senha || "") };
  return proxy;
}
function send(channel,data){ if(win && !win.isDestroyed()) win.webContents.send(channel,data); }
function stamp(){ return new Date().toLocaleString("pt-BR"); }

function parseLine(line,isErr=false){
  if(!line) return;
  stats.ultimaMensagem=line;
  if(line.includes("SISTEMA ATIVO")){ stats.status="RODANDO"; stats.whatsapp="CONECTADO"; reiniciosAutomaticos=0; }
  if(line.includes("Leia o QR Code")){ stats.status="AGUARDANDO QR"; stats.whatsapp="AGUARDANDO AUTENTICAÇÃO"; }
  if(line.includes("PROXY ATIVO")) stats.proxy="ATIVO";
  if(line.includes("PROXY: DESATIVADO")) stats.proxy="DESATIVADO";
  if(line.includes("PROXY COM AUTENTICAÇÃO CONFIGURADA")) stats.proxy="AUTENTICADO/CONFIGURADO";
  if(line.includes("RECONEXÃO")) stats.whatsapp="RECONECTANDO";
  if(line.includes("NOTÍCIA IDENTIFICADA")){ capturandoNoticia=true; capturandoVideo=false; stats.ultimaNoticia={titulo:"--",veiculo:"--",grupo:"--",data:"--",assunto:"--",analise:"--",autor:"--",link:""}; }
  if(line.includes("VÍDEO IDENTIFICADO")){ capturandoVideo=true; capturandoNoticia=false; }
  if(capturandoNoticia){
    if(line.startsWith("Data:")) stats.ultimaNoticia.data=line.slice(5).trim();
    if(line.startsWith("Veículo:")) stats.ultimaNoticia.veiculo=line.slice(8).trim();
    if(line.startsWith("Título:")) stats.ultimaNoticia.titulo=line.slice(7).trim();
    if(line.startsWith("Autor:")) stats.ultimaNoticia.autor=line.slice(6).trim();
    if(line.startsWith("Análise:")) stats.ultimaNoticia.analise=line.slice(8).trim();
    if(line.startsWith("Assunto:")) stats.ultimaNoticia.assunto=line.slice(8).trim();
    if(line.startsWith("Link:")) stats.ultimaNoticia.link=line.slice(5).trim();
  }
  if(line.includes("PLANILHA ATUALIZADA")){ stats.planilha="OK"; stats.processadas++; stats.ultimaAtualizacao=stamp(); capturandoNoticia=false; }
  if(line.includes("VÍDEO REGISTRADO NA PLANILHA")){ stats.planilha="OK"; stats.processadas++; stats.videos++; stats.ultimaAtualizacao=stamp(); capturandoVideo=false; }
  if(line.startsWith("Linha:")) stats.ultimaLinha=line.replace("Linha:","").trim();
  if(line.includes("ERRO AO ENVIAR PARA PLANILHA")) stats.planilha="ERRO";
  if(line.includes("Falha na autenticação") || line.includes("ERRO AO INICIALIZAR WHATSAPP")) stats.whatsapp="ERRO";
  if(line.includes("WhatsApp desconectado")) stats.whatsapp="DESCONECTADO";
  if(line.includes("HTTP: 407") || line.includes("407")) stats.proxy="AUTENTICAÇÃO REJEITADA";
  if(line.includes("ERR_INVALID_AUTH_CREDENTIALS")) stats.proxy="CREDENCIAIS REJEITADAS";
  if(isErr && !line.includes("ERRO AO ENVIAR PARA PLANILHA")) stats.erros++;
  send("log",{line,isErr});
  send("status",stats);
}

function iniciarMotor(){
  if(motor) return {ok:false,message:"Motor já está em execução."};
  ensureConfig();
  encerramentoManual=false;
  stats.status="INICIANDO"; stats.whatsapp="CONECTANDO"; stats.planilha="AGUARDANDO"; stats.proxy=readConfig().proxy?.ativo ? "CONFIGURADO" : "DESATIVADO";
  send("status",stats);
  const env={...process.env,CONFIG_PATH:configPath()};
  if(app.isPackaged) env.ELECTRON_RUN_AS_NODE="1";
  motor=spawn(process.execPath,[enginePath()],{cwd:baseDir(),env,windowsHide:true});
  motor.stdout.setEncoding("utf8"); motor.stderr.setEncoding("utf8");
  motor.stdout.on("data",d=>String(d).split(/\r?\n/).forEach(l=>parseLine(l,false)));
  motor.stderr.on("data",d=>String(d).split(/\r?\n/).forEach(l=>parseLine(l,true)));
  motor.on("exit",code=>{
    parseLine(`Motor finalizado. Código: ${code}`,code!==0); motor=null;
    if(!encerramentoManual && code!==0){
      reiniciosAutomaticos++;
      if(reinicioTimer) clearTimeout(reinicioTimer);
      if(reinicioAutomaticoPermitido()){
        stats.status="RECUPERANDO"; send("status",stats);
        reinicioTimer=setTimeout(()=>{reinicioTimer=null;iniciarMotor();},5000);
        return;
      }
      stats.status="ERRO";
    } else stats.status="PARADO";
    if(stats.whatsapp!=="ERRO") stats.whatsapp="DESCONECTADO";
    send("status",stats);
  });
  motor.on("error",err=>{ parseLine(`Erro ao iniciar motor: ${err.message}`,true); motor=null; stats.status="ERRO"; send("status",stats); });
  return {ok:true};
}
function reinicioAutomaticoPermitido(){ return reiniciosAutomaticos<=5; }
function pararMotor(){
  if(!motor){ if(reinicioTimer){clearTimeout(reinicioTimer);reinicioTimer=null;} return {ok:false,message:"Motor já está parado."}; }
  encerramentoManual=true; if(reinicioTimer){clearTimeout(reinicioTimer);reinicioTimer=null;}
  try{motor.kill();}catch(_){} motor=null; stats.status="PARADO"; stats.whatsapp="DESCONECTADO"; send("status",stats); return {ok:true};
}

async function testarProxy(){
  try{
    const cfg=readConfig();
    if(!cfg.proxy?.ativo) return {ok:false,message:"Proxy está desativado."};
    const proxy=proxyFromConfig(cfg);
    if(!proxy) return {ok:false,message:"Servidor e porta do proxy não estão configurados."};
    stats.proxy="TESTANDO"; send("status",stats);
    const r=await axios.get("https://web.whatsapp.com/",{proxy,timeout:10000,validateStatus:()=>true});
    if(r.status>=200 && r.status<500){ stats.proxy=proxy.auth?"OK COM AUTENTICAÇÃO":"OK SEM AUTENTICAÇÃO"; return {ok:true,message:`Proxy respondeu HTTP ${r.status}.`}; }
    stats.proxy=`ERRO HTTP ${r.status}`; return {ok:false,message:`Proxy respondeu HTTP ${r.status}.`};
  }catch(err){
    const code=err?.response?.status || "";
    stats.proxy=code===407?"AUTENTICAÇÃO REJEITADA":"ERRO";
    const detail=err?.response?.status ? `HTTP ${err.response.status}` : (err?.code || err?.message || "erro desconhecido");
    return {ok:false,message:`Falha no teste do proxy: ${detail}`};
  } finally { send("status",stats); }
}

function createWindow(){
  win=new BrowserWindow({width:1240,height:790,minWidth:1050,minHeight:680,title:"Automação Planilhas - WhatsApp → Planilhas Google",backgroundColor:"#07131d",icon:appIcon(),webPreferences:{preload:path.join(__dirname,"preload.js"),contextIsolation:true,nodeIntegration:false}});
  win.loadFile(path.join(__dirname,"renderer","index.html")); win.setMenuBarVisibility(false);
}

app.whenReady().then(()=>{
  ensureConfig(); createWindow();
  ipcMain.handle("motor:start",()=>iniciarMotor());
  ipcMain.handle("motor:stop",()=>pararMotor());
  ipcMain.handle("status:get",()=>stats);
  ipcMain.handle("proxy:test",()=>testarProxy());
  ipcMain.handle("config:get",()=>readConfig());
  ipcMain.handle("config:save",(_,cfg)=>{fs.writeFileSync(ensureConfig(),JSON.stringify(cfg,null,2),"utf8");return {ok:true,path:configPath()};});
  ipcMain.handle("config:open-folder",()=>{shell.openPath(baseDir());return {ok:true};});
});
app.on("before-quit",()=>{encerramentoManual=true;if(reinicioTimer)clearTimeout(reinicioTimer);try{if(motor)motor.kill();}catch(_){} });
app.on("window-all-closed",()=>{if(process.platform!=="darwin")app.quit();});
