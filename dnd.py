import random

def roll(update, context) -> None:
    try:
        dice_roll = context.args[0]
        num_dice, dice_type = map(int, dice_roll.split('d'))
        
        rolls = [random.randint(1, dice_type) for _ in range(num_dice)]
        if num_dice > 1:
            total = sum(rolls)
            update.message.reply_text(f'Выпало: {rolls}, сумма: {total}')
        else:
            update.message.reply_text(f'Выпало: {rolls[0]}')
    except Exception as _:
        update.message.reply_text('Usage: /roll XdY (e.g. /roll 2d6)')

