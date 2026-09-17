# FFMPEG BUILD MANIFEST — PASSO 26

## Binários distribuídos

- `ffmpeg.exe` SHA-256: `91678b935eb52cc740249474574b6042768b744c622347f28a1b487e1ed29915`
- `ffprobe.exe` SHA-256: `c42ada47df746e3788e2ba3ed2f7af07662a58f9088f9894e1b14d3d5c432263`
- versão: `n9.0.1-29-gad500d59cb-20260913`

### Correção auditável de identidade

Os hashes acima são os valores medidos diretamente no portable validado pelo workflow `Passo 25 - Audit FFmpeg Provenance`, run `34796296147`, que concluiu `PASS25_PROVENANCE_MATCH=YES` e comprovou igualdade byte-a-byte com o pacote BtbN de SHA-256 `a224a1dbea8b3e4e75ce17e9465a919cc74c9f027021046eaec610e40464bf27`.

Os valores `828bef350665c78b76e4bc3597b1714c66d3bd79a642948243e59754dab1878d` e `897cabca3eb2a16be9bf111a9955277ec93a17527aa6c6b108fd07ab182927f6` registrados posteriormente no PASSO 26 eram inconsistentes com essa evidência primária. A correção deste manifesto não substitui nem recompila FFmpeg/FFprobe; corrige somente o registro dos hashes.

## Build BtbN exata

- fornecedor: `BtbN/FFmpeg-Builds`
- pacote: `ffmpeg-n9.0.1-29-gad500d59cb-win64-gpl-9.0.zip`
- família histórica: `ffmpeg-n9.0-latest-win64-gpl-9.0.zip`
- SHA-256 do pacote comprovado: `a224a1dbea8b3e4e75ce17e9465a919cc74c9f027021046eaec610e40464bf27`
- run BtbN: `34756521749`
- artifact: `ffmpeg-win64-gpl-9.0`, id `10319722058`
- build recipe commit: `3e6685eda92f9288c15ac320139622dcedca09a4`
- tag histórica: `autobuild-2026-09-13-14-50`
- tipo: Windows x64, static, GPL, linha 9.0

## FFmpeg source

- source version: `n9.0.1-29-gad500d59cb-20260913`
- commit: `ad500d59cb6e0126add4fcb95afb4e2557c4292c`
- branch usada pela variante: `release/9.0`
- source tag exata: **NÃO DETERMINADA PELO ARTEFATO/BUILD ANALISADO**
- archive: `source-archives/FFmpeg-ad500d59cb6e0126add4fcb95afb4e2557c4292c.tar.gz`
- SHA-256: `02b4a070afde52755156d3011508bc54e02adf03da0b51d264735ee5efea4a1c`

## Build scripts

- repositório: `https://github.com/BtbN/FFmpeg-Builds.git`
- commit: `3e6685eda92f9288c15ac320139622dcedca09a4`
- archive: `source-archives/FFmpeg-Builds-3e6685eda92f9288c15ac320139622dcedca09a4.tar.gz`
- SHA-256: `95eb040c960fc4636c1e9505fee7659d41902380a0fa4ca8aaa5458f40166c21`

## Patches / transformações

Os scripts históricos sob `build-recipe/scripts.d/` são preservados integralmente. O recipe x265 aplica comprovadamente:

`sed -i '1i#include <cstdint>' source/dynamicHDR10/json11/json11.cpp`

Essa transformação permanece no build script original incluído no Corresponding Source. **PATCHES ADICIONAIS COMPROVADOS = NENHUM.**

## Componentes GPL externos comprovados

### x264
- source: `https://code.videolan.org/videolan/x264.git`
- commit: `0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee`
- cache materializado: `50-x264_7aee4cf46b7c0eff1a5ad3d23ae43a29562065ef2866a4a883d7ad2db0fb755d.tar.xz`
- SHA-256 real: `20aa4369ccaa99e0bab9208f611c3d633ff3c87654d7a673c840510e64777b97`
- incluído no Corresponding Source: SIM

### x265
- source: `https://github.com/Multicorewareinc/x265.git`
- commit: `116b87573ed0cec20b75ccacd5641bf06f6e57bd`
- cache materializado: `50-x265_6151d2ebb2cf627d498368b2667da4d00df1e91e351920993dd4e553639303c0.tar.xz`
- SHA-256 real: `a0ab07b667e4f65243b1b9d0a2b8d6009a709284a4324b193b93c1b1e9e273e9`
- incluído no Corresponding Source: SIM

Os demais sources usados pelas recipes históricas BtbN estão preservados em `dependency-sources/`; não foram reclassificados por suposição.

## Configuration integral comprovada

`--prefix=/ffbuild/prefix --pkg-config-flags=--static --pkg-config=pkg-config --cross-prefix=x86_64-w64-mingw32- --arch=x86_64 --target-os=mingw32 --enable-gpl --enable-version3 --disable-debug --disable-w32threads --enable-pthreads --enable-iconv --enable-zlib --enable-libxml2 --enable-libvmaf --enable-fontconfig --enable-libharfbuzz --enable-libfreetype --enable-libfribidi --enable-vulkan --enable-libdav1d --enable-libvorbis --enable-librav1e --enable-librsvg --disable-libxcb --disable-xlib --disable-libpulse --enable-gmp --enable-lzma --enable-liblcevc-dec --enable-opencl --enable-amf --enable-libaom --enable-avisynth --enable-chromaprint --enable-libdavs2 --enable-libdvdread --enable-libdvdnav --disable-libfdk-aac --enable-ffnvcodec --enable-cuda-llvm --enable-frei0r --enable-libgme --enable-libjxl --enable-libkvazaar --enable-libaribb24 --enable-libaribcaption --enable-libass --enable-libbluray --enable-libmp3lame --enable-libopus --enable-libplacebo --enable-librist --enable-libssh --enable-libtheora --enable-libvpx --enable-libwebp --enable-libzmq --enable-lv2 --enable-libvpl --enable-openal --enable-liboapv --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 --enable-libopenjpeg --enable-libopenmpt --enable-librubberband --enable-schannel --enable-sdl2 --enable-libsnappy --enable-libsoxr --enable-libsrt --enable-libsvtav1 --enable-libtwolame --enable-libuavs3d --disable-libdrm --enable-vaapi --enable-libvidstab --enable-libvvenc --disable-whisper --enable-libx264 --enable-libx265 --enable-libxavs2 --enable-libxvid --enable-libzimg --enable-libzvbi --extra-cflags=-DLIBTWOLAME_STATIC --extra-cxxflags= --extra-libs=-lgomp --extra-ldflags=-pthread --extra-ldexeflags= --cc=x86_64-w64-mingw32-gcc --cxx=x86_64-w64-mingw32-g++ --ar=x86_64-w64-mingw32-gcc-ar --ranlib=x86_64-w64-mingw32-gcc-ranlib --nm=x86_64-w64-mingw32-gcc-nm --extra-version=20260913`

## Regime técnico

- `--enable-gpl`: SIM
- `--enable-version3`: SIM
- `--enable-nonfree`: NÃO
- `--disable-libfdk-aac`: SIM
- classificação técnica: GPL/version3

## Corresponding Source final

- arquivo: `MONITOR-DE-NOTICIAS-FFMPEG-CORRESPONDING-SOURCE-n9.0.1-29-gad500d59cb-20260913.zip`
- tamanho: `4466155388` bytes
- SHA-256: `54a2b6472bfa13b7bdb35ee25f0793461d890e774074eab350e6e9eb812f35eb`
- árvore: `10950` arquivos, `4462017668` bytes antes do ZIP final
- integridade da árvore: PASS
- reextração do ZIP final: PASS
- publication target: mesma futura GitHub Release do portable Windows.
