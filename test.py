import logging
import Torrent

logging.basicConfig(filename='torrent.log', level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filemode='w')

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    torrent = Torrent.Torrent("Dune Part 2 (1.6GB).torrent",logger)
    torrent.start()