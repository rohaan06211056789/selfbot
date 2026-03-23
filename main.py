import discord
import asyncio
import subprocess
from datetime import datetime
import os
import aiohttp
import random
#cfg
PREFIX = "sb!"
PURGE_LIMIT = 50
DEL_DELAY = 0.2

client = discord.Client()

def log(level, msg):
    print(f"[{level.upper()}] {msg}")

def channel_name(channel):
    return channel.name if hasattr(channel,'name') else f"DM({channel.recipient})"

async def raw_sdelete(channel_id, msg_id, token):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    payload = {
        "content":"** **",
        "nonce": str(message_id),
        "tts": False
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status==200:
                data = await resp.json()
                ghost_msg_id = data['id']
                await asyncio.sleep(0.2)
                return ghost_msg_id
    return None

@client.event
async def on_ready():
    log("info", f"logged in as {client.user} (ID: {client.user.id})")
    log("info", f"PREFIX: {PREFIX} - e.g {PREFIX}purge")
    log("info", f"PURGE_LIMIT val: {PURGE_LIMIT} messages")
    log("info", f"DEL_DELAY val: {DEL_DELAY}s")
    print()

@client.event
async def on_message(msg):
    if msg.author != client.user:
        return
    
    #purge, sb!purge
    if msg.content.lower().startswith(f"{PREFIX}purge"):
        parts = msg.content.split()
        if len(parts) > 1:
            try:
                limit = int(parts[1])
                if limit <= 0:
                    raise ValueError
            except ValueError:
                log("error", f"invalid arg '{parts[1]}' - must be a positive number")
                await msg.edit(content=f'invalid usage. try {PREFIX}purge or {PREFIX}purge <amount>')
                await asyncio.sleep(3)
                await msg.delete()
                return
        else:
            limit = PURGE_LIMIT
        channel = msg.channel
        log("info",f"purge started in #{channel_name(channel)} (ID: {channel.id}), scanning up to {limit} msgs")
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
        deleted = 0
        failed = 0
        scanned = 0
        async for entry in channel.history(limit=limit):
            scanned+=1
            if entry.author == client.user:
                try:
                    await entry.delete()
                    deleted += 1
                    log("action",f"deleted msg {deleted}: \"{entry.content[:60]}{'...' if len(entry.content) > 60 else ''}\"")
                    await asyncio.sleep(DEL_DELAY)
                except discord.Forbidden:
                    failed += 1
                    log("error", f"hit discord.Forbidden on msg id {entry.id}, failed to delete")
                except discord.HTTPException as e:
                    failed += 1
                    log("warning", f"hit discord.HTTPException {entry.id}-{e}, failed to delete")
        print()
        log("info",f"purge complete! scanned {scanned}, deleted {deleted}, failed {failed}")
        print()
    
    #reaction spam, sb!react <count> <emoji>
    if msg.content.lower().startswith(f"{PREFIX}react"):
        parts = msg.content.split()
        if len(parts) < 3:
            await msg.edit(content=f"invalid usage. try {PREFIX}react <count> <emoji>")
            await asyncio.sleep(2)
            await msg.delete()
            return
        try:
            limit = int(parts[1])
            emoji = parts[2]
        except ValueError:
            await msg.edit(content="count must be a number.")
            return
        try:
            await msg.delete()
        except:
            pass
        log("info",f"reacting to {limit} messages with {emoji} in #{channel_name(msg.channel)}")
        count = 0
        async for entry in msg.channel.history(limit = limit):
            try:
                await entry.add_reaction(emoji)
                count += 1
                log("action",f"reacted to msg {count}/{limit}")
                await asyncio.sleep(DEL_DELAY)
            except discord.Forbidden:
                log("error",f"hit discord.Forbidden on msg id {entry.id}, failed to react")
                break
            except discord.HTTPException as e:
                log("warning", f"hit discord.HTTPException {entry.id}-{e}, failed to react")
                await asyncio.sleep(1)
                continue
        log("info",f"finished reacting to {count} msgs.")
    
    #reaction remover, sb!removereacts
    if msg.content.lower().startswith(f"{PREFIX}removereacts"):
        parts = msg.content.split()
        limit = PURGE_LIMIT
        emoji = None
        for part in parts[1:]:
            try:
                limit = int(part)
            except ValueError:
                emoji = part
        channel = msg.channel
        log("info",f"removing {'all' if not emoji else emoji} reactions in last {limit} msgs in #{channel_name(channel)}")
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
        count = 0
        failed = 0
        async for entry in channel.history(limit=limit):
            try:
                if emoji:
                    await entry.remove_reaction(emoji,client.user)
                else:
                    for reaction in entry.reactions:
                        await reaction.remove(client.user)
                        await asyncio.sleep(0.05)
                count += 1
                log("action",f"cleared reactions on msg {count}: \"{entry.content[:60]}{'...' if len(entry.content) > 60 else ''}\"")
                await asyncio.sleep(DEL_DELAY)
            except discord.Forbidden:
                failed += 1
                log("error", f"hit discord.Forbidden on msg id {entry.id}")
            except discord.HTTPException as e:
                failed += 1
                log("warning",f"hit discord.HTTPException on {entry.id}-{e}")
        print()
        log("info",f"successfully cleared reactions on {count} msgs, failed {failed}")
        print()

    #chat export, sb!export
    if msg.content.lower().startswith(f"{PREFIX}export"):
        parts = msg.content.split()
        channel_id = msg.channel.id
        os.makedirs("exports",exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exports/{channel_name(msg.channel)}_{timestamp}.html"
        cmd = [
            DCE_CLI,
            "export",
            "-t", TOKEN,
            "-c", str(channel_id),
            "-f", "HtmlDark",
            "-o", output_filename
        ]
        if len(parts) > 1:
            try:
                limit = int(parts[1])
                cmd += ["--after",parts[1]] #i.e sb!export 2026-03-20
            except ValueError:
                log("error",f"invalid arg '{parts[1]}'")
                return
        log("info",f"exporting #{channel_name(msg.channel)}...")
        channel = msg.channel
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True)
        )
        if result.returncode == 0:
            log("info","export complete, uploading to catbox...")
            export_file = None
            if os.path.exists(output_filename):
                export_file = output_filename
            else:
                html_files = [
                    os.path.join("exports",f) for f in os.listdir("exports")
                    if f.endswith(".html")
                ]
                if html_files:
                    export_file = max(html_files, key=os.path.getmtime)
            if not export_file:
                log("error","export file not found post export")
                return
            catbox_url = None
            try:
                with open(export_file,"rb") as f:
                    form = aiohttp.FormData()
                    form.add_field("reqtype","fileupload")
                    form.add_field("fileToUpload",f,filename=os.path.basename(export_file),content_type="text/html")
                    async with aiohttp.ClientSession() as session:
                        async with session.post("https://catbox.moe/user/api.php",data=form) as resp:
                            if resp.status == 200:
                                catbox_url = (await resp.text()).strip()
                                log("info",f"uploaded to catbox: {catbox_url}")
                            else:
                                log("error",f"catbox upload failed with status {resp.status}")
            except Exception as e:
                log("error",f"catbox upload error: {e}")
            if catbox_url:
                notice = await channel.send(f"export ready: {catbox_url}")
                await asyncio.sleep(5)
                await notice.delete()
            else:
                notice = await channel.send("export done, catbox upload failed.")
                await asyncio.sleep(5)
                await notice.delete()
        else:
            log("error", f"export failed: {result.stderr.strip()}")

    #timed messages, sb!msgsend
    if msg.content.lower().startswith(f"{PREFIX}msgsend"):
        parts = msg.content.split(maxsplit=2)
        if len(parts) < 3:
            await msg.edit(content=f"invalid usage. try {PREFIX}msgsend <HH:MM> <message>")
            await asyncio.sleep(3)
            await msg.delete()
            return
        try:
            send_time = datetime.strptime(parts[1],"%H:%M").replace(
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day
            )
        except ValueError:
            await msg.edit(content="invalid time format, use HH:MM e.g 14:30")
            await asyncio.sleep(3)
            await msg.delete()
            return
        text = parts[2]
        channel = msg.channel
        now = datetime.now()
        delay = (send_time - now).total_seconds()
        if delay < 0:
            await msg.edit(content="that time has already passed today!")
            await asyncio.sleep(3)
            await msg.delete()
            return
        log("info",f"scheduled message in #{channel_name(channel)} at {parts[1]} ({int(delay)}s from now)")
        await msg.delete()
        await asyncio.sleep(delay)
        await channel.send(text)
        log("info",f"sent scheduled msg: \"{text[:60]}\"")

    #timed message delete, sb!msgdelete
    if msg.content.lower().startswith(f"{PREFIX}msgdelete"):
        parts = msg.content.split()
        if len(parts) < 3:
            await msg.edit(content=f"invalid usage. try {PREFIX}msgdelete <HH:MM> <msgId>")
            await asyncio.sleep(3)
            await msg.delete()
            return
        try:
            delete_time = datetime.strptime(parts[1],"%H:%M").replace(
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day
            )
            message_id=int(parts[2])
        except ValueError:
            await msg.edit(content="invalid time format. use HH:MM e.g 14:30")
            await asyncio.sleep(3)
            await msg.delete()
            return
        now = datetime.now()
        delay = (delete_time-now).total_seconds()
        if delay <0:
            await msg.edit(content="that time has already passed today!")
            await asyncio.sleep(3)
            await msg.delete()
            return
        channel = msg.channel
        log("info",f"scheduled delete of msg {message_id} at {parts[1]} ({int(delay)}s from now)")
        await msg.delete()
        await asyncio.sleep(delay)
        try:
            target = await channel.fetch_message(message_id)
            await target.delete()
            log("info",f"deleted scheduled message {message_id}")
        except discord.NotFound:
            log("error", f"message {message_id} not found")
        except discord.Forbidden:
            log("error", f"hit discord.Forbidden, can't delete msg {message_id}")
        except discord.HTTPException as e:
            log("error", f"hit discord.HTTPException-{e}")

    
    #spam, sb!spam <count> <phrase>
    if msg.content.lower().startswith(f"{PREFIX}spam"):
        parts = msg.content.split(maxsplit=2)
        if len(parts) < 3:
            await msg.edit(content=f"invalid usage. try {PREFIX}spam <count> <phrase>")
            await asyncio.sleep(2)
            await msg.delete()
            return
        try:
            count = int(parts[1])
            phrase = parts[2]
        except ValueError:
            await msg.edit(content="count must be a number!")
            await asyncio.sleep(2)
            await msg.delete()
            return
        try:
            await msg.delete()
        except:
            pass
        log("info",f"spamming '{phrase[:30]}...' {count} times in #{channel_name(msg.channel)}")
        for i in range(count):
            try:
                await msg.channel.send(phrase)
                log("action",f"sent msg {i+1}/{count}")
                await asyncio.sleep(DEL_DELAY)
            except discord.Forbidden:
                log("error", "hit discord.Forbidden, failed to send messages here")
                break
            except discord.HTTPException as e:
                log("warning", f"hit discord.HTTPException-{e}")
                await asyncio.sleep(2)
        log("info",f"finished spamming {count} times!")
    
    #ai, sb!ai
    if msg.content.lower().startswith(f"{PREFIX}ai"):
        parts = msg.content.split(maxsplit=1)
        if len(parts) < 2:
            await msg.edit(content=f"invalid usage. try {PREFIX}ai <prompt>")
            await asyncio.sleep(3)
            await msg.delete()
            return
        if not AI_KEY:
            await msg.edit(content="no AI API key configured.")
            await asyncio.sleep(3)
            await msg.delete()
            return
        prompt = parts[1]
        try:
            await msg.edit(content="thinking...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ai.hackclub.com/proxy/v1/chat/completions",
                    headers = {
                        "Authorization": f"Bearer {AI_KEY}",
                        "Content-Type": "application/json"
                    },
                    json = {
                        "model": "google/gemini-3-flash-preview",
                        "messages": [{"role":"user","content":prompt}],
                        "max_tokens": 10000
                    }
                ) as resp:
                    data = await resp.json()
                    log("info",f"raw ai res {str(data)[:200]}")
                    if resp.status == 200:
                        reply = data["choices"][0]["message"]["content"].strip()
                        reply = reply + "\n\n\n-# generated by gemini i think"
                        log("info",f"AI response: \"{reply[:60]}\"")
                        if len(reply) > 2000:
                            await msg.edit(content=reply[:1973]+"...\n-#generated with magick AI")
                        else:
                            await msg.edit(content=reply)
                    else:
                        err = data.get("error",{}).get("message","unknown error")
                        log("error",f"AI API error: {err}")
                        await msg.edit(content=f"AI error: {err}")
        except Exception as e:
            log("error",f"AI request failed, {e}")
            await msg.edit(content="AI request failed.")

if __name__=='__main__':
    print('\nThe original bot was not made by me, I just added a few changes to it. \n\n')
    print('Keep in mind the export command only works on linux, that was intentional')
    print('COMMANDS: \n\nsb!purge(msgs)\nsb!react(iterations)(emoji)\nsb!export\nsb!spam(iterations)\nsb!removereacts\nTheres a few more but I honestly dont think anyone is gonna use them\n')
    with open("token.txt") as f:
    	TOKEN = f.read().strip()
    if not TOKEN:
        TOKEN = input("Enter your discord token (it's stored locally, dw): ").strip()
        with open("token.txt", "w") as f:
            f.write(TOKEN)
    with open("key.txt") as e:
    	AI_KEY = e.read().strip()
    if not AI_KEY:
        AI_KEY = input('(OPTIONAL) Enter ai key to use sb!ai (u can dm me for one but i probably wont have any): ').strip()
        if AI_KEY:
            with open("key.txt", "w") as f:
                f.write(AI_KEY)
    else:
        print('Using ai key:\n',AI_KEY)
    DCE_CLI = "./exporter/DiscordChatExporter.Cli"

    client.run(TOKEN)

