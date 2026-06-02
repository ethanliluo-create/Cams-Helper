import discord
import re
import os
import json
import time
import requests
import random
from discord.ext import commands, tasks
from discord import ui
from discord import app_commands, Interaction, Member

# ===== CONFIG =====
GUILD_ID = 1463054860550148271
INFRACTION_CHANNEL_ID = 1463054861431214163
PROMOTION_CHANNEL_ID = 1463054861431214163

# HR ROLE
HR_ROLE_ID = 1497420696043782334

# CUSTOM LOGO EMOJI
LOGO_EMOJI = "<:Logo:1497710871449964727>"

# EMBED COLORS
DEFAULT_COLOR = 0x25b6ff
INFRACTION_COLOR = 0xa63423
PROMOTION_COLOR = 0x63ab29


# READ ME

# This code is official property of Vertex Systems and you may not claim this code as your own, we would like you to add credit
# wherever is possible but it is not mandatory.

# This code is fitted with instructions and annotations throughout, which you are free to remove. These annotations provide
# instructions on what you should change/replace.

# If you would like anything changed/customised, or you would like to report an issue create a support ticket in the dashboard in Vertex Systems.

# Happy use, and once again please let us know if you encounter any issues! Thanks for purchasing, have a good one.

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="&", intents=intents)

GUILD_ID = discord.Object(id=1463054860550148271)

ticket_openers = {}

ROBLOSECURITY = ""
GROUP_ID = 748351092

# roblox session
def _roblox_session() -> requests.Session:
    s = requests.Session()
    s.cookies[".ROBLOSECURITY"] = ROBLOSECURITY
    return s

def roblox_get_funds(group_id: int) -> dict:
    session = _roblox_session()
    currency_resp = session.get(f"https://economy.roblox.com/v1/groups/{group_id}/currency")
    currency_resp.raise_for_status()
    available = currency_resp.json().get("robux", 0)
    pending = 0
    pending_resp = session.get(f"https://economy.roblox.com/v1/groups/{group_id}/revenue/summary/Month")
    if pending_resp.ok:
        data = pending_resp.json()
        pending = data.get("pendingRobux", 0)
    return {
        "available": available,
        "pending":   pending,
        "total":     available + pending,
    }

# --------------------------------- Review Command ---------------------------------



DESIGNER_ROLE_ID = 1497716042087010394

REVIEW_CHANNEL_ID = 1468863738969981079

RATING_CHOICES = [
    app_commands.Choice(name=str(i), value=i) for i in range(1, 11)
]

class Designer(app_commands.Transformer):
    async def transform(self, interaction: Interaction, value: Member) -> Member:
        if any(role.id == DESIGNER_ROLE_ID for role in value.roles):
            return value
        raise app_commands.AppCommandError(f"{value.display_name} is not a staff member!")

class MyReviewLayout(ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, designer: Designer, rating: app_commands.Choice[int], review: str):
        super().__init__(timeout=None)

        review_container = ui.Container(
            ui.TextDisplay(
                "# Review"
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(
                "**Designer:**\n"
                f"{designer.mention}\n\n"
                "**Rating:**\n"
                f"{rating.value}/10\n\n"
                "**Review:**\n"
                f"{review}"
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            ui.MediaGallery(
                discord.MediaGalleryItem(
                    "https://cdn.discordapp.com/attachments/1118792507812229161/1500309181327085759/image.png"
                )
            ),
            ui.TextDisplay(
                f"-# Review submit by {interaction.user}"
            )
        )

        self.add_item(review_container)

CUSTOMER_ROLE_ID = 1468877862634389544

def has_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id == CUSTOMER_ROLE_ID for role in interaction.user.roles)
    return app_commands.check(predicate)

@bot.tree.command(
    name="review",
    description="Submit a review for a staff member!",
    guild=GUILD_ID
)
@has_role()
@app_commands.describe(
    designer="The staff member you're reviewing",
    rating="Select a rating from 1 to 10",
    review="Your review text"
)
@app_commands.choices(
    rating=[app_commands.Choice(name=str(i), value=i) for i in range(1, 11)]
)
async def review(
    interaction: Interaction,
    designer: discord.Member,
    rating: app_commands.Choice[int],
    review: str
):
    if not any(role.id == DESIGNER_ROLE_ID for role in designer.roles):
        await interaction.response.send_message(
            f"{designer.mention} is not a staff member!",
            ephemeral=True
        )
        return

    layout = MyReviewLayout(interaction, designer, rating, review)

    await interaction.response.send_message(
        "Review submitted!",
        ephemeral=True
    )

    channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
    if channel:
        await channel.send(view=layout)

@review.error
async def review_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

# --------------------------------- Suggestion Command ---------------------------------

SUGGESTION_CHANNEL_ID = 1500415691197648956

class MySuggestionLayout(ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, suggestion: str):
        super().__init__(timeout=None)

        self.upvotes = set()
        self.downvotes = set()

        suggestion_container = ui.Container(
            ui.TextDisplay("# Suggestion"),
            ui.Separator(spacing=discord.SeparatorSpacing.small, visible=False),
            ui.TextDisplay(
                f"**Suggestion:**\n{suggestion}"
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            ui.MediaGallery(
                discord.MediaGalleryItem(
                    "https://cdn.discordapp.com/attachments/1118792507812229161/1500442355457589339/image.png"
                )
            ),
            ui.TextDisplay(
                f"-# Suggestion submitted by {interaction.user}"
            )
        )

        class UpvoteButton(ui.Button):
            def __init__(self, view):
                super().__init__(
                    label="0",
                    emoji="👍",
                    style=discord.ButtonStyle.grey,
                    custom_id="upvote"
                )
                self.view_ref = view

            async def callback(self, interaction: discord.Interaction):
                user_id = interaction.user.id

                if user_id in self.view_ref.upvotes:
                    self.view_ref.upvotes.remove(user_id)
                else:
                    self.view_ref.upvotes.add(user_id)
                    self.view_ref.downvotes.discard(user_id)

                self.view_ref.update_buttons()
                await interaction.response.edit_message(view=self.view_ref)

        class DownvoteButton(ui.Button):
            def __init__(self, view):
                super().__init__(
                    label="0",
                    emoji="👎",
                    style=discord.ButtonStyle.grey,
                    custom_id="downvote"
                )
                self.view_ref = view

            async def callback(self, interaction: discord.Interaction):
                user_id = interaction.user.id

                if user_id in self.view_ref.downvotes:
                    self.view_ref.downvotes.remove(user_id)
                else:
                    self.view_ref.downvotes.add(user_id)
                    self.view_ref.upvotes.discard(user_id)

                self.view_ref.update_buttons()
                await interaction.response.edit_message(view=self.view_ref)

        button_row = ui.ActionRow(
            UpvoteButton(self),
            DownvoteButton(self)
        )

        self.add_item(suggestion_container)
        self.add_item(button_row)

    def update_buttons(self):
        for item in self.children:
            if isinstance(item, ui.ActionRow):
                for child in item.children:
                    if isinstance(child, ui.Button):
                        if child.custom_id == "upvote":
                            child.label = str(len(self.upvotes))
                        elif child.custom_id == "downvote":
                            child.label = str(len(self.downvotes))


@bot.tree.command(name="suggestion", description="Submit a suggestion!", guild=GUILD_ID)
async def suggestion(interaction: discord.Interaction, suggestion: str):
    layout = MySuggestionLayout(interaction, suggestion)

    await interaction.response.send_message(
        "Suggestion submitted!",
        ephemeral=True
    )

    channel = interaction.guild.get_channel(SUGGESTION_CHANNEL_ID)
    if channel:
        message = await channel.send(view=layout)

    thread = await message.create_thread(
        name=f"{interaction.user}'s Suggestion"
    )

# --------------------------------- Order Status Command ---------------------------------

ORDERSTATUS_ROLE_ID = 1497415094202535987

ORDERSTATUS_CHANNEL_ID = 1468863704178233395

class MyOrderStatusLayout(ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, clothing: str, discorddevelopment: str, graphics: str, liveries: str, els: str):
        super().__init__(timeout=None)

        orderstatus_container = ui.Container(
            ui.TextDisplay(
                "# Order Status\n"
                "### Legend:\n"
                "**🟢: Orders are open with regular waiting times.**\n"
                "**🟡: Orders are open with delayed waiting times.**\n"
                "**🔴: Orders are closed.**"
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(
                f"**Clothing:** {clothing}\n"
                f"**Discord Development:** {discorddevelopment}\n"
                f"**Graphics:** {graphics}\n"
                f"**Liveries:** {liveries}\n"
                f"**ELS:** {els}"
            )
        )

        self.add_item(orderstatus_container)

def has_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id == ORDERSTATUS_ROLE_ID for role in interaction.user.roles)
    return app_commands.check(predicate)

@bot.tree.command(name="orderstatus", description="Update the order status!", guild=GUILD_ID)
@has_role()
@app_commands.choices(clothing=[
    app_commands.Choice(name="Open", value="🟢"),
    app_commands.Choice(name="Delayed", value="🟡"),
    app_commands.Choice(name="Closed", value="🔴"),
])
@app_commands.choices(discorddevelopment=[
    app_commands.Choice(name="Open", value="🟢"),
    app_commands.Choice(name="Delayed", value="🟡"),
    app_commands.Choice(name="Closed", value="🔴"),
])
@app_commands.choices(graphics=[
    app_commands.Choice(name="Open", value="🟢"),
    app_commands.Choice(name="Delayed", value="🟡"),
    app_commands.Choice(name="Closed", value="🔴"),
])
@app_commands.choices(liveries=[
    app_commands.Choice(name="Open", value="🟢"),
    app_commands.Choice(name="Delayed", value="🟡"),
    app_commands.Choice(name="Closed", value="🔴"),
])
@app_commands.choices(els=[
    app_commands.Choice(name="Open", value="🟢"),
    app_commands.Choice(name="Delayed", value="🟡"),
    app_commands.Choice(name="Closed", value="🔴"),
])
async def orderstatus(interaction: discord.Interaction, clothing: app_commands.Choice[str], discorddevelopment: app_commands.Choice[str], graphics: app_commands.Choice[str], liveries: app_commands.Choice[str], els: app_commands.Choice[str]):
    channel = interaction.guild.get_channel(ORDERSTATUS_CHANNEL_ID)
    layout = MyOrderStatusLayout(interaction, clothing.value, discorddevelopment.value, graphics.value, liveries.value, els.value)

    await channel.send(view=layout)
    await interaction.response.send_message("Order Status Successfully Updated.", ephemeral=True)

@orderstatus.error
async def orderstatus_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

# --------------------------------- Portfoliocreate Command ---------------------------------

PORTFOLIO_ROLE_ID = 1497415094202535987
PORTFOLIO_CHANNEL_ID = 1497420259605610577

def has_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id == PORTFOLIO_ROLE_ID for role in interaction.user.roles)
    return app_commands.check(predicate)

@bot.tree.command(name="portfoliocreate", description="Create a portfolio!", guild=GUILD_ID)
@has_role()
async def portfolio(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)

    forum = interaction.guild.get_channel(PORTFOLIO_CHANNEL_ID)

    thread_name = f"{user.name}'s Portfolio"

    thread, message = await forum.create_thread(
        name=thread_name,
        content="https://cdn.discordapp.com/attachments/1118792507812229161/1500441807933280307/image.png"
    )

    await thread.send(f"{user.mention}")

    await interaction.followup.send(f"Successfully created {user.mention}'s portfolio!", ephemeral=True)

@portfolio.error
async def portfolio_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

# --------------------------------- Order Embed ---------------------------------

class MyOrderMessage(ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, option: str, product: str):
        super().__init__(timeout=None)
        support_role = interaction.guild.get_role(1497415733062139994)
        
        form_container = ui.Container(
            ui.TextDisplay(
                "# Order"
            ),
            ui.Separator(),
            ui.TextDisplay(
                "**Option:**\n"
                f"{option}\n\n"
                "**Product:**\n"
                f"{product}\n\n"
                "**Opener:**\n"
                f"{interaction.user.mention}\n\n"
                f"||{support_role.mention}||"
            ),
            ui.Separator(),
            ui.MediaGallery(
                discord.MediaGalleryItem(
                    "https://cdn.discordapp.com/attachments/1118792507812229161/1500416345223856189/image.png"
                )
            )
        )

        claim_button = ui.Button(
            label="Claim",
            style=discord.ButtonStyle.green,
            emoji="🔑"
        )

        async def claim_callback(interaction: discord.Interaction):
            channel = interaction.channel
            designer_role_id = 1497716042087010394

            if designer_role_id not in [role.id for role in interaction.user.roles]:
                return await interaction.response.send_message(
                    "Must be a designer to claim this order.",
                    ephemeral=True
                )
            
            if channel.name.startswith("🟢"):
                return await interaction.response.send_message(
                    "This order is already claimed!",
                    ephemeral=True
                )

            new_name = channel.name.replace("🔴", "🟢")
            await channel.edit(name=new_name)

            await interaction.response.send_message(f"Your order will be handled by {interaction.user.mention}.", ephemeral=False)

        claim_button.callback = claim_callback

        close_button = ui.Button(
            label="Close",
            style=discord.ButtonStyle.red,
            emoji="🔐"
        )

        async def close_callback(interaction: discord.Interaction):
            await interaction.response.send_message("Closing ticket now.", ephemeral=True)
            await interaction.channel.delete()

        close_button.callback = close_callback

        button_row = ui.ActionRow(
            close_button,
            claim_button
        )

        self.add_item(form_container)
        self.add_item(button_row)

class MyOrderModal(ui.Modal, title="Order"):

    option = ui.Label(
        text="Premade or custom",
        component=ui.Select(
            placeholder="Select whether your product is premade or custom",
            options=[
                discord.SelectOption(label="Premade", value="Premade"),
                discord.SelectOption(label="Custom", value="Custom")
            ]
        )
    )

    product = ui.TextInput(
        label="What product(s) would you like to purchase?",
        placeholder="e.g. Uniform, Livery",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        category_id = 1500414997082275900
        category = await guild.fetch_channel(category_id)

        support_role_id = 1497415733062139994
        support_role = guild.get_role(support_role_id)

        designer_role_id = 1497716042087010394
        designer_role = guild.get_role(designer_role_id)

        selected_value = self.option.component.values[0]

        safe_name = re.sub(r'[^a-zA-Z0-9]', '', interaction.user.name)
        channel_name = f"🔴-ticket-{safe_name}"

        existing = discord.utils.get(guild.channels, name=channel_name)
        if existing:
            return await interaction.response.send_message(
                "You already have an order open!",
                ephemeral=True
            )
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True),
            designer_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            view=MyOrderMessage(interaction, selected_value, self.product.value)
        )

        await interaction.response.send_message(
            f"Your ticket has been created: {channel.mention}",
            ephemeral=True
        )

class OrderButton(ui.Button):
    def __init__(self):
        super().__init__(
            label="Order",
            style=discord.ButtonStyle.blurple
        )

    async def callback(self, interaction):
        await interaction.response.send_modal(MyOrderModal())

class MyOrderLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        ticket_container = ui.Container(
            ui.MediaGallery(
                discord.MediaGalleryItem(
                    "https://cdn.discordapp.com/attachments/1118792507812229161/1500416345223856189/image.png"
                )
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            ui.TextDisplay(
                "***Welcome to Cams Commissions*** your go-to place for high quality, custom made designs tailored exactly to what you’re looking for.\n\n"
                "Whether you have a clear vision or just an idea, our team is here to bring it to life with precision and creativity. We offer a wide range of services to suit your needs, all focused on delivering clean, professional, and standout results."
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            ui.ActionRow(
                OrderButton()
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            ui.MediaGallery(
                discord.MediaGalleryItem(
                    "https://cdn.discordapp.com/attachments/1118792507812229161/1500442630801195139/image.png"
                )
            )
        )

        self.add_item(ticket_container)

@bot.tree.command(name="order", description="Send the order panel!", guild=GUILD_ID)
async def order(interaction: discord.Interaction):
    layout = MyOrderLayout()

    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(view=layout)
    await interaction.followup.send("Order panel successfully sent.", ephemeral=True)

@order.error
async def order_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

# dashboard select menu shit

LOG_CHANNEL_ID = 1497559161595105410

class guidelines(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            ui.Container(
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.TextDisplay(f"# Guidelines\n**Respect:**\n> Members are required to respect people and property. Treat everyone with kindness.\n\n**NSFW Content:**\n> Any form of NSFW content is strictly prohibited.\n\n**Spamming:**\n> Please do not spam emojis, soundboards, noises or messages.\n\n**Discord TOS:**\n> You are required to follow [Discord TOS](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwioq8HytvSTAxXOs1YBHbibPJUQFnoECAwQAQ&url=https%3A%2F%2Fdiscord.com%2Fterms&usg=AOvVaw0jthmhEq2sRUdked_hRviA&opi=89978449) at all times.\n\n**Common Sense:**\n> We cannot list every rule here - if you believe someone is doing something wrong, do not join in, report it instead."),
                ui.Separator(spacing=discord.SeparatorSpacing.small)
            )
        )

class aboutUs(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            ui.Container(
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.TextDisplay(
                    "Cams Commissions was built with one goal in mind — to deliver high-quality, custom designs that match exactly what clients are looking for. We understand that every server and project is different, and finding designs that are both unique and well-made can be difficult. That’s why Cams Commissions focuses on creating tailored work with attention to detail, style, and consistency.\n\n"
                    "Whether you’re starting fresh or upgrading your current look, we provide clean, professional designs with reliable turnaround times. At Cams Commissions, it’s all about bringing your vision to life while maintaining quality you can trust.\n\n"
                    "*Spirit of Designs*"
                ),
                ui.Separator(spacing=discord.SeparatorSpacing.small)
            )
        )

class DashboardSelect(ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="Navigation",
            options=[
                discord.SelectOption(label="Guidelines", value="1"),
                discord.SelectOption(label="About Us", value="2")
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "1":
            await interaction.response.send_message(view=guidelines(), ephemeral=True)
        elif self.values[0] == "2":
            await interaction.response.send_message(view=aboutUs(), ephemeral=True)

# support system

class MyTicketMessage(ui.LayoutView):
    def __init__(self, interaction: discord.Interaction, question: str, select: str):
        super().__init__(timeout=None)
        support_role = interaction.guild.get_role(1497415733062139994)
        
        form_container = ui.Container(
            ui.TextDisplay("# Support Ticket"),
            ui.Separator(),
            ui.TextDisplay(
                f"-# ||{support_role.mention}||\n"
                f"> Hey there, {interaction.user.mention}! Thank you for creating a **support ticket**. Please refrain from pinging any staff members within **24 hours** of creating your ticket.\n"
                "**Inquiry:**\n"
                f"{question}\n"
                "**Opener Username:**\n"
                f"{interaction.user.name}"
            ),
            ui.Separator(),
            ui.MediaGallery(
                discord.MediaGalleryItem("https://cdn.discordapp.com/attachments/1118792507812229161/1500442630801195139/image.png")
            )
        )
        
        claim_button = ui.Button(label="Claim", style=discord.ButtonStyle.green)

        async def claim_callback(interaction: discord.Interaction):
            channel = interaction.channel
            support_role_id = 1497415733062139994

            if support_role_id not in [role.id for role in interaction.user.roles]:
                return await interaction.response.send_message("Must be customer service to claim this ticket.", ephemeral=True)

            if channel.name.startswith("🟢"):
                new_name = channel.name.replace("🟢", "🔴")
                await channel.edit(name=new_name)
                await interaction.response.send_message(f"Ticket unclaimed by {interaction.user.mention}.")
            else:
                new_name = channel.name.replace("🔴", "🟢")
                await channel.edit(name=new_name)
                await interaction.response.send_message(f"Your ticket will be handled by {interaction.user.mention}.")

        claim_button.callback = claim_callback

        close_button = ui.Button(label="Close", style=discord.ButtonStyle.red)

        async def close_callback(interaction: discord.Interaction):
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                opener_id = ticket_openers.get(interaction.channel.id)
                opener_mention = f"<@{opener_id}>" if opener_id else "Unknown"
                close_time = discord.utils.utcnow().strftime("%d/%m/%Y at %H:%M UTC")
                log_view = ui.LayoutView(timeout=None)
                log_view.add_item(
                    ui.Container(
                        ui.TextDisplay(
                            "# Ticket Closed\n"
                            f"> A ticket has been closed.\n\n"
                            f"`-` **Closed by:** {interaction.user.mention}\n"
                            f"`-` **Opened by:** {opener_mention}\n"
                            f"`-` **Channel:** {interaction.channel.name}\n"
                            f"`-` **Time:** {close_time}"
                        ),
                        ui.Separator(),
                        ui.MediaGallery(
                            discord.MediaGalleryItem(
                                "https://cdn.discordapp.com/attachments/1118792507812229161/1500442630801195139/image.png"
                            )
                        )
                    )
                )
                await log_channel.send(view=log_view)
            ticket_openers.pop(interaction.channel.id, None)
            await interaction.response.send_message("Closing ticket now.", ephemeral=True)
            await interaction.channel.delete()

        close_button.callback = close_callback

        button_row = ui.ActionRow(claim_button, close_button)

        self.add_item(form_container)
        self.add_item(button_row)

class MyTicketModal(ui.Modal, title="Support"):
    question = ui.TextInput(label="Question", placeholder="Your question here!", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        category_id = 1497598247114637322
        category = await guild.fetch_channel(category_id)

        support_role_id = 1497415733062139994
        support_role = guild.get_role(support_role_id)

        selected_value = "None"

        safe_name = re.sub(r'[^a-zA-Z0-9]', '', interaction.user.name)
        channel_name = f"🔴-ticket-{safe_name}"

        existing = discord.utils.get(guild.channels, name=channel_name)
        if existing:
            return await interaction.response.send_message("You already have a ticket open!", ephemeral=True)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True, attach_files=True)
        }

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        ticket_openers[channel.id] = interaction.user.id  # store opener
        await channel.send(view=MyTicketMessage(interaction, self.question.value, selected_value))
        await interaction.followup.send(f"Your ticket has been created: {channel.mention}", ephemeral=True)

class TicketButton(ui.Button):
    def __init__(self):
        super().__init__(label="Support", style=discord.ButtonStyle.danger)

    async def callback(self, interaction):
        await interaction.response.send_modal(MyTicketModal())

# application (broken)

class MyApproveMessage(ui.LayoutView):
    def __init__(self, staff: discord.Member):
        super().__init__(timeout=None)

        approve_container = ui.Container(
            ui.TextDisplay(
                f"Your application has been approved by {staff.mention}."
            )
        )

        self.add_item(approve_container)

class MyDenyMessage(ui.LayoutView):
    def __init__(self, staff: discord.Member):
        super().__init__(timeout=None)

        deny_container = ui.Container(
            ui.TextDisplay(
                f"Your application has been denied by {staff.mention}."
            )
        )

        self.add_item(deny_container)

class MyFormMessage(ui.LayoutView):
    def __init__(self, applicant: discord.Member, guild: discord.Guild, position: str, experience: str, team: str, portfolio_url: str = None, attachment_urls: list[str] = None):
        super().__init__(timeout=None)

        REVIEWER_ROLE_ID = [1497415135810289745, 1497415094202535987]

        gallery_items = [discord.MediaGalleryItem(media=url) for url in (attachment_urls or [])]

        application_reader = guild.get_role(REVIEWER_ROLE_ID[0])

        form_container = ui.Container(
            ui.TextDisplay(
                f"-# {application_reader.mention}\n"
                "# New Application\n"
                "> Please find the applicants answers attached below."
            ),
            ui.Separator(),
            ui.TextDisplay("## Application Answers"),
            ui.TextDisplay(
                "**Applicant:**\n"
                f"{applicant.mention}\n\n"
                "**Position:**\n"
                f"{position}\n\n"
                "**Experience:**\n"
                f"{experience}\n\n"
                "**Reason for joining team:**\n"
                f"{team}\n\n"
                "**Portfolio URL:**\n"
                f"{portfolio_url if portfolio_url else '**No URL provided.**'}\n\n"
                "**Past Work:**"
            ),
            ui.MediaGallery(*gallery_items) if gallery_items else ui.TextDisplay("**No attachments provided.**")
        )

        approve_button = ui.Button(label="Approve", style=discord.ButtonStyle.green)

        async def approve_callback(interaction: discord.Interaction):
            if not any(role.id in REVIEWER_ROLE_ID for role in interaction.user.roles):
                return await interaction.response.send_message(
                    "You don't have permission to approve applications!",
                    ephemeral=True
                )

            try:
                await applicant.send(view=MyApproveMessage(interaction.user))
            except discord.Forbidden:
                pass

            approve_button.disabled = True
            deny_button.disabled = True
            approve_button.label = "Approved ✅"

            await interaction.response.defer()
            await interaction.message.edit(view=self)
            await interaction.followup.send(
                f"{applicant.mention}'s application has been approved!",
                ephemeral=True
            )

        approve_button.callback = approve_callback

        deny_button = ui.Button(label="Deny", style=discord.ButtonStyle.red)

        async def deny_callback(interaction: discord.Interaction):
            if not any(role.id in REVIEWER_ROLE_ID for role in interaction.user.roles):
                return await interaction.response.send_message(
                    "You don't have permission to deny applications!",
                    ephemeral=True
                )

            try:
                await applicant.send(view=MyDenyMessage(interaction.user))
            except discord.Forbidden:
                pass

            approve_button.disabled = True
            deny_button.disabled = True
            deny_button.label = "Denied ❌"

            await interaction.response.defer()
            await interaction.message.edit(view=self)
            await interaction.followup.send(
                f"{applicant.mention}'s application has been denied!",
                ephemeral=True
            )

        deny_button.callback = deny_callback

        button_row = ui.ActionRow(approve_button, deny_button)

        self.add_item(form_container)
        self.add_item(button_row)

class MyFormModal(ui.Modal, title="Designer Application"):

    position = ui.Label(
        text="Position",
        component=ui.Select(
            placeholder="Select the position you are applying for",
            options=[
                discord.SelectOption(label="Discord Development", value="Discord Development"),
                discord.SelectOption(label="Liveries", value="Liveries"),
                discord.SelectOption(label="Clothing", value="Clothing"),
                discord.SelectOption(label="Graphics", value="Graphics"),
                discord.SelectOption(label="ELS", value="ELS")
            ],
            required=True
        )
    )

    experience = ui.TextInput(
        label="Experience",
        placeholder="Tell us about your previous experience designing.",
        style=discord.TextStyle.paragraph,
        required=True
    )

    team = ui.TextInput(
        label="Why do you want to join our team?",
        placeholder="What motivates you to join our team?",
        style=discord.TextStyle.paragraph,
        required=True
    )

    portfolio_url = ui.TextInput(
        label="Portfolio URL",
        placeholder="If your work is on a website, put the link here, if not leave blank and attach files below.",
        style=discord.TextStyle.short,
        required=False
    )

    past_work = ui.Label(
        text="Past Work",
        description="Please attach any past work below",
        component=ui.FileUpload(
            min_values=1,
            max_values=10,
            required=False
        )
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        applicant = interaction.user

        channel_id = 1497503065065127956
        channel = await guild.fetch_channel(channel_id)

        resolved = interaction.data.get("resolved") or {}
        attachments = resolved.get("attachments") or {}
        attachment_urls = [a["url"] for a in attachments.values()]

        selected_value = self.position.component.values[0] if self.position.component.values else "None"

        await channel.send(
            view=MyFormMessage(
                applicant,
                guild,
                selected_value,
                self.experience.value,
                self.team.value,
                self.portfolio_url.value,
                attachment_urls
            )
        )

        await interaction.response.send_message(
            "Your application was successfully submitted!",
            ephemeral=True
        )

class FormButton(ui.Button):
    def __init__(self):
        super().__init__(label="Designer Application", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        await interaction.response.send_modal(MyFormModal())

# dashboard embed

class MyComponentsV2Layout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            ui.Container(
                ui.MediaGallery(
                    discord.MediaGalleryItem("https://cdn.discordapp.com/attachments/1118792507812229161/1500805633946030171/image.png")
                ),
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.TextDisplay(
                    "> Welcome to **Cam's Commissions**! Since 2026, we've been leading the game with the **highest quality**, and **cheapest** designs out there. Use our dropdown below to explore further."
                ),
                ui.ActionRow(TicketButton(), FormButton(), ui.Button(
                    label="Roblox Group",
                    style=discord.ButtonStyle.link,
                    url="https://www.roblox.com/communities/748351092/Cams-Commissions-Pre-made-Assets#!/about"
                )),
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.ActionRow(DashboardSelect()),
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.MediaGallery(
                    discord.MediaGalleryItem("https://cdn.discordapp.com/attachments/1118792507812229161/1500442630801195139/image.png")
                )
            )
        )

@bot.tree.command(name="dashboard", guild=GUILD_ID)
async def dashboard(interaction: discord.Interaction):
    required_role_id = 1497415094202535987

    if required_role_id not in [role.id for role in interaction.user.roles]:
        return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

    channel_id = 1468852319071371290
    channel = interaction.guild.get_channel(channel_id)

    if not channel:
        return await interaction.response.send_message("Dashboard channel not found.", ephemeral=True)

    await channel.send(view=MyComponentsV2Layout())
    await interaction.response.send_message("Dashboard sent successfully.", ephemeral=True)

@bot.tree.command(name="funds", description="Check the Robux balance of the Roblox group.", guild=GUILD_ID)
async def slash_groupfunds(interaction: discord.Interaction):
    required_role_id = 1497553372553674854
    if required_role_id not in [role.id for role in interaction.user.roles]:
        return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        funds = roblox_get_funds(GROUP_ID)
        layout = ui.LayoutView(timeout=None)
        layout.add_item(
            ui.Container(
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.TextDisplay(
                    f"## Cam's Commissions Group Funds\n"
                    f"> `-` **Available Funds:** `{funds['available']:,}`R$\n"
                    f"> `-` **Pending Funds:** `{funds['pending']:,}`R$\n"
                    f"> `-` **Total Funds:** `{funds['total']:,}`R$"
                ),
                ui.Separator(spacing=discord.SeparatorSpacing.small)
            )
        )
        await interaction.followup.send(view=layout, ephemeral=True)
    except requests.HTTPError as e:
        await interaction.followup.send(f"Failed: HTTP {e.response.status_code}: {e.response.text}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Unexpected error: {e}", ephemeral=True)\
        
@bot.command(name="funds", aliases=["groupfunds"])
async def funds(ctx):
    required_role_id = 1497553372553674854
    if required_role_id not in [role.id for role in ctx.author.roles]:
        return await ctx.send("You do not have permission to use this command.")
    try:
        data = roblox_get_funds(GROUP_ID)
        layout = ui.LayoutView(timeout=None)
        layout.add_item(
            ui.Container(
                ui.Separator(spacing=discord.SeparatorSpacing.small),
                ui.TextDisplay(
                    f"## Cam's Commissions Group Funds\n"
                    f"> `-` **Available Funds:** `{data['available']:,}`R$\n"
                    f"> `-` **Pending Funds:** `{data['pending']:,}`R$\n"
                    f"> `-` **Total Funds:** `{data['total']:,}`R$"
                ),
                ui.Separator(spacing=discord.SeparatorSpacing.small)
            )
        )
        await ctx.send(view=layout)
    except Exception as e:
        await ctx.send(f"Unexpected error: {e}")
    prefix_channel_id = 1503285614089601176
    prefix_channel = ctx.guild.get_channel(prefix_channel_id)
    prefix_log_view = ui.LayoutView(timeout=None)
    prefix_log_view.add_item(
        ui.Container(
            ui.Separator(spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(
                f"## Prefix Command Invoked\n"
                f"> {ctx.author.mention} used `{ctx.invoked_with}` command in {ctx.channel.mention}.\n"
            ),
            ui.Separator(spacing=discord.SeparatorSpacing.small)
        )
    )
    await prefix_channel.send(view=prefix_log_view, allowed_mentions=discord.AllowedMentions.none())

# --------------------------------- Sale Log Command ---------------------------------

SALES_FILE = "camscommisionssales.json"

def load_sales():
    if not os.path.exists(SALES_FILE):
        return []
    with open(SALES_FILE, "r") as f:
        return json.load(f)

def save_sales(data):
    with open(SALES_FILE, "w") as f:
        json.dump(data, f, indent=4)

class MySaleLogLayout(ui.LayoutView):
    def __init__(self, sales: list):
        super().__init__(timeout=None)

        if not sales:
            text = "# Logged Sales:\n\nNo sales logged yet."
        else:
            text = "# Logged Sales:\n\n"
            for sale in sales:
                timestamp = f"<t:{sale['timestamp']}:R>"
                text += (
                    f"**{sale['id']}**\n"
                    f"Product: {sale['product']}\n"
                    f"Customer: <@{sale['customer']}>\n"
                    f"Date: {timestamp}\n\n"
                )

        salelog_container = ui.Container(
            ui.TextDisplay(text)
        )

        self.add_item(salelog_container)

SALELOG_ROLE_ID = 1497716042087010394
CUSTOMER_ROLE_ID = 1468877862634389544

def has_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id == SALELOG_ROLE_ID for role in interaction.user.roles)
    return app_commands.check(predicate)

@bot.tree.command(name="salelogview", description="View the logged sales!", guild=GUILD_ID)
@has_role()
async def salelogview(interaction: discord.Interaction):
    sales = load_sales()

    view = MySaleLogLayout(sales)

    await interaction.response.send_message(view=view)

@salelogview.error
async def dashboard_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

def has_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id == SALELOG_ROLE_ID for role in interaction.user.roles)
    return app_commands.check(predicate)

@bot.tree.command(name="salelog", description="Log a sale!", guild=GUILD_ID)
@has_role()
@app_commands.describe(product="Product sold", customer="Customer who bought it")
async def salelog(
    interaction: discord.Interaction,
    product: str,
    customer: discord.Member
):
    if not any(role.id == CUSTOMER_ROLE_ID for role in customer.roles):
        return await interaction.response.send_message(
            "That user is not a customer.",
            ephemeral=True
        )

    sales = load_sales()

    sale_number = len(sales) + 1
    sale_id = f"#{sale_number:02d}"

    sale_data = {
        "id": sale_id,
        "product": product,
        "customer": customer.id,
        "timestamp": int(time.time())
    }

    sales.append(sale_data)
    save_sales(sales)

    channel = interaction.guild.get_channel(1506551078785912933)
    if channel:
        await channel.edit(name=f"Sales: {len(sales)}")

    await interaction.response.send_message(
        f"Sale successfully logged! Sale number: {sale_id} | {product} → {customer.mention}",
        ephemeral=True
    )

@salelog.error
async def dashboard_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )

# status
@tasks.loop(seconds=15)
async def rotate_status():
    guild = bot.get_guild(GUILD_ID.id) if hasattr(GUILD_ID, "id") else bot.get_guild(GUILD_ID)
    member_count = guild.member_count if guild else 0
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name=f"🌊 Cam's Commissions — {member_count} members"),
        discord.Activity(type=discord.ActivityType.watching, name=f"⚡ Powering Cam's Commissions"),
        discord.Activity(type=discord.ActivityType.watching, name=f"🌸 Leading the game"),
    ]
    await bot.change_presence(activity=random.choice(statuses), status=discord.Status.online)

# --------------------------------- Bot Startup/Run ---------------------------------

@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}!")
    await rotate_status.start()

    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"Synced {len(synced)} commands to guild {GUILD_ID.id}")
    except Exception as e:
        print(f"Error syncing commands: {e}")


# Giveaway storage
giveaways = {}

# Giveaway counter
giveaway_counter = 1


# =====================================================
# ROLE CHECK
# =====================================================

def has_hr_role(member: discord.Member):
    return any(role.id == HR_ROLE_ID for role in member.roles)


# =====================================================
# TIME FORMAT CHECK
# =====================================================

def valid_duration(duration):
    return re.match(r"^\d+(s|m|h|d|w)$", duration)


# =====================================================
# READY EVENT
# =====================================================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)

    print(f"Logged in as {bot.user}")


# =====================================================
# GIVEAWAY BUTTON
# =====================================================

class GiveawayView(View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(
        label="Enter 🎉",
        style=discord.ButtonStyle.green,
        custom_id="giveaway_enter"
    )
    async def enter_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        giveaway = giveaways.get(self.giveaway_id)

        if not giveaway:
            return await interaction.response.send_message(
                "❌ This giveaway has already ended.",
                ephemeral=True
            )

        if interaction.user.id in giveaway["entries"]:
            return await interaction.response.send_message(
                "❌ You already entered this giveaway.",
                ephemeral=True
            )

        giveaway["entries"].append(interaction.user.id)

        await interaction.response.send_message(
            "✅ You entered the giveaway!",
            ephemeral=True
        )


# =====================================================
# INFRACTION COMMAND
# =====================================================

@bot.tree.command(
    name="infraction",
    description="Issue a staff infraction.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    user="The staff member being infracted",
    reason="Reason for the infraction",
    punishment="Punishment being issued",
    notes="Additional notes"
)
async def infraction(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str,
    punishment: str,
    notes: str
):

    embed = discord.Embed(
        description=(
            "# Infraction\n"
            "The following staff member has been infracted, if you feel this is unfair, please open a ticket.\n\n"
            f"**User** `-` {user.mention}\n"
            f"**Reason** `-` {reason}\n"
            f"**Punishment** `-` {punishment}\n"
            f"**Notes** `-` {notes}"
        ),
        color=INFRACTION_COLOR
    )

    embed.set_footer(
        text=f"Executed by: {interaction.user}",
        icon_url=interaction.user.display_avatar.url
    )

    channel = bot.get_channel(INFRACTION_CHANNEL_ID)

    await channel.send(
        content=user.mention,
        embed=embed
    )

    await interaction.response.send_message(
        "✅ Infraction successfully logged.",
        ephemeral=True
    )


# =====================================================
# TAX COMMAND
# =====================================================

@bot.tree.command(
    name="tax",
    description="Calculate Roblox tax.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    amount="Amount of Robux"
)
async def tax(
    interaction: discord.Interaction,
    amount: int
):

    needed = math.ceil(amount / 0.7)
    received = math.floor(amount * 0.7)

    embed = discord.Embed(
        description=(
            f"To receive `{amount:,}` Robux you will need to be paid `{needed:,}` Robux.\n\n"
            f"When being paid `{amount:,}` Robux you will receive `{received:,}` Robux."
        ),
        color=DEFAULT_COLOR
    )

    await interaction.response.send_message(embed=embed)


# =====================================================
# PROMOTION COMMAND
# =====================================================

@bot.tree.command(
    name="promotion",
    description="Log a staff promotion.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    user="The staff member being promoted",
    old_rank="Their previous rank",
    new_rank="Their new rank",
    reason="Reason for the promotion",
    notes="Additional notes"
)
async def promotion(
    interaction: discord.Interaction,
    user: discord.Member,
    old_rank: str,
    new_rank: str,
    reason: str,
    notes: str
):

    if not has_hr_role(interaction.user):
        return await interaction.response.send_message(
            "❌ You do not have the required permissions to execute this command.",
            ephemeral=True
        )

    embed = discord.Embed(
        description=(
            "# Promotion\n"
            "The following staff member has been promoted.\n\n"
            f"**User** `-` {user.mention}\n"
            f"**Old Rank** `-` {old_rank}\n"
            f"**New Rank** `-` {new_rank}\n"
            f"**Reason** `-` {reason}\n"
            f"**Notes** `-` {notes}"
        ),
        color=PROMOTION_COLOR
    )

    embed.set_footer(
        text=f"Executed by: {interaction.user}",
        icon_url=interaction.user.display_avatar.url
    )

    channel = bot.get_channel(PROMOTION_CHANNEL_ID)

    await channel.send(
        content=user.mention,
        embed=embed
    )

    await interaction.response.send_message(
        "✅ Promotion successfully logged.",
        ephemeral=True
    )


# =====================================================
# GIVEAWAY COMMAND
# =====================================================

@bot.tree.command(
    name="giveaway",
    description="Start a giveaway.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    prize="Prize for the giveaway",
    duration="Duration of the giveaway (1d, 1w, 1m etc)",
    winners="Amount of winners",
    requirements="Requirements to enter"
)
async def giveaway(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int,
    requirements: str
):

    global giveaway_counter

    if not has_hr_role(interaction.user):
        return await interaction.response.send_message(
            "❌ You do not have the required permissions to execute this command.",
            ephemeral=True
        )

    if not valid_duration(duration):
        return await interaction.response.send_message(
            "❌ Invalid duration format. Use formats like `1d`, `1w`, `1m`, `12h`.",
            ephemeral=True
        )

    current_id = giveaway_counter

    embed = discord.Embed(
        description=(
            f"-# Giveaway ID - {current_id}\n\n"
            "# Giveaway\n\n"
            f"**Prize** `-` {prize}\n"
            f"**Duration** `-` {duration}\n"
            f"**Winners** `-` {winners}\n"
            f"**Requirements** `-` {requirements}"
        ),
        color=DEFAULT_COLOR
    )

    message = await interaction.channel.send(
        embed=embed,
        view=GiveawayView(current_id)
    )

    giveaways[current_id] = {
        "message_id": message.id,
        "winners": winners,
        "entries": []
    }

    giveaway_counter += 1

    await interaction.response.send_message(
        f"✅ Giveaway created. Giveaway ID: `{current_id}`",
        ephemeral=True
    )


# =====================================================
# CLAIM GIVEAWAY COMMAND
# =====================================================

@bot.tree.command(
    name="claim",
    description="End a giveaway and pick winners.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    giveaway_id="Giveaway ID"
)
async def claim(
    interaction: discord.Interaction,
    giveaway_id: int
):

    if not has_hr_role(interaction.user):
        return await interaction.response.send_message(
            "❌ You do not have the required permissions to execute this command.",
            ephemeral=True
        )

    giveaway = giveaways.get(giveaway_id)

    if not giveaway:
        return await interaction.response.send_message(
            "❌ Giveaway not found.",
            ephemeral=True
        )

    entries = giveaway["entries"]
    winner_count = giveaway["winners"]

    if len(entries) == 0:
        return await interaction.response.send_message(
            "❌ No one entered the giveaway.",
            ephemeral=True
        )

    winners = random.sample(
        entries,
        min(winner_count, len(entries))
    )

    mentions = ", ".join(f"<@{user_id}>" for user_id in winners)

    message = await interaction.channel.fetch_message(
        giveaway["message_id"]
    )

    await message.reply(
        f"**Winner** `-` {mentions}"
    )

    del giveaways[giveaway_id]

    await interaction.response.send_message(
        "✅ Giveaway ended and claimed.",
        ephemeral=True
    )


# =====================================================
# REROLL COMMAND
# =====================================================

@bot.tree.command(
    name="reroll",
    description="Re-roll a giveaway.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    giveaway_id="Giveaway ID",
    reroll_winners="Amount of winners to reroll"
)
async def reroll(
    interaction: discord.Interaction,
    giveaway_id: int,
    reroll_winners: int
):

    if not has_hr_role(interaction.user):
        return await interaction.response.send_message(
            "❌ You do not have the required permissions to execute this command.",
            ephemeral=True
        )

    giveaway = giveaways.get(giveaway_id)

    if not giveaway:
        return await interaction.response.send_message(
            "❌ Giveaway not found.",
            ephemeral=True
        )

    original_winners = giveaway["winners"]

    if reroll_winners > original_winners:
        return await interaction.response.send_message(
            "❌ That does not match the original winner amount. Please reroll the same amount or lower.",
            ephemeral=True
        )

    entries = giveaway["entries"]

    if len(entries) == 0:
        return await interaction.response.send_message(
            "❌ No giveaway entries found.",
            ephemeral=True
        )

    winners = random.sample(
        entries,
        min(reroll_winners, len(entries))
    )

    mentions = ", ".join(f"<@{user_id}>" for user_id in winners)

    message = await interaction.channel.fetch_message(
        giveaway["message_id"]
    )

    await message.reply(
        f"Re-rolled, **Winner** `-` {mentions}"
    )

    await interaction.response.send_message(
        "✅ Giveaway rerolled.",
        ephemeral=True
    )


# =====================================================
# AD COMMAND
# =====================================================

@bot.command(name="ad")
async def ad(ctx):

    ad_message = f"""
# {LOGO_EMOJI} // Cams Commissions

> Design isn’t just about looks - it’s about identity and quality.
> At Cams Commissions, every design is built with **purpose, creativity, and detail** to match your vision.

## What we want:
> Experienced Designers
> Experienced High Ranks
> Members
> **YOU**

Got a vision? We’ve got the skill to make it real.
Let's get it started by you joining our Cam's Commissions today!

https://discord.gg/xbn3PmhH
"""

bot.run(BOT_TOKEN)