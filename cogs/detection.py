# detection.py
"""Collects and parses Tree messages"""

import re
from typing import Dict, Union

import discord
from discord.ext import commands

from database import users
from processing import chests, clean, cooldowns, daily, fusion, hive, laboratory, profile, prune, quests, tool
from processing import tracking, vote
from resources import exceptions, functions, regex, settings


class DetectionCog(commands.Cog):
    """Cog that contains the detection events"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        if message_before.pinned != message_after.pinned: return
        if message_before.components and not message_after.components: return
        active_component = await check_message_for_active_components(message_after)
        if active_component: await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id not in [settings.GAME_ID, settings.TESTY_ID]: return
        user_settings = None
        embed_data = await parse_embed(message)
        embed_data['embed_user'] = None
        embed_data['embed_user_settings'] = None
        interaction_user = await functions.get_interaction_user(message)
        user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
        if user_id_match:
            embed_data['embed_user'] = message.guild.get_member(int(user_id_match.group(1)))
        if interaction_user is not None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
        if embed_data['embed_user'] is not None:
            if interaction_user is not None and embed_data['embed_user'] == interaction_user:
                embed_user_settings = user_settings
            else:
                try:
                    embed_user_settings: users.User = await users.get_user(embed_data['embed_user'].id)
                except exceptions.FirstTimeUserError:
                    embed_user_settings = None
            embed_data['embed_user_settings'] = embed_user_settings
        return_values = []
        reminder_chests_enabled = getattr(getattr(user_settings, 'reminder_chests', None), 'enabled', True)
        reminder_clean_enabled = getattr(getattr(user_settings, 'reminder_clean', None), 'enabled', True)
        reminder_daily_enabled = getattr(getattr(user_settings, 'reminder_daily', None), 'enabled', True)
        reminder_fusion_enabled = getattr(getattr(user_settings, 'reminder_fusion', None), 'enabled', True)
        reminder_hive_enabled = getattr(getattr(user_settings, 'reminder_hive_energy', None), 'enabled', True)
        reminder_prune_enabled = getattr(getattr(user_settings, 'reminder_prune', None), 'enabled', True)
        reminder_quests_enabled = getattr(getattr(user_settings, 'reminder_quests', None), 'enabled', True)
        reminder_research_enabled = getattr(getattr(user_settings, 'reminder_research', None), 'enabled', True)
        reminder_upgrade_enabled = getattr(getattr(user_settings, 'reminder_upgrade', None), 'enabled', True)
        reminder_vote_enabled = getattr(getattr(user_settings, 'reminder_vote', None), 'enabled', True)
        tracking_enabled = getattr(user_settings, 'tracking_enabled', True)

        # Cooldowns
        add_reaction = await cooldowns.process_message(message, embed_data, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Chests
        if reminder_chests_enabled:
            add_reaction = await chests.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)

        # Clean
        if reminder_clean_enabled or tracking_enabled:
            add_reaction = await clean.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Daily
        if reminder_daily_enabled:
            add_reaction = await daily.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)

        # Fusion
        if reminder_fusion_enabled:
            add_reaction = await fusion.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Hive
        if reminder_hive_enabled:
            add_reaction = await hive.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Prune
        if reminder_prune_enabled:
            add_reaction = await prune.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Laboratory
        if reminder_research_enabled:
            add_reaction = await laboratory.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Profile & Stats
        if reminder_research_enabled or reminder_upgrade_enabled:
            add_reaction = await profile.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)

        # Quests
        if reminder_quests_enabled:
            add_reaction = await quests.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Tool upgrade
        if reminder_upgrade_enabled:
            add_reaction = await tool.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Tracking
        if tracking_enabled:
            add_reaction = await tracking.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)
            
        # Vote
        if reminder_vote_enabled:
            add_reaction = await vote.process_message(message, embed_data, interaction_user, user_settings)
            return_values.append(add_reaction)

        if any(return_values): await functions.add_logo_reaction(message)

# Initialization
def setup(bot):
    bot.add_cog(DetectionCog(bot))


# Functions
async def parse_embed(message: discord.Message) -> Dict[str, str]:
    """Parses all data from an embed into a dictionary.
    All keys are guaranteed to exist and have an empty string as value if not set in the embed.
    """    
    embed_data = {
        'author': {'icon_url': '', 'name': ''},
        'description': '',
        'field0': {'name': '', 'value': ''},
        'field1': {'name': '', 'value': ''},
        'field2': {'name': '', 'value': ''},
        'field3': {'name': '', 'value': ''},
        'field4': {'name': '', 'value': ''},
        'field5': {'name': '', 'value': ''},
        'footer': {'icon_url': '', 'text': ''},
        'title': '',
    }
    if message.embeds:
        embed = message.embeds[0]
        if embed.author:
            if embed.author.icon_url != discord.Embed.Empty:
                embed_data['author']['icon_url'] = embed.author.icon_url
            if embed.author.name != discord.Embed.Empty:
                embed_data['author']['name'] = embed.author.name
        if embed.description:
            embed_data['description'] = embed.description
        if embed.fields:
            try:
                embed_data['field0']['name'] = embed.fields[0].name
                embed_data['field0']['value'] = embed.fields[0].value
            except IndexError:
                pass
            try:
                embed_data['field1']['name'] = embed.fields[1].name
                embed_data['field1']['value'] = embed.fields[1].value
            except IndexError:
                pass
            try:
                embed_data['field2']['name'] = embed.fields[2].name
                embed_data['field2']['value'] = embed.fields[2].value
            except IndexError:
                pass
            try:
                embed_data['field3']['name'] = embed.fields[3].name
                embed_data['field3']['value'] = embed.fields[3].value
            except IndexError:
                pass
            try:
                embed_data['field4']['name'] = embed.fields[4].name
                embed_data['field4']['value'] = embed.fields[4].value
            except IndexError:
                pass
            try:
                embed_data['field5']['name'] = embed.fields[5].name
                embed_data['field5']['value'] = embed.fields[5].value
            except IndexError:
                pass
        if embed.footer:
            if embed.footer.icon_url != discord.Embed.Empty:
                embed_data['footer']['icon_url'] = embed.footer.icon_url
            if embed.footer.text != discord.Embed.Empty:
                embed_data['footer']['text'] = embed.footer.text
        if embed.title:
            embed_data['title'] = embed.title
    return embed_data


async def check_message_for_active_components(message: discord.Message) -> Union[bool, None]:
    """Checks if the message has any active components.
    
    Returns
    -------
    - False if all components are disabled
    - True if at least one component is not disabled OR the message doesn't have any components
    """
    if not message.components: return True
    active_component = False
    for row in message.components:
        for component in row.children:
            if not component.disabled:
                active_component = True
                break
    return active_component