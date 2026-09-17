from .direct_page import DirectVideoPageResolver
from .globoplay_editions import GloboplayEditionCollector
from .globoplay_jarvis import GloboplayJarvisCollector
from .globoplay_trechos import GloboplayTrechosCollector
from .sources import DESKTOP_VIDEO_EXTRAS
from .website import WebsiteVideoCollector
from .youtube import YouTubeCollector

__all__=["DirectVideoPageResolver","GloboplayEditionCollector","GloboplayJarvisCollector","GloboplayTrechosCollector","DESKTOP_VIDEO_EXTRAS","WebsiteVideoCollector","YouTubeCollector"]
