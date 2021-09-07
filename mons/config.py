import configparser
import os

from appdirs import AppDirs # https://github.com/ActiveState/appdirs

dirs = AppDirs('mons', 'coloursofnoise')

CONFIG_FILE = 'config.ini'
INSTALLS_FILE = 'installs.ini'
CACHE_FILE = 'cache.ini'

#Config, Installs, Cache
Config_DEFAULT = {}
Installs_DEFAULT = {
    'PreferredBranch': 'stable',
}
Cache_DEFAULT = {
    'CelesteVersion': '1.4.0.0',
    'Everest': False,
    'Hash': 'f1c4967fa8f1f113858327590e274b69',
}

def loadConfig(file, default):
    config = configparser.ConfigParser()
    config_file = os.path.join(dirs.user_data_dir, file)
    if os.path.isfile(config_file):
        config.read(config_file)
    else:
        config['DEFAULT'] = default
        os.makedirs(dirs.user_data_dir, exist_ok=True)
        with open(config_file, 'x') as f:
            config.write(f)
    return config

def saveConfig(config, file):
    with open(os.path.join(dirs.user_data_dir, file), 'w') as f:
        config.write(f)