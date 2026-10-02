import discord
from discord.ext import commands
import random
import os
import json

# 🔑 PASTE YOUR BOT TOKEN INSIDE THE SINGLE QUOTES BELOW
DISCORD_TOKEN = 'YOUR_BOT_TOKEN_HERE'

# Initialize the bot with prefix commands
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary defining the text files for your reward stock categories
PLATFORMS = {
    "epic": "epic_games.txt",
    "roblox": "roblox.txt",
    "steam": "steam.txt",
    "fortnite": "fortnite.txt"
}

# 💰 COST PRICING MAP (Set custom coin values for each platform here)
PRICING = {
    "epic": 50,
    "roblox": 30,
    "steam": 75,
    "fortnite": 100
}

ECONOMY_FILE = "balances.json"

# --- DATABASE HELPER FUNCTIONS ---
def load_balances():
    if not os.path.exists(ECONOMY_FILE):
        return {}
    with open(ECONOMY_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {}

def save_balances(balances):
    with open(ECONOMY_FILE, "w") as file:
        json.dump(balances, file, indent=4)

def get_balance(user_id):
    balances = load_balances()
    return balances.get(str(user_id), 0)

def update_balance(user_id, amount):
    balances = load_balances()
    user_str = str(user_id)
    balances[user_str] = balances.get(user_str, 0) + amount
    if balances[user_str] < 0:
        balances[user_str] = 0
    save_balances(balances)

# Helper function to read a file and return a clean list of lines
def get_file_lines(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as file:
        return [line.strip() for line in file.readlines() if line.strip()]

# Helper function to write lines back to a file
def write_file_lines(filename, lines):
    with open(filename, "w") as file:
        for line in lines:
            file.write(line + "\n")

@bot.event
async def on_ready():
    for filename in PLATFORMS.values():
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                pass
    print(f"🤖 Selector Shop Bot is online as {bot.user}")

# --- PUBLIC COMMAND 1: THE MENU SHOWING EVERY ITEM BY ID ---
@bot.command(name="shop")
async def show_shop(ctx):
    embed = discord.Embed(
        title="🛒 VIRTUAL SHOP CATALOG", 
        description="""Earn coins using `!daily` and buy rewards!

**Commands:**
• Single choice: `!buy [platform] #[ID]`
• Bulk random: `!buy [platform] [amount]`""",
        color=discord.Color.gold()
    )
    
    for platform_name, filename in PLATFORMS.items():
        price = PRICING[platform_name]
        items = get_file_lines(filename)
        
        if not items:
            embed.add_field(
                name=f"🎮 {platform_name.upper()} (💰 {price} coins)", 
                value="*❌ Out of Stock*", 
                inline=False
            )
        else:
            item_list_text = ""
            for index, item in enumerate(items, 1):
                display_label = item.split(":") if ":" in item else "Premium Reward"
                item_list_text += f"`#{index}` - {display_label}\n"
                
            embed.add_field(
                name=f"🎮 {platform_name.upper()} (💰 {price} coins)", 
                value=item_list_text, 
                inline=False
            )
        
    embed.set_footer(text=f"Your Wallet: {get_balance(ctx.author.id)} coins | Example: !buy roblox #2")
    await ctx.send(embed=embed)

# --- PUBLIC COMMAND 2: BUY A SPECIFIC SELECTION OR MULTIPLE ITEMS ---
@bot.command(name="buy", aliases=["gen"])
@commands.cooldown(1, 10, commands.BucketType.user)
async def buy_item(ctx, platform: str = None, choice_or_amount: str = None):
    if not platform or platform.lower() not in PLATFORMS or choice_or_amount is None:
        valid_list = ", ".join([f"`{p}`" for p in PLATFORMS.keys()])
        await ctx.send(f"❌ Usage:\n• Single item: `!buy [platform] #[ID]` (e.g. `!buy epic #2`)\n• Bulk items: `!buy [platform] [amount]` (e.g. `!buy epic 3`)\nOptions: {valid_list}")
        ctx.command.reset_cooldown(ctx)
        return

    platform_key = platform.lower()
    filename = PLATFORMS[platform_key]
    cost_per_item = PRICING[platform_key]

    user_id = ctx.author.id
    current_balance = get_balance(user_id)
    items = get_file_lines(filename)

    if not items:
        await ctx.send(f"❌ The **{platform_key.upper()}** stock is currently empty!")
        ctx.command.reset_cooldown(ctx)
        return

    # --- CASE 1: USER IS BUYING A SPECIFIC ID (Starts with #) ---
    if choice_or_amount.startswith("#"):
        try:
            item_id = int(choice_or_amount.replace("#", ""))
        except ValueError:
            await ctx.send("❌ Invalid ID format! Use a number like `#1` or `#2`.")
            ctx.command.reset_cooldown(ctx)
            return

        if current_balance < cost_per_item:
            await ctx.send(f"❌ You don't have enough coins! **{platform_key.upper()}** costs **{cost_per_item} coins**. Balance: **{current_balance}**.")
            ctx.command.reset_cooldown(ctx)
            return

        if item_id < 1 or item_id > len(items):
            await ctx.send(f"❌ Invalid ID number! Check `!shop` for available numbers (1 to {len(items)}).")
            ctx.command.reset_cooldown(ctx)
            return

        selected_item = items.pop(item_id - 1)
        write_file_lines(filename, items)
        update_balance(user_id, -cost_per_item)

        embed = discord.Embed(
            title=f"🎉 {platform_key.upper()} Choice Dispatched!",
            description=f"**Your Selected Item Details:**\n`{selected_item}`\n\n*Purchased for {cost_per_item} virtual coins.*",
            color=discord.Color.green()
        )
        
        try:
            await ctx.author.send(embed=embed)
            await ctx.send(f"📬 {ctx.author.mention}, check your DMs for selection `#{item_id}`!")
        except discord.Forbidden:
            await ctx.send("❌ I couldn't DM you! Refunding coins...")
            update_balance(user_id, cost_per_item)
            items.insert(item_id - 1, selected_item)
            write_file_lines(filename, items)
            ctx.command.reset_cooldown(ctx)

    # --- CASE 2: USER IS BUYING IN BULK (e.g. !buy epic 3) ---
    else:
        try:
            amount = int(choice_or_amount)
        except ValueError:
            await ctx.send("❌ Please enter a valid number amount or a specific ID starting with `#`.")
            ctx.command.reset_cooldown(ctx)
            return

        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0!")
            ctx.command.reset_cooldown(ctx)
            return

        if amount > len(items):
            await ctx.send(f"❌ Not enough stock! Only **{len(items)}** items left in **{platform_key.upper()}**.")
            ctx.command.reset_cooldown(ctx)
            return

        total_cost = cost_per_item * amount
        if current_balance < total_cost:
            await ctx.send(f"❌ You can't afford **{amount}** items! Total cost: **{total_cost} coins**. Your balance: **{current_balance}**.")
            ctx.command.reset_cooldown(ctx)
            return

        purchased_items = []
        for _ in range(amount):
            purchased_items.append(items.pop(0))

        write_file_lines(filename, items)
        update_balance(user_id, -total_cost)

        items_text = "\n".join([f"📦 **Item:** `{item}`" for item in purchased_items])
        
        embed = discord.Embed(
            title=f"🎉 {platform_key.upper()} Bulk Purchase Dispatched!",
            description=f"**Your Purchased Items:**\n{items_text}\n\n*Purchased {amount} items for {total_cost} virtual coins.*",
            color=discord.Color.green()
        )

        try:
            await ctx.author.send(embed=embed)
            await ctx.send(f"📬 {ctx.author.mention}, you successfully bought **{amount} items** for **{total_cost} coins**! Check your DMs.")
        except discord.Forbidden:
            await ctx.send("❌ I couldn't DM you! Refunding your coins...")
            update_balance(user_id, total_cost)
            for item in reversed(purchased_items):
                items.insert(0, item)
            write_file_lines(filename, items)
            ctx.command.reset_cooldown(ctx)

# --- PUBLIC COMMAND 3: DAILY FREE COINS ---
@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily_coins(ctx):
    reward = 50
    update_balance(ctx.author.id, reward)
    await ctx.send(f"💰 {ctx.author.mention}, you claimed your daily reward of **{reward} coins**! Type `!shop` to browse items.")

# --- PUBLIC COMMAND 4: CHECK PROFILE BALANCE ---
@bot.command(name="balance")
async def check_balance(ctx):
    balance = get_balance(ctx.author.id)
    await ctx.send(f"💳 {ctx.author.mention}, your current balance is **{balance} coins**.")

# --- STAFF COMMAND 5: ADD STOCK (STAFF ONLY) ---
@bot.command(name="add")
@commands.has_permissions(manage_messages=True)
async def add_stock(ctx, platform: str = None, *, item: str = None):
    if not platform or platform.lower() not in PLATFORMS or not item:
        await ctx.send("❌ Usage: `!add [platform] [details]`")
        return
    platform_key = platform.lower()
    filename = PLATFORMS[platform_key]
    
    items = get_file_lines(filename)
    items.append(item)
    write_file_lines(filename, items)
    
    await ctx.send(f"✅ Successfully added to **{platform_key.upper()}** stock as Item `#{len(items)}`!")

# --- STAFF COMMAND 6: REMOVE A SPECIFIC ITEM BY ID (STAFF ONLY) ---
@bot.command(name="removeitem")
@commands.has_permissions(manage_messages=True)
async def remove_stock_item(ctx, platform: str = None, item_id: int = None):
    if not platform or platform.lower() not in PLATFORMS or item_id is None:
        await ctx.send("❌ Usage: `!removeitem [platform] [ID_Number]`")
        return

    platform_key = platform.lower()
    filename = PLATFORMS[platform_key]
    items = get_file_lines(filename)

    if not items:
        await ctx.send(f"❌ The **{platform_key.upper()}** stock is already empty!")
        return

    if item_id < 1 or item_id > len(items):
        await ctx.send(f"❌ Invalid ID! Check `!shop` for current item numbers (1 to {len(items)}).")
        return

    items.pop(item_id - 1)
    write_file_lines(filename, items)
    await ctx.send(f"🗑️ Successfully removed Item `#{item_id}` from **{platform_key.upper()}** stock.")

# --- STAFF COMMAND 7: GIVE COINS (STAFF ONLY) ---
@bot.command(name="givecoins")
@commands.has_permissions(manage_messages=True)
async def give_coins(ctx, member: discord.Member = None, amount: int = None):
    if not member or amount is None or amount <= 0:
        await ctx.send("❌ Usage: `!givecoins [@user] [amount]`")
        return
    update_balance(member.id, amount)
    new_bal = get_balance(member.id)
    await ctx.send(f"✅ Awarded **{amount} coins** to {member.mention}! Their new balance is **{new_bal} coins**.")

# --- ERROR HANDLING ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        if ctx.command.name == "daily":
            hours = int(error.retry_after // 3600)
            minutes = int((error.retry_after % 3600) // 60)
            await ctx.send(f"⏳ Come back in **{hours}h {minutes}m**.")
        else:
            await ctx.send(f"⏳ Please wait **{error.retry_after:.1f}** seconds before using `!{ctx.invoked_with}` again.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use this staff command.")

bot.run(DISCORD_TOKEN)
