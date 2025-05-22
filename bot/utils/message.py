async def send_temp_message(message, text: str):
    temp = await message.answer(text)
    try:
        await temp.delete()
    except:
        pass
