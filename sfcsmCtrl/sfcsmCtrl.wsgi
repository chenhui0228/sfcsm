#author 01107267
#licence : apache v2

# change dir for sfcsmCtrl folder
import sys, os
abspath = os.path.dirname(__file__)
sys.path.append(abspath)
os.chdir(abspath)

from Log import Log

sys.path.insert(0, '/home/workspace/sfcsm/sfcsmCtrl')
from sfcsmCtrlcore import app as application