from monitor_noticias.models import VideoSource

DESKTOP_VIDEO_EXTRAS = [
    VideoSource(id="youtube-g1", name="YouTube • g1", group="YouTube oficial • g1", landingUrl="https://www.youtube.com/channel/UCaGmdJSSiR7fkh2A-c6emsA/videos", linkHints=["/watch"], aliases=["g1", "G1", "Globo", "Portal g1"], youtubeHandle="@g1"),
    VideoSource(id="youtube-domingo-espetacular", name="YouTube • Domingo Espetacular", group="YouTube oficial • Domingo Espetacular", landingUrl="https://www.youtube.com/channel/UCP-Vg2PcmLiWpEdvMI1R35w/videos", linkHints=["/watch"], aliases=["Domingo Espetacular", "Record", "Record TV"], youtubeHandle="@domingoespetacular"),
]
