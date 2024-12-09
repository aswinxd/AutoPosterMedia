from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
import asyncio
import motor.motor_asyncio


api_id = 12799559
api_hash = '077254e69d93d08357f25bb5f4504580'
bot_token = ''


client = TelegramClient('user_session', api_id, api_hash)
bot = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)


mongo_client = motor.motor_asyncio.AsyncIOMotorClient('mongodb+srv://test:test@cluster0.q9llhnj.mongodr0')
db = mongo_client['telegram_bot']
collection = db['schedules']
tasks = {}

async def forward_messages(user_id, source_channel_id, destination_channel_id, batch_size, delay):
    post_counter = 0

    async with client:
        async for message in client.iter_messages(int(source_channel_id), reverse=True):
            if post_counter >= batch_size:
                await asyncio.sleep(delay)  # Wait for the specified delay before sending the next batch
                post_counter = 0  # Reset the post counter after sending a batch

            if message.photo or message.video:
                try:
                    await client.send_message(int(destination_channel_id), message)
                    post_counter += 1
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 5)
                    await client.send_message(int(destination_channel_id), message)
                except Exception as e:
                    print(f"An error occurred: {e}")

            if user_id not in tasks or tasks[user_id].cancelled():
                break

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id


    user_data = await collection.find_one({'user_id': user_id})

    if user_data:
        await event.respond('You already have a schedule set up. To create a new schedule, use the /newschedule command.')
        return
    else:
        await collection.insert_one({'user_id': user_id})

    async with bot.conversation(user_id) as conv:
        await conv.send_message('Please provide the source channel ID:')
        source_channel_id = await conv.get_response()
        if not source_channel_id.text.lstrip('-').isdigit():
            await conv.send_message('Invalid channel ID. Please restart the process with /start.')
            return

        await conv.send_message('Please provide the destination channel ID:')
        destination_channel_id = await conv.get_response()
        if not destination_channel_id.text.lstrip('-').isdigit():
            await conv.send_message('Invalid channel ID. Please restart the process with /start.')
            return

        await conv.send_message('How many posts do you want to forward in each batch?')
        post_limit = await conv.get_response()
        if not post_limit.text.isdigit():
            await conv.send_message('Invalid number of posts. Please restart the process with /start.')
            return

        await conv.send_message('What is the time interval between batches in seconds?')
        delay = await conv.get_response()
        if not delay.text.isdigit():
            await conv.send_message('Invalid delay. Please restart the process with /start.')
            return

        await conv.send_message(f'You have set up the following schedule:\nSource Channel ID: {source_channel_id.text}\nDestination Channel ID: {destination_channel_id.text}\nPost Limit: {post_limit.text}\nDelay: {delay.text} seconds\n\nDo you want to start forwarding? (yes/no)')
        confirmation = await conv.get_response()
        if confirmation.text.lower() != 'yes':
            await conv.send_message('Schedule setup cancelled.')
            return
        await collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'source_channel_id': int(source_channel_id.text),
                'destination_channel_id': int(destination_channel_id.text),
                'post_limit': int(post_limit.text),
                'delay': int(delay.text)
            }}
        )

        await conv.send_message(f'Forwarding messages from {source_channel_id.text} to {destination_channel_id.text} every {delay.text} seconds...')


        task = asyncio.create_task(forward_messages(user_id, int(source_channel_id.text), int(destination_channel_id.text), int(post_limit.text), int(delay.text)))
        tasks[user_id] = task

        await conv.send_message(f'Schedule details:\nSource Channel ID: {source_channel_id.text}\nDestination Channel ID: {destination_channel_id.text}\nPost Limit: {post_limit.text}\nDelay: {delay.text} seconds')


#@bot.on(events.NewMessage(pattern='/newschedule'))
#async def new_schedule(event):
@bot.on(events.NewMessage(pattern='/newschedule'))
async def new_schedule(event):
    user_id = event.sender_id

    async with bot.conversation(user_id) as conv:
        await conv.send_message('Please provide the source channel ID:')
        source_channel_id = await conv.get_response()
        if not source_channel_id.text.lstrip('-').isdigit():
            await conv.send_message('Invalid channel ID. Please restart the process with /newschedule.')
            return

        await conv.send_message('Please provide the destination channel ID:')
        destination_channel_id = await conv.get_response()
        if not destination_channel_id.text.lstrip('-').isdigit():
            await conv.send_message('Invalid channel ID. Please restart the process with /newschedule.')
            return

        await conv.send_message('How many posts do you want to forward in each batch?')
        post_limit = await conv.get_response()
        if not post_limit.text.isdigit():
            await conv.send_message('Invalid number of posts. Please restart the process with /newschedule.')
            return

        await conv.send_message('What is the time interval between batches in seconds?')
        delay = await conv.get_response()
        if not delay.text.isdigit():
            await conv.send_message('Invalid delay. Please restart the process with /newschedule.')
            return

        await conv.send_message(f'You have set up the following schedule:\nSource Channel ID: {source_channel_id.text}\nDestination Channel ID: {destination_channel_id.text}\nPost Limit: {post_limit.text}\nDelay: {delay.text} seconds\n\nDo you want to start forwarding? (yes/no)')
        confirmation = await conv.get_response()
        if confirmation.text.lower() != 'yes':
            await conv.send_message('Schedule setup cancelled.')
            return

        
        await collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'source_channel_id': int(source_channel_id.text),
                'destination_channel_id': int(destination_channel_id.text),
                'post_limit': int(post_limit.text),
                'delay': int(delay.text)
            }},
            upsert=True
        )

        await conv.send_message(f'Forwarding messages from {source_channel_id.text} to {destination_channel_id.text} every {delay.text} seconds...')

    
        if user_id in tasks and not tasks[user_id].cancelled():
            tasks[user_id].cancel()
    
        task = asyncio.create_task(forward_messages(user_id, int(source_channel_id.text), int(destination_channel_id.text), int(post_limit.text), int(delay.text)))
        tasks[user_id] = task

        await conv.send_message(f'Schedule details:\nSource Channel ID: {source_channel_id.text}\nDestination Channel ID: {destination_channel_id.text}\nPost Limit: {post_limit.text}\nDelay: {delay.text} seconds')
  
@bot.on(events.NewMessage(pattern='/stop'))
async def stop(event):
    user_id = event.sender_id

    if user_id in tasks and not tasks[user_id].cancelled():
        tasks[user_id].cancel()
        await event.respond('Forwarding process stopped.')
    else:
        await event.respond('No active forwarding process found.')


bot.start(bot_token=bot_token)

#itely
asyncio.get_event_loop().run_forever()
