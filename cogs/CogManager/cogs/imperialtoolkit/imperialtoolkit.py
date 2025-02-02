import discord
import os
import sys
import cpuinfo
import platform
import lavalink

from datetime import datetime

from redbot.core import version_info as red_version_info, commands

from redbot.core.utils.chat_formatting import humanize_timedelta

from redbot.cogs.audio.manager import JAR_BUILD as jarversion

import psutil

if sys.platform == "linux":
    import distro


class ImperialToolkit(commands.Cog):
    """Collection of useful commands and tools."""

    __author__ = "kennnyshiwa"

    def __init__(self, bot):
        self.bot = bot
        lavalink.register_event_listener(self.event_handler)
    
    def cog_unload(self):
        lavalink.unregister_event_listener(self.event_handler)
    
    async def event_handler(self, player, event_type, extra):  # To delete at next audio update.
        # Thanks Draper#6666
        if event_type == lavalink.LavalinkEvents.TRACK_START:
            self.bot.counter["tracks_played"] += 1

    # Planned for next audio update.
    # @commands.Cog.listener()
    # async def on_track_start(self, guild: discord.Guild, track, reuester):
    #     self.bot.counter["tracks_played"] += 1

    @staticmethod
    def _size(num):
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1024.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1024.0
        return "{0:.1f}{1}".format(num, "YB")

    def get_bot_uptime(self):
        delta = datetime.utcnow() - self.bot.uptime
        uptime = humanize_timedelta(timedelta=delta)
        return uptime

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def botstat(self, ctx):
        """Get stats about the bot including messages sent and recieved and other info."""
        async with ctx.typing():
            cpustats = psutil.cpu_percent()
            ramusage = psutil.virtual_memory()
            netusage = psutil.net_io_counters()
            width = max([len(self._size(n)) for n in [netusage.bytes_sent, netusage.bytes_recv]])
            net_ios = (
                "\u200b" "\n"
                "{sent_text:<11}: {sent:>{width}}\n"
                "{recv_text:<11}: {recv:>{width}}"
            ).format(
                sent_text="Bytes sent",
                sent=self._size(netusage.bytes_sent),
                width=width,
                recv_text="Bytes recv",
                recv=self._size(netusage.bytes_recv),
            )

            IS_WINDOWS = os.name == "nt"
            IS_MAC = sys.platform == "darwin"
            IS_LINUX = sys.platform == "linux"

            if IS_WINDOWS:
                os_info = platform.uname()
                osver = "``{} {} (version {})``".format(
                    os_info.system, os_info.release, os_info.version
                )
            elif IS_MAC:
                os_info = platform.mac_ver()
                osver = "``Mac OSX {} {}``".format(os_info[0], os_info[2])
            elif IS_LINUX:
                os_info = distro.linux_distribution()
                osver = "``{} {}``".format(os_info[0], os_info[1]).strip()
            else:
                osver = "Could not parse OS, report this on Github."

            try:
                cpu = cpuinfo.get_cpu_info()["brand"]
            except:
                cpu = "unknown"
            cpucount = psutil.cpu_count()
            ramamount = psutil.virtual_memory()
            ram_ios = "{0:<11} {1:>{width}}".format("", self._size(ramamount.total), width=width)

            servers = len(self.bot.guilds)
            shards = self.bot.shard_count
            totalusers = sum(len(s.members) for s in self.bot.guilds)
            channels = sum(len(s.channels) for s in self.bot.guilds)
            numcommands = len(self.bot.commands)
            uptime = str(self.get_bot_uptime())
            tracks_played = "`{:,}`".format(self.bot.counter["tracks_played"])
            try:
                total_num = "`{:,}`".format(
                    len(lavalink.active_players())
                )
            except AttributeError:
                total_num = "`{:,}`".format(
                    len([p for p in lavalink.players if p.current is not None])
                )

            red = red_version_info
            dpy = discord.__version__

            embed = discord.Embed(
                title="Bot Stats for {}".format(ctx.bot.user.name),
                description="Below are various stats about the bot and the machine that runs the bot",
                color=await ctx.embed_color(),
            )
            embed.add_field(
                name="\N{DESKTOP COMPUTER} Server Info",
                value=(
                    "CPU usage: `{cpu_usage}%`\n"
                    "RAM usage: `{ram_usage}%`\n"
                    "Network usage: `{network_usage}`\n"
                    "Boot Time: `{boot_time}`\n"
                    "OS: {os}\n"
                    "CPU Info: `{cpu}`\n"
                    "Core Count: `{cores}`\n"
                    "Total Ram: `{ram}`"
                ).format(
                    cpu_usage=str(cpustats),
                    ram_usage=str(ramusage.percent),
                    network_usage=net_ios,
                    boot_time=datetime.fromtimestamp(psutil.boot_time()).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    os=osver,
                    cpu=cpu,
                    cores=cpucount,
                    ram=ram_ios,
                ),
            )
            embed.add_field(
                name="\N{ROBOT FACE} Bot Info",
                value=(
                    "Servers: `{servs:,}`\n"
                    "Users: `{users:,}`\n"
                    "Shard{s}: `{shard:,}`\n"
                    "Playing Music on: `{totalnum:}` servers\n"
                    "Tracks Played: `{tracksplayed:}`\n"
                    "Channels: `{channels:,}`\n"
                    "Number of commands: `{numcommands:,}`\n"
                    "Bot Uptime: `{uptime}`"
                ).format(
                    servs=servers,
                    users=totalusers,
                    s="s" if shards >= 2 else "",
                    shard=shards,
                    totalnum=total_num,
                    tracksplayed=tracks_played,
                    channels=channels,
                    numcommands=numcommands,
                    uptime=uptime,
                ),
                inline=True,
            )
            embed.add_field(
                name="\N{BOOKS} Libraries,",
                value=(
                    "Lavalink: `{lavalink}`\n"
                    "Jar Version: `{jarbuild}`\n"
                    "Red Version: `{redversion}`\n"
                    "Discord.py Version: `{discordversion}`"
                ).format(
                    lavalink=lavalink.__version__,
                    jarbuild=jarversion,
                    redversion=red,
                    discordversion=dpy,
                ),
            )
            embed.set_thumbnail(url=ctx.bot.user.avatar_url_as(static_format="png"))
            embed.set_footer(text=await ctx.bot.db.help.tagline())

        return await ctx.send(embed=embed)
