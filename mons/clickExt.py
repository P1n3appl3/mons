import click

import configparser

class Install(click.ParamType):
    name = 'Install'

    def __init__(self, exist=True, resolve_install=False) -> None:
        super().__init__()
        self.exist = exist
        self.resolve_install = resolve_install

    def convert(self, value, param, ctx):
        installs: configparser.ConfigParser = ctx.obj.installs

        if self.exist:
            if not isinstance(value, configparser.SectionProxy):
                if not installs.has_section(value):
                    self.fail(f'install {value} does not exist.', param, ctx)
                elif self.resolve_install:
                    value = installs[value]
        else:
            if installs.has_section(value):
                self.fail(f'install {value} already exists.', param, ctx)

        return value
