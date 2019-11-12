# InstantCommands by retke, aka El Laggron
# Idea by Malarne

import discord
import asyncio
import traceback
import textwrap
import logging
import os

from redbot.core import commands
from redbot.core import checks
from redbot.core import Config
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import pagify

log = logging.getLogger("laggron.instantcmd")
log.setLevel(logging.DEBUG)

BaseCog = getattr(commands, "Cog", object)

# Red 3.0 backwards compatibility, thanks Sinbad
listener = getattr(commands.Cog, "listener", None)
if listener is None:

    def listener(name=None):
        return lambda x: x


class FakeListener:
    """
    A fake listener used to remove the extra listeners.

    This is needed due to how extra listeners works, and how the cog stores these.
    When adding a listener to the list, we get its ID. Then, when we need to remove\
    the listener, we call this fake class with that ID, so discord.py thinks this is\
    that listener.

    Credit to mikeshardmind for finding this solution. For more info, please look at this issue:
    https://github.com/Rapptz/discord.py/issues/1284
    """

    def __init__(self, idx):
        self.idx = idx

    def __eq__(self, function):
        return self.idx == id(function)


class InstantCommands(BaseCog):
    """
    Generate a new command from a code snippet, without making a new cog.

    Report a bug or ask a question: https://discord.gg/AVzjfpR
    Full documentation and FAQ: https://laggrons-dumb-cogs.readthedocs.io/instantcommands.html
    """

    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(self, 260)

        def_global = {"commands": {}, "updated_body": False}
        self.data.register_global(**def_global)
        self.listeners = {}

        # these are the availables values when creating an instant cmd
        self.env = {"bot": self.bot, "discord": discord, "commands": commands, "checks": checks}
        # resume all commands and listeners
        bot.loop.create_task(self.resume_commands())
        self._init_logger()

    __author__ = ["retke (El Laggron)"]
    __version__ = "1.0.1"

    def _init_logger(self):
        log_format = logging.Formatter(
            f"%(asctime)s %(levelname)s {self.__class__.__name__}: %(message)s",
            datefmt="[%d/%m/%Y %H:%M]",
        )
        # logging to a log file
        # file is automatically created by the module, if the parent foler exists
        cog_path = cog_data_path(self)
        if cog_path.exists():
            log_path = cog_path / f"{os.path.basename(__file__)[:-3]}.log"
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(log_format)
            log.addHandler(file_handler)

        # stdout stuff
        stdout_handler = logging.StreamHandler()
        stdout_handler.setFormatter(log_format)
        # if --debug flag is passed, we also set our debugger on debug mode
        if logging.getLogger("red").isEnabledFor(logging.DEBUG):
            stdout_handler.setLevel(logging.DEBUG)
        else:
            stdout_handler.setLevel(logging.INFO)
        log.addHandler(stdout_handler)
        self.stdout_handler = stdout_handler

    # def get_config_identifier(self, name):
    # """
    # Get a random ID from a string for Config
    # """

    # random.seed(name)
    # identifier = random.randint(0, 999999)
    # self.env["config"] = Config.get_conf(self, identifier)

    def get_function_from_str(self, command, name=None):
        """
        Execute a string, and try to get a function from it.
        """

        # self.get_config_identifier(name)
        to_compile = "def func():\n%s" % textwrap.indent(command, "  ")
        exec(to_compile, self.env)
        result = self.env["func"]()
        if not result:
            raise RuntimeError("Nothing detected. Make sure to return a command or a listener")
        return result

    def load_command_or_listener(self, function):
        """
        Add a command to discord.py or create a listener
        """

        if isinstance(function, commands.Command):
            self.bot.add_command(function)
            log.debug(f"Added command {function.name}")
        else:
            self.bot.add_listener(function)
            self.listeners[function.__name__] = id(function)
            log.debug(f"Added listener {function.__name__} (ID of the function: {id(function)})")

    async def resume_commands(self):
        """
        Load all instant commands made.
        This is executed on load with __init__
        """

        _commands = await self.data.commands()
        for name, command_string in _commands.items():
            function = self.get_function_from_str(command_string, name)
            self.load_command_or_listener(function)

    async def remove_commands(self):
        async with self.data.commands() as _commands:
            for command in _commands:
                if command in self.listeners:
                    # remove a listener
                    self.bot.remove_listener(FakeListener(self.listeners[command]), name=command)
                    log.debug(f"Removed listener {command} due to cog unload.")
                else:
                    # remove a command
                    self.bot.remove_command(command)
                    log.debug(f"Removed command {command} due to cog unload.")

    # from DEV cog, made by Cog Creators (tekulvw)
    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @checks.is_owner()
    @commands.group(aliases=["instacmd", "instantcommand"])
    async def instantcmd(self, ctx):
        """Instant Commands cog management"""
        pass

    @instantcmd.command()
    async def create(self, ctx):
        """
        Instantly generate a new command from a code snippet.

        If you want to make a listener, give its name instead of the command name.
        """
        await ctx.send(
            "You're about to create a new command. \n"
            "Your next message will be the code of the command. \n\n"
            "If this is the first time you're adding instant commands, "
            "please read the wiki:\n"
            "<https://laggrons-dumb-cogs.readthedocs.io/instantcommands.html>"
        )
        pred = MessagePredicate.same_context(ctx)
        try:
            response = await self.bot.wait_for("message", timeout=900, check=pred)
        except asyncio.TimeoutError:
            await ctx.send("Question timed out.")
            return

        function_string = self.cleanup_code(response.content)
        try:
            function = self.get_function_from_str(function_string)
        except Exception as e:
            exception = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            message = (
                f"An exception has occured while compiling your code:\n```py\n{exception}\n```"
            )
            for page in pagify(message):
                await ctx.send(page)
            return
        # if the user used the command correctly, we should have one async function

        if isinstance(function, commands.Command):
            async with self.data.commands() as _commands:
                if function.name in _commands:
                    await ctx.send("Error: That listener is already registered.")
                    return
            try:
                self.bot.add_command(function)
            except Exception as e:
                exception = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                message = (
                    "An expetion has occured while adding the command to discord.py:\n"
                    f"```py\n{exception}\n```"
                )
                for page in pagify(message):
                    await ctx.send(page)
                return
            else:
                async with self.data.commands() as _commands:
                    _commands[function.name] = function_string
                await ctx.send(f"The command `{function.name}` was successfully added.")

        else:
            async with self.data.commands() as _commands:
                if function.__name__ in _commands:
                    await ctx.send("Error: That listener is already registered.")
                    return
            try:
                self.bot.add_listener(function)
            except Exception as e:
                exception = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                message = (
                    "An expetion has occured while adding the listener to discord.py:\n"
                    f"```py\n{exception}\n```"
                )
                for page in pagify(message):
                    await ctx.send(page)
                return
            else:
                self.listeners[function.__name__] = id(function)
                async with self.data.commands() as _commands:
                    _commands[function.__name__] = function_string
                await ctx.send(f"The listener `{function.__name__}` was successfully added.")

    @instantcmd.command(aliases=["del", "remove"])
    async def delete(self, ctx, command_or_listener: str):
        """
        Remove a command or a listener from the registered instant commands.
        """
        command = command_or_listener
        async with self.data.commands() as _commands:
            if command not in _commands:
                await ctx.send("That instant command doesn't exist")
                return
            if command in self.listeners:
                text = "listener"
                self.bot.remove_listener(FakeListener(self.listeners[command]), name=command)
            else:
                text = "command"
                self.bot.remove_command(command)
            _commands.pop(command)
        await ctx.send(f"The {text} `{command}` was successfully removed.")

    @instantcmd.command()
    async def info(self, ctx, command: str = None):
        """
        List all existing commands made using Instant Commands.

        If a command name is given and found in the Instant commands list, the code will be shown.
        """

        if not command:
            message = "List of instant commands:\n" "```Diff\n"
            _commands = await self.data.commands()

            for name, command in _commands.items():
                message += f"+ {name}\n"
            message += (
                "```\n"
                "*Hint:* You can show the command source code by typing "
                f"`{ctx.prefix}instacmd info <command>`"
            )

            if _commands == {}:
                await ctx.send("No instant command created.")
                return

            for page in pagify(message):
                await ctx.send(message)

        else:
            _commands = await self.data.commands()

            if command not in _commands:
                await ctx.send("Command not found.")
                return

            message = (
                f"Source code for `{ctx.prefix}{command}`:\n"
                + "```Py\n"
                + _commands[command]
                + "```"
            )
            for page in pagify(message):
                await ctx.send(page)

    @commands.command(hidden=True)
    @checks.is_owner()
    async def instantcmdinfo(self, ctx):
        """
        Get informations about the cog.
        """
        await ctx.send(
            "Laggron's Dumb Cogs V3 - instantcmd\n\n"
            "Version: {0.__version__}\n"
            "Author: {0.__author__}\n"
            "Github repository: https://github.com/retke/Laggrons-Dumb-Cogs/tree/v3\n"
            "Discord server: https://discord.gg/AVzjfpR\n"
            "Documentation: http://laggrons-dumb-cogs.readthedocs.io/\n\n"
            "Support my work on Patreon: https://www.patreon.com/retke"
        ).format(self)

    @listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, commands.CommandInvokeError):
            return
        if not ctx.command.cog_name == self.__class__.__name__:
            # That error doesn't belong to the cog
            return
        async with self.data.commands() as _commands:
            if ctx.command.name in _commands:
                log.info(f"Error in instant command {ctx.command.name}.", exc_info=error.original)
                return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "I need the `Add reactions` and `Manage messages` in the "
                "current channel if you want to use this command."
            )
        log.removeHandler(self.stdout_handler)  # remove console output since red also handle this
        log.error(
            f"Exception in command '{ctx.command.qualified_name}'.\n\n", exc_info=error.original
        )
        log.addHandler(self.stdout_handler)  # re-enable console output for warnings

    # correctly unload the cog
    def __unload(self):
        self.cog_unload()

    def cog_unload(self):
        log.debug("Unloading cog...")

        async def unload():
            # removes commands and listeners
            await self.remove_commands()

            # remove all handlers from the logger, this prevents adding
            # multiple times the same handler if the cog gets reloaded
            log.handlers = []

        # I am forced to put everything in an async function to execute the remove_commands
        # function, and then remove the handlers. Using loop.create_task on remove_commands only
        # executes it after removing the log handlers, while it needs to log...
        self.bot.loop.create_task(unload())
