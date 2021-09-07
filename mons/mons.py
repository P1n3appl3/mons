#!/usr/bin/env python

import click

from contextlib import AbstractContextManager

from mons.utils import *
from mons.config import *

class UserInfo(AbstractContextManager):
    def __enter__(self):
        self.config = loadConfig(CONFIG_FILE, Config_DEFAULT)
        self.installs = loadConfig(INSTALLS_FILE, Installs_DEFAULT)
        self.cache = loadConfig(CACHE_FILE, Cache_DEFAULT)
        if not self.config.has_section('user'):
            self.config['user'] = {}
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        saveConfig(self.config, CONFIG_FILE)
        saveConfig(self.installs, INSTALLS_FILE)
        saveConfig(self.cache, CACHE_FILE)


@click.group()
@click.pass_context
@click.version_option()
def cli(ctx: click.Context):
    ctx.obj = ctx.with_resource(UserInfo())

from mons.commands import *