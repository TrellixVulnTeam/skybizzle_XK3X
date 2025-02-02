import io
import logging

import discord
from redbot.core import Config
from redbot.core import checks
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify

from .serialize import deserialize_embed, serialize_embed
from cog_shared.sinbad_libs.time_utils import parse_time
from .yaml_parse import embed_from_userstr

log = logging.getLogger("red.sinbadcogs.embedmaker")


# TODO: Remove this supression after handling `embed_from_userstr`
# noinspection PyBroadException
class EmbedMaker(commands.Cog):
    """
    Storable, recallable, embed maker
    """

    __version__ = "5.0.1"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.init_custom("EMBED", 2)
        self.config.register_custom("EMBED", embed={}, owner=None)
        self.config.register_guild(active=True)

    @commands.group(name="embed", autohelp=True)
    async def _embed(self, ctx: commands.Context):
        """
        Embed commands
        """
        pass

    @checks.guildowner()
    @commands.guild_only()
    @_embed.command(name="editmsg")
    async def editmessage_embed(
        self, ctx: commands.Context, message: discord.Message, embedname: str
    ):
        """
        Edits an existing message by channelID-messageID to have an embed (must be saved)
        """

        if message.guild != ctx.guild:
            return

        if message.author != ctx.guild.me:
            return await ctx.send("Not my message, can't edit")

        if await self.config.custom("EMBED", ctx.guild.id, embedname).owner():
            data = await self.config.custom("EMBED", ctx.guild.id, embedname).embed()
            embed = deserialize_embed(data)
        else:
            return await ctx.send("No embed by that name here")

        try:
            await message.edit(embed=embed)
        except discord.HTTPException:
            pass  # TODO
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @_embed.command(name="advmake")
    async def make_adv(self, ctx: commands.Context, name: str, *, data: str):
        """
        makes an embed from valid yaml

        Note: Fields should be provided as nested key: value pairs,
        keys indicating position.
        """
        name = name.lower()
        group = self.config.custom("EMBED", ctx.guild.id, name)
        if await group.owner() not in (ctx.author.id, None):
            return await ctx.maybe_send_embed("An embed with that name already exists!")

        try:
            e = await embed_from_userstr(ctx, data)
            await ctx.send(embed=e)
        except discord.HTTPException:
            await ctx.maybe_send_embed("Discord didn't like that embed")
        except Exception:
            await ctx.maybe_send_embed("There was something wrong with that input")
        else:
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @_embed.command(name="uploadnostore")
    @commands.bot_has_permissions(embed_links=True)
    async def no_storage_upload(self, ctx):
        """
        Quickly make an embed without intent to store
        """
        try:
            with io.BytesIO() as fp:
                await ctx.message.attachments[0].save(fp)
                data = fp.read()
                data = data.decode("utf-8")
        except IndexError:
            return await ctx.send("You need to upload a file")

        try:
            e = await embed_from_userstr(ctx, data)
            await ctx.send(embed=e)
        except discord.HTTPException:
            await ctx.send("Discord didn't like that embed", delete_after=30)
        except Exception:
            await ctx.send("There was something wrong with that input", delete_after=30)

    @_embed.command(name="advnostore")
    @commands.bot_has_permissions(embed_links=True)
    async def no_storage_adv(self, ctx, *, data):
        """
        Quickly make an embed without intent to store
        """
        try:
            e = await embed_from_userstr(ctx, data)
            await ctx.send(embed=e)
        except discord.HTTPException:
            await ctx.send("Discord didn't like that embed", delete_after=30)
        except Exception:
            await ctx.send("There was something wrong with that input", delete_after=30)

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @_embed.command(name="upload")
    async def make_upload(self, ctx: commands.Context, name: str):
        """
        makes an embed from valid yaml file upload

        Note: Fields should be provided as nested key: value pairs,
        keys indicating position.
        """
        name = name.lower()
        group = self.config.custom("EMBED", ctx.guild.id, name)
        if await group.owner() not in (ctx.author.id, None):
            return await ctx.maybe_send_embed("An embed with that name already exists!")

        try:
            with io.BytesIO() as fp:
                await ctx.message.attachments[0].save(fp)
                data = fp.read().decode("utf-8")
        except IndexError:
            return await ctx.send("You need to upload a file")

        try:
            e = await embed_from_userstr(ctx, data)
            await ctx.send(embed=e)
        except discord.HTTPException:
            await ctx.maybe_send_embed("Discord didn't like that embed")
        except Exception:
            await ctx.maybe_send_embed("There was something wrong with that input")
        else:
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @commands.bot_has_permissions(embed_links=True)
    @checks.is_owner()
    @_embed.command(name="uploadglobal")
    async def make_global_upload(self, ctx: commands.Context, name: str):
        """
        makes an embed from valid yaml file upload

        Note: Fields should be provided as nested key: value pairs,
        keys indicating position.
        """

        try:
            with io.BytesIO() as fp:
                await ctx.message.attachments[0].save(fp)
                data = fp.read().decode("utf-8")
        except IndexError:
            return await ctx.send("You need to upload a file")

        try:
            name = name.lower()
            e = await embed_from_userstr(ctx, data)
            await ctx.send(embed=e)
        except discord.HTTPException:
            await ctx.maybe_send_embed("Discord didn't like that embed")
        except Exception:
            await ctx.maybe_send_embed("There was something wrong with that input")
        else:
            await self.config.custom("EMBED", "GLOBAL", name).owner.set(ctx.author.id)
            await self.config.custom("EMBED", "GLOBAL", name).embed.set(
                serialize_embed(e)
            )

    @commands.bot_has_permissions(embed_links=True)
    @_embed.command(name="event")
    async def event_timestamp(self, ctx: commands.Context, event: str, *, time: str):
        """
        Creates an event embed with localized timestamp in the current channel

        If you need your event to span multiple words, surround it in quotes
        """
        try:
            timestamp = parse_time(time)
        except Exception:
            return await ctx.send("I could not parse that timestamp")
        color = ctx.guild.me.color if ctx.guild else discord.Embed.Empty
        author = ctx.author
        avatar = ctx.author.avatar_url
        embed = discord.Embed(description=event, color=color, timestamp=timestamp)
        embed.set_author(
            name=f"Event created by {author.display_name}", icon_url=avatar
        )
        embed.set_footer(text="Event local time: ")
        await ctx.send(embed=embed)

    @commands.bot_has_permissions(embed_links=True)
    @checks.is_owner()
    @_embed.command(name="advmakeglobal")
    async def make_global_adv(self, ctx: commands.Context, name: str, *, data: str):
        """
        makes an embed from valid yaml

        Note: Fields should be provided as nested key: value pairs,
        keys indicating position.
        """
        try:
            name = name.lower()
            e = await embed_from_userstr(ctx, data)
            await ctx.send(embed=e)
        except discord.HTTPException:
            await ctx.maybe_send_embed("Discord didn't like that embed")
        except Exception:
            await ctx.maybe_send_embed("There was something wrong with that input")
        else:
            await self.config.custom("EMBED", "GLOBAL", name).owner.set(ctx.author.id)
            await self.config.custom("EMBED", "GLOBAL", name).embed.set(
                serialize_embed(e)
            )

    @commands.guild_only()
    @_embed.command(name="make")
    async def _make(self, ctx: commands.Context, name: str, *, content: str):
        """
        makes an embed
        """
        name = name.lower()
        group = self.config.custom("EMBED", ctx.guild.id, name)
        if await group.owner() not in (ctx.author.id, None):
            return await ctx.maybe_send_embed("An embed with that name already exists!")

        e = discord.Embed(description=content)
        try:
            await ctx.send(embed=e)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.maybe_send_embed("Discord didn't like that embed")
        else:
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @checks.is_owner()
    @_embed.command(name="makeglobal")
    async def make_global(self, ctx: commands.Context, name: str, *, content: str):
        """
        make a global embed
        """
        name = name.lower()
        group = self.config.custom("EMBED", "GLOBAL", name)
        try:
            e = discord.Embed(description=content)
            await ctx.send(embed=e)
        except ValueError:
            await ctx.maybe_send_embed("There was something wrong with that input")
        except (discord.Forbidden, discord.HTTPException):
            await ctx.maybe_send_embed("Discord didn't like that embed")
        else:
            await group.owner.set(ctx.author.id)
            await group.embed.set(serialize_embed(e))

    @_embed.command(name="list")
    async def _list(self, ctx: commands.Context):
        """
        lists the embeds here
        """
        embed_dict = await self.config.custom("EMBED").all()

        if ctx.guild:
            local_embeds = list(sorted(embed_dict.get(str(ctx.guild.id), {}).keys()))
        else:
            local_embeds = []

        global_embeds = list(sorted(embed_dict.get("GLOBAL", {}).keys()))

        if not local_embeds and not global_embeds:
            return await ctx.maybe_send_embed("No embeds available here.")

        if local_embeds:
            local_embeds.insert(0, "Local Embeds:")
            if global_embeds:
                local_embeds.append("\n")
        if global_embeds:
            global_embeds.insert(0, "Global Embeds:")
        output = "\n".join(local_embeds + global_embeds)

        for page in pagify(output):
            await ctx.maybe_send_embed(page)

    @commands.guild_only()
    @_embed.command(name="remove")
    async def _remove(self, ctx: commands.Context, name: str):
        """
        removes an embed
        """
        name = name.lower()
        group = self.config.custom("EMBED", ctx.guild.id, name)
        if not await group.owner():
            return await ctx.maybe_send_embed("No such embed")
        if any(  # who created, bot owner, admins, mods
            (
                await group.owner() == ctx.author.id,
                await ctx.bot.is_owner(ctx.author),
                await ctx.bot.is_admin(ctx.author),
                await ctx.bot.is_mod(ctx.author),
            )
        ):
            await group.clear()
            await ctx.tick()

    @checks.is_owner()
    @_embed.command(name="rmglobal")
    async def remove_global(self, ctx: commands.Context, name: str):
        """
        removes a global embed
        """
        name = name.lower()
        await self.config.custom("EMBED", "GLOBAL", name).clear()
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @_embed.command()
    async def drop(self, ctx: commands.Context, name: str):
        """
        drops an embed here
        """
        name = name.lower()
        try:
            await self.get_and_send(ctx.channel, ctx.guild.id, name)
        except (discord.Forbidden, discord.HTTPException) as e:
            log.error(e)

    @checks.is_owner()
    @_embed.command(name="dropglobal")
    async def drop_global(self, ctx: commands.Context, name: str):
        """
        drop a global embed here
        """
        name = name.lower()
        try:
            await self.get_and_send(ctx.channel, "GLOBAL", name)
        except (discord.Forbidden, discord.HTTPException) as e:
            log.error(e)

    @checks.admin()
    @commands.guild_only()
    @_embed.command()
    async def dm(self, ctx: commands.Context, name: str, user: discord.Member):
        """
        DMs an embed
        """
        name = name.lower()
        try:
            x = await self.get_and_send(user, ctx.guild.id, name)
        except discord.Forbidden:
            await ctx.maybe_send_embed(
                "User has disabled DMs from this server or blocked me"
            )
        else:
            if x is not None:
                await ctx.tick()

    @checks.admin()
    @_embed.command()
    async def dmglobal(self, ctx: commands.Context, name: str, user: discord.Member):
        """
        DMs a global embed
        """
        name = name.lower()
        try:
            x = await self.get_and_send(user, "GLOBAL", name)
        except discord.Forbidden:
            await ctx.maybe_send_embed(
                "User has disabled DMs from this server or blocked me"
            )
        else:
            if x is not None:
                await ctx.tick()

    @commands.guild_only()
    @_embed.command()
    async def dmme(self, ctx: commands.Context, name: str):
        """
        DMs an embed
        """
        name = name.lower()
        try:
            x = await self.get_and_send(ctx.author, ctx.guild.id, name)
        except discord.Forbidden:
            await ctx.maybe_send_embed(
                "User has disabled DMs from this server or blocked me"
            )
        else:
            if x is not None:
                await ctx.tick()

    @_embed.command()
    async def dmmeglobal(self, ctx: commands.Context, name: str):
        """
        DMs a global embed
        """
        name = name.lower()
        try:
            x = await self.get_and_send(ctx.author, "GLOBAL", name)
        except discord.Forbidden:
            await ctx.maybe_send_embed(
                "User has disabled DMs from this server or blocked me"
            )
        else:
            if x is not None:
                await ctx.tick()

    @commands.guild_only()
    @_embed.command(name="frommsg")
    async def from_message(self, ctx: commands.Context, name: str, _id: int):
        """
        Store's a message's embed
        """
        name = name.lower()
        try:
            e = (await ctx.channel.fetch_message(_id)).embeds[0]
        except Exception:
            return

        await self.config.custom("EMBED", ctx.guild.id, name).embed.set(
            serialize_embed(e)
        )
        await self.config.custom("EMBED", ctx.guild.id, name).owner.set(ctx.author.id)
        await ctx.tick()

    @checks.is_owner()
    @_embed.command(name="globalfrommsg")
    async def global_from_message(self, ctx: commands.Context, name: str, _id: int):
        """
        stores a message's embed
        """
        name = name.lower()
        try:
            e = (await ctx.channel.fetch_message(_id)).embeds[0]
        except Exception:
            return

        await self.config.custom("EMBED", "GLOBAL", name).embed.set(serialize_embed(e))
        await self.config.custom("EMBED", "GLOBAL", name).owner.set(ctx.author.id)
        await ctx.tick()

    async def get_and_send(self, where, *identifiers):
        if await self.config.custom("EMBED", *identifiers).owner():
            data = await self.config.custom("EMBED", *identifiers).embed()
            embed = deserialize_embed(data)
            return await where.send(embed=embed)
