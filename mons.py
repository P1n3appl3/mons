#!/usr/bin/env python

#region IMPORTS
import sys
import os
import configparser
import importlib

import hashlib
import subprocess

import urllib.request
import zipfile
import json

import dnfile # https://github.com/malwarefrank/dnfile
from pefile import DIRECTORY_ENTRY # https://github.com/erocarrera/pefile

from typing import Tuple, List, Dict
from pprint import pprint
#endregion

#region CONSTANTS
PLUGIN_MODULE = 'bin'

USER_FOLDER = './usr'
INSTALLS_FILE = f'{USER_FOLDER}/installs.ini'
CACHE_FILE = f'{USER_FOLDER}/cache.ini'
PLUGIN_FOLDER = './bin'

VanillaHashes = {
    'f1c4967fa8f1f113858327590e274b69': '1.4.0.0',
}

#endregion

#region UTILITIES
Commands = {}
Installs = {}
Installs_DEFAULT = {
    'PreferredBranch': 'stable',
}
Cache = {}
Cache_DEFAULT = {
    'CelesteVersion': '1.4.0.0',
    'Everest': False,
    'Hash': 'f1c4967fa8f1f113858327590e274b69',
}

def command(func):
    command = func.__name__.replace('_', '-')
    if command in Commands:
        raise ValueError(f'Duplicate command: {command}')
    Commands[command] = func

def splitFlags(args) -> Tuple[List[str], Dict[str, str]]:
    pass

def loadInstalls():
    global Installs
    Installs, exists = loadConfig(INSTALLS_FILE, Installs_DEFAULT)
    return exists

def saveInstalls():
    saveConfig(Installs, INSTALLS_FILE)

def loadCache() -> bool: 
    global Cache
    Cache, exists = loadConfig(CACHE_FILE, Cache_DEFAULT)
    return exists

def saveCache():
    saveConfig(Cache, CACHE_FILE)

def loadConfig(file, default) -> Tuple[configparser.ConfigParser, bool]:
    config = configparser.ConfigParser()
    file = resolvePath(file)
    if os.path.isfile(file):
        config.read(file)
        exists = True
    else:
        config['DEFAULT'] = default
        os.makedirs(resolvePath(USER_FOLDER), exist_ok=True)
        with open(file, 'x') as f:
            config.write(f)
        exists = False
    return config, exists

def saveConfig(config, file) -> bool:
    with open(resolvePath(file), 'w') as f:
        config.write(f)

def loadPlugins():
    for file in os.listdir(resolvePath(PLUGIN_FOLDER)):
        name, ext = os.path.splitext(file)
        if ext == '.py':
            plugin = importlib.import_module(f'{PLUGIN_MODULE}.{name}')
            if not (hasattr(plugin, 'PREFIX') and hasattr(plugin, 'main')):
                print(f'Plugin {plugin} not loaded:')
                print('Plugins must include a \'PREFIX\' constant and \'main\' function')
                continue
            Commands[plugin.PREFIX] = plugin.main

def resolvePath(*paths: str, local=False) -> str:
    root = ""
    if local:
        root = os.path.dirname(__file__)
    return os.path.join(root, *paths)

def getMD5Hash(path: str) -> str:
    with open(path, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()

def parseVersionSpec(string: str) -> int:
    if string.startswith('1.') and string.endswith('.0'):
        string = string[2:-2]
    if string.isdigit():
        buildnumber = int(string)
    else:
        buildnumber = getLatestBuild(string)

    return buildnumber
    
def getLatestBuild(branch: str) -> int:
    builds = json.loads(urllib.request.urlopen('https://dev.azure.com/EverestAPI/Everest/_apis/build/builds?api-version=6.0').read())['value']
    for build in builds:
        if not (build['status'] == 'completed' and build['result'] == 'succeeded'):
            continue
        if not (build['reason'] == 'manual' or build['reason'] == 'individualCI'):
            continue

        if not branch or branch == build['sourceBranch'].replace('refs/heads/', ''):
            try:
                return int(build['id']) + 700
            except:
                pass
    return False

def downloadBuild(build: int):
    return urllib.request.urlopen(f'https://dev.azure.com/EverestAPI/Everest/_apis/build/builds/{build - 700}/artifacts?artifactName=olympus-build&api-version=6.0&%24format=zip')
#endregion

#region COMMANDS
@command
def help(args):
    print('Commands:')
    pprint(Commands.keys())

@command
def add(args):
    path = os.path.abspath(args[1])
    installPath = ''
    if os.path.isfile(path) and os.path.splitext(path)[1] == '.exe':
        installPath = path
    elif os.path.isdir(path) and os.path.isfile(os.path.join(path, 'Celeste.exe')):
        installPath = os.path.join(path, 'Celeste.exe')

    if installPath:
        Installs[args[0]] = {
            'Path': installPath,
        }
        print(f'Found Celeste.exe: {installPath}')
    else:
        print(f'Could not find Celeste.exe {installPath}')

@command
def rename(args):
    if Installs.has_section(args[0]):
        Installs[args[1]] = Installs.pop(args[0])

@command
def set_path(args):
    # use add command stuff for this
    Installs[args[0]]['Path'] = resolvePath(args[1])

@command
def set_branch(args):
    Installs[args[0]]['preferredBranch'] = args[1]

@command
def list(args):
    print('Current Installs:')
    pprint(Installs.sections())

@command
def info(args):
    path = Installs[args[0]]['Path']
    
    peHash = getMD5Hash(path)
    if Cache.has_section(args[0]) and Cache[args[0]].get('Hash', '') == peHash:
        print('Found valid cache')
        print('Hash: ' + peHash)
        print('Everest' if Cache[args[0]].getboolean('Everest') else 'Vanilla')
        return
    elif (version := VanillaHashes.get(peHash, '')) != '':
        print('Vanilla match')
        print('Hash: ' + peHash)
        Cache[args[0]] = {
            'CelesteVersion': version,
            'Hash': peHash,
            'Everest': False,
        }
        return

    infoCache = {}
    print('Hash: ' + peHash)
    infoCache['Hash'] = peHash

    pe = dnfile.dnPE(path, fast_load=True)
    pe.parse_data_directories(directories=DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR'])
    stringHeap = pe.net.metadata.streams_list[1]
    
    i = 0
    foundEverest = False
    while i < len(stringHeap.__data__):
        string = stringHeap.get(i)
        if string.startswith('EverestBuild'):
            print('Everest Build: ' + string[len('EverestBuild'):])
            foundEverest = True
            break
        i += max(len(string), 1)

    if not foundEverest:
        print('Vanilla')
    infoCache['Everest'] = foundEverest

    Cache[args[0]] = infoCache

@command
def install(args):
    path = Installs[args[0]]['Path']
    success = False
    
    build = parseVersionSpec(args[1])
    if build:
        response = downloadBuild(build)
    
    if response and response:
        artifactPath = os.path.join(os.path.dirname(path), 'olympus-build.zip')
        print(f'Downloading to file: {artifactPath}...')
        with open(artifactPath, 'wb') as file:
            file.write(response.read())

        with open(artifactPath, 'rb') as file:
            print(f'Opening file {artifactPath}...')
            with zipfile.ZipFile(file, mode='r') as artifact:
                with zipfile.ZipFile(artifact.open('olympus-build/build.zip')) as build:
                    print('Extracting files...')
                    build.extractall(os.path.dirname(path))
                    success = True

    if success:
        print('Success! Starting MiniInstaller:')
        installer_ret = subprocess.run(os.path.join(os.path.dirname(path), 'MiniInstaller.exe'), cwd=os.path.dirname(path))
        if installer_ret.returncode == 0:
            print('Computing new hash for cache...')
            peHash = getMD5Hash(path)
            Cache[args[0]].update({
                'Hash': peHash,
                'Everest': str(True),
            })

@command
def launch(args):
    if os.path.exists(Installs[args[0]]['Path']):
        args[0] = Installs[args[0]]['Path']
        subprocess.Popen(args)
#endregion

#region MAIN
def main():
    if (len(sys.argv) < 2):
        Commands['help']()
        return
    
    Commands[sys.argv[1]](sys.argv[2:])


if __name__ == '__main__':
    loadInstalls()
    loadCache()
    loadPlugins()
    main()
    saveInstalls()
    saveCache()
#endregion