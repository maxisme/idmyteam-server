import logging
from settings.config import ROOT

logging.getLogger("tornado.access").disabled = True
logging.getLogger("rq.worker").disabled = True

logger = logging.getLogger('')
logger.setLevel(logging.NOTSET)

c_handler = logging.StreamHandler()
c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)

f_handler = logging.FileHandler(ROOT + '/idmyteam.log')
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
