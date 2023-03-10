# reminders_lists.py
"""Contains reminder list commands"""

from typing import List, Optional, Union

import discord
from discord import utils
from discord.ext import commands

from database import reminders, users
from resources import emojis, functions, exceptions, settings, strings, views


# -- Commands ---
async def command_list(
    bot: discord.Bot,
    ctx: Union[commands.Context, discord.ApplicationContext, discord.Message],
    user: Optional[discord.User] = None
) -> None:
    """Lists all active reminders"""
    user = user if user is not None else ctx.author
    try:
        user_settings: users.User = await users.get_user(user.id)
    except exceptions.FirstTimeUserError:
        if user == ctx.author:
            raise
        else:
            await functions.reply_or_respond(ctx, 'This user is not registered with me.', True)
        return
    try:
        custom_reminders = list(await reminders.get_active_reminders(user.id, 'custom'))
    except exceptions.NoDataFoundError:
        custom_reminders = []
    try:
        user_reminders = list(await reminders.get_active_reminders(user.id))
    except:
        user_reminders = []
    embed = await embed_reminders_list(bot, user, user_reminders)
    view = views.RemindersListView(bot, ctx, user, user_reminders, custom_reminders, embed_reminders_list)
    if isinstance(ctx, discord.ApplicationContext):
        interaction_message = await ctx.respond(embed=embed, view=view)
    else:
        interaction_message = await ctx.reply(embed=embed, view=view)
    view.interaction_message = interaction_message
    await view.wait()


# -- Embeds ---
async def embed_reminders_list(bot: discord.Bot, user: discord.User, user_reminders: List[reminders.Reminder],
                               show_timestamps: Optional[bool] = False) -> discord.Embed:
    """Embed with active reminders"""
    current_time = utils.utcnow().replace(microsecond=0)
    reminders_commands_list = []
    reminders_boosts_list = []
    reminders_custom_list = []
    for reminder in user_reminders:
        if reminder.activity == 'custom':
            reminders_custom_list.append(reminder)
        elif reminder.activity in strings.ACTIVITIES_BOOSTS:
            reminders_boosts_list.append(reminder)
        else:
            reminders_commands_list.append(reminder)

    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.name}\'s active reminders'
    )
    if not user_reminders:
        embed.description = f'{emojis.BP} You have no active reminders'
    if reminders_commands_list:
        field_command_reminders = ''
        for reminder in reminders_commands_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**{timestring}**'
            activity = reminder.activity.replace('-',' ').capitalize()
            field_command_reminders = (
                f'{field_command_reminders}\n'
                f'{emojis.BP} **`{activity}`** ({reminder_time})'
            )
        embed.add_field(name='Commands', value=field_command_reminders.strip(), inline=False)
    if reminders_boosts_list:
        field_boosts_reminders = ''
        for reminder in reminders_boosts_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**{timestring}**'
            activity = reminder.activity.replace('-',' ').capitalize()
            field_boosts_reminders = (
                f'{field_boosts_reminders}\n'
                f'{emojis.BP} **`{activity}`** ({reminder_time})'
            )
        embed.add_field(name='Boosts', value=field_boosts_reminders.strip(), inline=False)
    if reminders_custom_list:
        field_custom_reminders = ''
        for reminder in reminders_custom_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**{timestring}**'
            custom_id = f'0{reminder.custom_id}' if reminder.custom_id <= 9 else reminder.custom_id
            field_custom_reminders = (
                f'{field_custom_reminders}\n'
                f'{emojis.BP} **`{custom_id}`** ({reminder_time}) - {reminder.message}'
            )
        embed.add_field(name='Custom', value=field_custom_reminders.strip(), inline=False)
    return embed